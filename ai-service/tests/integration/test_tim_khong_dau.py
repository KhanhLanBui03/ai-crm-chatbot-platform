"""Làn từ khoá trên Postgres THẬT (V210) — câu hỏi không dấu tìm được đoạn có dấu.

Chạy bằng role ``ai_app`` (chịu RLS). Mỗi test ghi dữ liệu trong một transaction
``force_rollback`` — không để lại dòng nào cho test khác.

Ba câu hội đồng sẽ hỏi, mỗi câu có một test làm bằng chứng:

- Vì sao hai đầu phải đi qua CÙNG một hàm bỏ dấu?
  → ``test_phia_hoi_khong_bo_dau_thi_truot``
- Vì sao OR mà không AND?
  → ``test_them_mot_tu_thua_or_van_khop_and_thi_rong``
- Vì sao cần hàm IMMUTABLE?
  → ``test_f_unaccent_la_immutable`` · ``test_content_segmented_la_cot_generated``
"""

from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import psycopg
import pytest

from src.ai.rag.tsquery import build_tsquery

_CHEN_TAI_LIEU = """
    INSERT INTO knowledge.knowledge_documents (id, tenant_id, title, source_type, file_path, status)
    VALUES (%s, ai.current_tenant(), %s, 'TXT', %s, 'PROCESSING')
"""
_CHEN_DOAN = """
    INSERT INTO knowledge.knowledge_chunks
        (tenant_id, document_id, chunk_index, content, embedding_model, embedding_version)
    VALUES (ai.current_tenant(), %s, %s, %s, 'chua-nhung', 'v0')
"""
# Truy vấn ĐÚNG như node retrieve sẽ dùng: hàm bỏ dấu phía hỏi là CÙNG hàm với cột GENERATED.
_TIM = """
    SELECT chunk_index FROM knowledge.knowledge_chunks
     WHERE document_id = %s
       AND content_segmented @@ to_tsquery('simple', knowledge.f_unaccent(%s))
     ORDER BY chunk_index
"""

DOAN = [
    "Chính sách đổi trả trong 30 ngày kể từ ngày nhận hàng.",  # 0
    # 1 — có cả "sách" lẫn "chính" nhưng KHÔNG liền nhau
    "Sách hướng dẫn này là bản chính thức của hãng.",
    "Tủ lạnh NH-TL256I giá niêm yết 6.790.000đ, giao miễn phí tại Đà Nẵng.",  # 2
    "Bảo hành máy lọc nước RO 24 tháng.",  # 3
]


@asynccontextmanager
async def _kho_tam(conn: psycopg.AsyncConnection, tenant: UUID):
    """Một tài liệu + ``DOAN`` trong tenant, rollback khi ra khỏi khối."""
    async with conn.transaction(force_rollback=True):
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant),))
        doc = uuid4()
        await conn.execute(_CHEN_TAI_LIEU, (doc, f"Kho tạm {doc}", f"/tam/{doc}.txt"))
        for i, noi_dung in enumerate(DOAN):
            await conn.execute(_CHEN_DOAN, (doc, i, noi_dung))
        yield doc


async def _tim(conn, doc: UUID, tsquery: str) -> list[int]:
    cur = await conn.execute(_TIM, (doc, tsquery))
    return [r[0] for r in await cur.fetchall()]


# ── Không dấu ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("cau_hoi", "phai_khop"),
    [
        ("chinh sach doi tra", 0),
        ("giao hang da nang", 2),  # đ → d
        ("bao hanh may loc nuoc", 3),
    ],
)
async def test_cau_khong_dau_tim_duoc_doan_co_dau(ai_conn, tenant_a, cau_hoi, phai_khop):
    async with _kho_tam(ai_conn, tenant_a) as doc:
        assert phai_khop in await _tim(ai_conn, doc, build_tsquery(cau_hoi))


async def test_phia_hoi_khong_bo_dau_thi_truot(ai_conn, tenant_a):
    """Kiểm ngược "một hàm cho hai đầu": bỏ ``f_unaccent`` ở phía hỏi thì câu có dấu trượt hẳn.

    Chỉ mục đã bỏ dấu ('chinh', 'sach'); câu hỏi giữ dấu ('chính', 'sách') không bao giờ bằng.
    Không lỗi, không cảnh báo — chỉ có 0 dòng.
    """
    async with _kho_tam(ai_conn, tenant_a) as doc:
        q = build_tsquery("Chính sách đổi trả")
        assert 0 in await _tim(ai_conn, doc, q)  # đường đúng
        cur = await ai_conn.execute(
            "SELECT count(*) FROM knowledge.knowledge_chunks WHERE document_id = %s"
            " AND content_segmented @@ to_tsquery('simple', %s)",
            (doc, q),
        )
        assert (await cur.fetchone())[0] == 0  # quên bỏ dấu ở một đầu


