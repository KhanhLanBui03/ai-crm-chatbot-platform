"""Truy hồi lai — MỘT câu SQL gộp làn vector và làn từ khoá, hợp nhất bằng RRF k=60. [PRODUCTION]

UC023 chặng 7 · ADR-0006 · ADR-0007. Hàm nhận một ``AsyncSession`` ĐÃ gắn tenant
(``src.ai.db.session.get_tenant_session``) và chạy mọi thứ trong đúng transaction của phiên đó.

::

    làn vector    ORDER BY embedding <=> q  LIMIT 30   ─┐ row_number() → hạng
                                                         ├─ RRF: Σ 1/(60 + hạng) ─→ top-k
    làn từ khoá   ORDER BY ts_rank DESC     LIMIT 30   ─┘ row_number() → hạng

BA CHẾ ĐỘ CỦA THÍ NGHIỆM E3 CHẠY CÙNG CÂU SQL NÀY
------------------------------------------------
Tắt một làn bằng cách truyền ``None`` (``vector=None`` → chỉ từ khoá, ``tsquery=None`` → chỉ
vector), không viết ba câu SQL. Làn còn lại một mình thì RRF giữ nguyên thứ hạng của nó, nên
dense / sparse / hybrid chỉ khác nhau đúng một biến — điều kiện để phép so có nghĩa.

NĂM ĐIỀU CỐ Ý
-------------
1. **Toán tử ``<=>`` (cosine), không phải ``<->`` (L2).** Chỉ mục dựng bằng ``vector_cosine_ops``
   (``scripts/create_hnsw_index.sql``). Toán tử lệch lớp toán tử của chỉ mục thì Postgres quét
   tuần tự — vẫn ra đúng thứ hạng vì bge-m3 đã chuẩn hoá L2, nên không test chức năng nào đỏ,
   nhưng không còn HNSW để mà đo. ``test_lan_vector_dung_chi_muc_hnsw`` khoá điều này.
2. **Chỉ dùng THỨ HẠNG, không cộng điểm thô** (ADR-0006). ``<=>`` và ``ts_rank`` là hai thang
   khác nhau; RRF né được việc chuẩn hoá chúng. Đừng "cải tiến" thành tổng có trọng số.
3. **Ba điều kiện lọc ở CẢ HAI làn:** ``tenant_id = ai.current_tenant()`` ngay trong câu
   (ADR-0007 — lớp thứ hai sau RLS, không nhận tenant làm tham số) · tài liệu ``READY`` (không
   lấy đoạn của job đang nạp hay đã lưu trữ) · đúng ``embedding_model`` + ``embedding_version``
   của vector câu hỏi (bất biến 1 §3.4.2: hai không gian vector không được trộn). Làn từ khoá
   cũng lọc model vì trong lúc nhúng lại, hai thế hệ đoạn của cùng nội dung có thể cùng tồn tại.
   Làn vector bỏ thêm đoạn chưa có vector: HNSW vốn không chứa chúng, nhưng quét tuần tự thì có
   (khoảng cách NULL xếp cuối) — không lọc thì hai kế hoạch truy vấn cho hai kết quả khác nhau.
4. **Tham số HNSW đặt bằng ``set_config(..., true)`` trong CÙNG transaction** — tương đương
   ``SET LOCAL`` nhưng nhận bind parameter (lý do như ``session.py``). Hết transaction là mất,
   không theo kết nối về pool. ``hnsw.iterative_scan``: HNSW lọc tenant SAU khi quét, nên ở kho
   nhiều tenant ``ef_search`` ứng viên đầu có thể gần như toàn của tenant khác. Quét lặp thì
   pgvector quét tiếp tới khi đủ ``LIMIT``. ``relaxed_order`` có thể trả hơi lệch thứ tự —
   ``row_number() OVER (ORDER BY khoang_cach)`` sau CTE ``MATERIALIZED`` xếp lại chính xác.
5. **``plan_cache_mode = force_custom_plan``.** psycopg3 tự chuẩn bị câu lệnh sau 5 lần chạy, rồi
   Postgres có thể chuyển sang kế hoạch chung (không nhìn giá trị tham số). Kế hoạch đổi giữa
   chừng một lượt đo là biến gây nhiễu: 5 câu đầu một đường, các câu sau đường khác.

Hoà điểm được phá bằng hạng tốt nhất rồi ``id`` — cùng dữ liệu thì chạy lại ra cùng thứ tự
(``.claude/rules/rag-eval.md``: harness phải tái lập được).

GIỚI HẠN ĐÃ BIẾT — ghi vào báo cáo
----------------------------------
``@@`` (``ts_match_vq``) KHÔNG leakproof. Dưới RLS, Postgres không được dùng một điều kiện không
leakproof làm điều kiện chỉ mục trước khi policy chạy, nên làn từ khoá của ``ai_app`` không dùng
GIN mà quét các đoạn của tenant (qua chỉ mục ``tenant_id``) rồi lọc ``@@`` từng dòng. Chi phí
tuyến tính theo số đoạn của MỘT tenant — chấp nhận được ở quy mô SME, phải đo ở Ngày 15.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.db.repositories.chunk_repository import vector_sang_chuoi

# k = 60 theo ADR-0006 — hằng số của thuật toán, không phải tham số cấu hình. 30 ứng viên mỗi làn
# theo kế hoạch 21 ngày (Ngày 6, ``hybrid_search(pool=30)``); ADR-0006 bản 19/08 còn ghi top-20.
RRF_K = 60
UNG_VIEN_MOI_LAN = 30
EF_SEARCH = 100

QuetLap = Literal["off", "relaxed_order", "strict_order"]

# Điều kiện chung của hai làn — viết một lần để hai làn không bao giờ lệch nhau.
_DIEU_KIEN = """
       c.tenant_id = ai.current_tenant()
       AND d.status = 'READY'
       AND c.embedding_model = :embedding_model
       AND c.embedding_version = :embedding_version
"""

_SQL_TIM_LAI = text(
    f"""
    WITH lan_vector AS MATERIALIZED (
        SELECT c.id, c.embedding <=> CAST(:vector AS vector) AS khoang_cach
          FROM knowledge.knowledge_chunks c
          JOIN knowledge.knowledge_documents d ON d.id = c.document_id
         WHERE CAST(:vector AS vector) IS NOT NULL
           AND c.embedding IS NOT NULL
           AND {_DIEU_KIEN}
         ORDER BY khoang_cach
         LIMIT :ung_vien
    ),
    hang_vector AS (
        SELECT id, row_number() OVER (ORDER BY khoang_cach, id) AS hang FROM lan_vector
    ),
    lan_tu_khoa AS MATERIALIZED (
        SELECT c.id, ts_rank(c.content_segmented, q.tsq) AS diem
          FROM knowledge.knowledge_chunks c
          JOIN knowledge.knowledge_documents d ON d.id = c.document_id
         CROSS JOIN to_tsquery('simple', knowledge.f_unaccent(CAST(:tsquery AS text))) AS q(tsq)
         WHERE c.content_segmented @@ q.tsq
           AND {_DIEU_KIEN}
         ORDER BY diem DESC, c.id
         LIMIT :ung_vien
    ),
    hang_tu_khoa AS (
        SELECT id, row_number() OVER (ORDER BY diem DESC, id) AS hang FROM lan_tu_khoa
    ),
    hop_nhat AS (
        SELECT COALESCE(v.id, t.id) AS id,
               v.hang AS hang_vector,
               t.hang AS hang_tu_khoa,
               COALESCE(1.0 / (:rrf_k + v.hang), 0) + COALESCE(1.0 / (:rrf_k + t.hang), 0)
                   AS diem_rrf
          FROM hang_vector v
          FULL OUTER JOIN hang_tu_khoa t ON t.id = v.id
    )
    SELECT h.id, c.document_id, d.title, d.file_name, d.version, c.chunk_index, c.heading,
           c.page_number, c.content, h.diem_rrf, h.hang_vector, h.hang_tu_khoa,
           1 - (c.embedding <=> CAST(:vector AS vector)) AS do_tuong_dong
      FROM hop_nhat h
      JOIN knowledge.knowledge_chunks c ON c.id = h.id
      JOIN knowledge.knowledge_documents d ON d.id = c.document_id
     ORDER BY h.diem_rrf DESC, LEAST(h.hang_vector, h.hang_tu_khoa), h.id
     LIMIT :k
    """
)


@dataclass(frozen=True, slots=True)
class DoanTimDuoc:
    """Một đoạn trong top-k, kèm hạng ở từng làn — ``None`` nghĩa là làn đó không đưa nó vào
    top ``UNG_VIEN_MOI_LAN``. Hai cột hạng là dữ liệu cho chương 5: làn nào cứu câu nào."""

    chunk_id: UUID
    document_id: UUID
    title: str
    file_name: str | None
    version: int
    chunk_index: int
    heading: str | None
    page_number: int | None
    content: str
    diem_rrf: float
    hang_vector: int | None
    hang_tu_khoa: int | None
    # Cosine với vector câu hỏi — thang TUYỆT ĐỐI để áp sàn liên quan (điểm RRF chỉ phản ánh thứ
    # hạng, ~0,016–0,033 với mọi câu). Tính ở SELECT cuối cho đúng k dòng, nên đoạn chỉ làn từ
    # khoá tìm thấy cũng có. ``None`` khi chạy không có vector (chế độ sparse).
    do_tuong_dong: float | None = None


def tham_so_cau_lenh(
    vector: Sequence[float] | None,
    tsquery: str | None,
    embedding_model: str,
    embedding_version: str,
    k: int,
    ung_vien: int,
) -> dict:
    """Bind parameter của ``_SQL_TIM_LAI`` — tách riêng để harness ``EXPLAIN`` ĐÚNG câu đã chạy."""
    return {
        "vector": None if vector is None else vector_sang_chuoi(vector),
        "tsquery": tsquery,
        "embedding_model": embedding_model,
        "embedding_version": embedding_version,
        "ung_vien": ung_vien,
        "rrf_k": RRF_K,
        "k": k,
    }


async def dat_tham_so_truy_hoi(
    session: AsyncSession, *, ef_search: int = EF_SEARCH, quet_lap: QuetLap = "relaxed_order"
) -> None:
    """Đặt tham số HNSW + kế hoạch truy vấn cho transaction hiện tại (hết transaction là mất)."""
    await session.execute(
        text(
            "SELECT set_config('hnsw.ef_search', :ef, true),"
            " set_config('hnsw.iterative_scan', :quet, true),"
            " set_config('plan_cache_mode', 'force_custom_plan', true)"
        ),
        {"ef": str(int(ef_search)), "quet": quet_lap},
    )


async def tim_kiem_lai(
    session: AsyncSession,
    *,
    vector: Sequence[float] | None,
    tsquery: str | None,
    embedding_model: str,
    embedding_version: str,
    k: int = 5,
    ung_vien: int = UNG_VIEN_MOI_LAN,
    ef_search: int = EF_SEARCH,
    quet_lap: QuetLap = "relaxed_order",
) -> list[DoanTimDuoc]:
    """Top-``k`` đoạn của tenant đang gắn trên ``session``, xếp theo RRF.

    ``tsquery`` là chuỗi từ ``src.ai.rag.tsquery.build_tsquery`` (đã lọc sạch toán tử).
    ``embedding_model``/``embedding_version`` lấy từ ``KetQuaNhung`` của CHÍNH vector câu hỏi —
    danh tính của phía đã sinh vector, để vector câu hỏi và vector kho luôn cùng một không gian.
    """
    if vector is None and tsquery is None:
        return []
    await dat_tham_so_truy_hoi(session, ef_search=ef_search, quet_lap=quet_lap)
    ket_qua = await session.execute(
        _SQL_TIM_LAI,
        tham_so_cau_lenh(vector, tsquery, embedding_model, embedding_version, k, ung_vien),
    )
    return [
        DoanTimDuoc(
            chunk_id=r.id,
            document_id=r.document_id,
            title=r.title,
            file_name=r.file_name,
            version=r.version,
            chunk_index=r.chunk_index,
            heading=r.heading,
            page_number=r.page_number,
            content=r.content,
            diem_rrf=float(r.diem_rrf),
            hang_vector=r.hang_vector,
            hang_tu_khoa=r.hang_tu_khoa,
            do_tuong_dong=None if r.do_tuong_dong is None else float(r.do_tuong_dong),
        )
        for r in ket_qua
    ]