# ── OR và <-> ────────────────────────────────────────────────────────────────


async def test_them_mot_tu_thua_or_van_khop_and_thi_rong(ai_conn, tenant_a):
    async with _kho_tam(ai_conn, tenant_a) as doc:
        q = build_tsquery("chính sách đổi trả laptop")  # kho không có chữ "laptop"
        assert 0 in await _tim(ai_conn, doc, q)
        assert await _tim(ai_conn, doc, q.replace(" | ", " & ")) == []


async def test_lien_ke_loai_doan_co_du_am_tiet_nhung_khong_lien_nhau(ai_conn, tenant_a):
    """Đoạn 1 có cả "sách" lẫn "chính" nhưng không phải từ "chính sách"."""
    async with _kho_tam(ai_conn, tenant_a) as doc:
        assert await _tim(ai_conn, doc, "(chính <-> sách)") == [0]
        assert await _tim(ai_conn, doc, "chính & sách") == [0, 1]  # không liền kề thì lẫn đoạn 1


@pytest.mark.parametrize("ma", ["NH-TL256I giá", "giá 6.790.000đ"])
async def test_ma_san_pham_va_so_tien(ai_conn, tenant_a, ma):
    async with _kho_tam(ai_conn, tenant_a) as doc:
        assert 2 in await _tim(ai_conn, doc, build_tsquery(ma))


# ── Cột GENERATED và hàm IMMUTABLE ───────────────────────────────────────────


async def test_content_segmented_la_cot_generated(ai_conn, tenant_a):
    """Ứng dụng không ghi được tsvector tính khác công thức — Postgres từ chối."""
    with pytest.raises(psycopg.errors.GeneratedAlways):
        async with ai_conn.transaction(force_rollback=True):
            await ai_conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_a),))
            await ai_conn.execute(
                "UPDATE knowledge.knowledge_chunks SET content_segmented = to_tsvector('x')"
            )


async def test_sua_content_thi_tsvector_tu_tinh_lai(ai_conn, tenant_a):
    """UC020 sửa nội dung đoạn: không có bước "nhớ cập nhật tsvector" nào để quên."""
    async with _kho_tam(ai_conn, tenant_a) as doc:
        await ai_conn.execute(
            "UPDATE knowledge.knowledge_chunks SET content = 'Máy giặt cửa trước'"
            " WHERE document_id = %s AND chunk_index = 3",
            (doc,),
        )
        assert await _tim(ai_conn, doc, build_tsquery("may giat")) == [3]


async def test_f_unaccent_la_immutable(ai_conn):
    cur = await ai_conn.execute(
        "SELECT provolatile FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace"
        " WHERE n.nspname = 'knowledge' AND p.proname = 'f_unaccent'"
    )
    assert (await cur.fetchone())[0] == "i"
    cur = await ai_conn.execute("SELECT knowledge.f_unaccent('Đổi trả ĐÀ NẴNG hoà thuỷ')")
    assert (await cur.fetchone())[0] == "Doi tra DA NANG hoa thuy"


# ── Cô lập tenant vẫn giữ ────────────────────────────────────────────────────


async def test_lan_tu_khoa_khong_thay_doan_cua_tenant_khac(ai_conn, tenant_a, tenant_b):
    """Làn từ khoá chịu RLS như mọi truy vấn khác: tenant B tìm cùng câu, không thấy gì của A."""
    async with ai_conn.transaction(force_rollback=True):
        await ai_conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_a),))
        doc = uuid4()
        await ai_conn.execute(_CHEN_TAI_LIEU, (doc, f"Riêng A {doc}", f"/tam/{doc}.txt"))
        await ai_conn.execute(_CHEN_DOAN, (doc, 0, "Bí mật kinh doanh của tenant A"))
        await ai_conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_b),))
        assert await _tim(ai_conn, doc, build_tsquery("bi mat kinh doanh")) == []
