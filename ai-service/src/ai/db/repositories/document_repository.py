"""Truy cập ``knowledge.knowledge_documents`` — UC018 · UC019. [PRODUCTION]

Mọi hàm nhận một ``AsyncSession`` ĐÃ gắn tenant (``src.ai.db.session.get_tenant_session``) —
trừ ``tim_job_ket``, hàm duy nhất chạy trong phiên hệ thống (ADR-0024).

Ba điều cố ý:

- **Không có ``WHERE tenant_id = …``** trong các câu đọc. RLS của V207 lọc thay
  (``.claude/rules/database.md``); tự lọc ở tầng ứng dụng tạo cảm giác an toàn giả và che mất
  lỗi cấu hình RLS. (Luật "lọc ``tenant_id`` ngay trong câu SQL" của ADR-0007 là cho truy vấn
  VECTOR ở ``knowledge_chunks`` — không áp cho bảng này.)
- **``tenant_id`` khi INSERT lấy từ ``ai.current_tenant()``**, không nhận làm tham số. Tenant
  của dòng mới vì thế LUÔN là tenant của phiên — không có tham số nào để truyền nhầm, và
  quên đặt tenant thì hàm đó ném 42501 ngay (V201).
- **Cấp version dưới khoá advisory** — xem ``tinh_version_ke_tiep``.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.exceptions import AiServiceError, IngestOwnershipLostError

# Không gian khoá advisory riêng cho việc cấp version tài liệu (18 = UC018). Dạng hai tham số
# (int4, int4) tách khỏi khoá của nơi khác trong cùng CSDL — Flyway cũng dùng khoá advisory.
_KHONG_GIAN_KHOA_VERSION = 18


async def tinh_version_ke_tiep(session: AsyncSession, title: str) -> int:
    """Version kế tiếp cho ``title`` trong tenant của phiên: ``1`` nếu chưa có, ngược lại
    ``MAX(version) + 1`` — trùng tiêu đề thì TĂNG version, không ghi đè bản cũ.

    ``title`` phải đã chuẩn hoá NFC + strip (DTO lo), nếu không hai cách gõ cùng một tiêu đề
    sẽ thành hai chuỗi version riêng.

    BẪY ĐỒNG THỜI: hai lượt tải cùng tiêu đề cùng đọc một MAX, cùng INSERT một version, lượt
    sau đụng ``uq_doc_title_version`` thành 500. ``SELECT … FOR UPDATE`` không cứu được: khi
    tiêu đề chưa có dòng nào thì không có dòng nào để khoá. Nên khoá một CÁI TÊN thay vì một
    dòng: ``pg_advisory_xact_lock`` trên (tenant, tiêu đề). Lượt thứ hai chờ tới khi lượt đầu
    commit, rồi mới đọc MAX — lúc đó đã thấy dòng lượt đầu vừa ghi.

    Ba điều kiện để khoá đúng:

    - **Khoá tính bằng ``hashtext`` của Postgres, không bằng ``hash()`` của Python.** ``hash()``
      của chuỗi bị ngẫu nhiên hoá theo từng tiến trình: hai replica ai-service khoá hai số khác
      nhau cho cùng một tiêu đề và không chặn được nhau — test một tiến trình không bao giờ lộ.
    - **Khoá gồm cả tenant** (``ai.current_tenant()``): hai tenant cùng tải "Chính sách đổi trả"
      không phải chờ nhau. Chưa đặt tenant thì hàm đó ném 42501 ngay (V201).
    - **Cùng transaction với INSERT** (cùng ``session``): khoá ``_xact_`` nhả lúc commit, tức
      SAU khi dòng mới đã ghi. Mức cô lập phải là READ COMMITTED (mặc định): mỗi câu lệnh lấy
      ảnh chụp mới nên câu MAX thấy dòng vừa commit. Ở REPEATABLE READ, ảnh chụp chốt từ câu
      đầu tiên của transaction và câu MAX sẽ không thấy — khoá thành vô dụng.

    Không có ``WHERE tenant_id`` trong câu MAX: RLS lọc thay (``.claude/rules/database.md``).
    """
    await session.execute(
        text(
            "SELECT pg_advisory_xact_lock("
            " :khong_gian, hashtext(ai.current_tenant()::text || '/' || :title))"
        ),
        {"khong_gian": _KHONG_GIAN_KHOA_VERSION, "title": title},
    )
    ket_qua = await session.execute(
        text(
            "SELECT COALESCE(MAX(version), 0) + 1"
            " FROM knowledge.knowledge_documents WHERE title = :title"
        ),
        {"title": title},
    )
    return ket_qua.scalar_one()


async def them_tai_lieu_pending(
    session: AsyncSession,
    *,
    title: str,
    description: str | None,
    language: str,
    source_type: str,
    file_name: str,
    file_path: str,
    mime_type: str,
    file_size_bytes: int,
    version: int,
    uploaded_by: UUID | None,
) -> UUID:
    """Ghi một tài liệu ở trạng thái ``PENDING``, trả về ``id`` vừa sinh.

    Ràng buộc V202 được thoả sẵn: ``ck_doc_source`` (tệp thì ``file_path`` khác NULL) và
    ``ck_doc_failed`` (``PENDING`` không cần ``error_message``). ``session.execute`` với
    ``text()`` gửi câu lệnh đi NGAY — vi phạm ràng buộc nổ tại đây, bên trong handler, chứ
    không đợi tới lúc commit.
    """
    ket_qua = await session.execute(
        text(
            """
            INSERT INTO knowledge.knowledge_documents (
                tenant_id, title, description, language, source_type,
                file_name, file_path, mime_type, file_size_bytes,
                status, version, uploaded_by
            ) VALUES (
                ai.current_tenant(), :title, :description, :language, :source_type,
                :file_name, :file_path, :mime_type, :file_size_bytes,
                'PENDING', :version, :uploaded_by
            )
            RETURNING id
            """
        ),
        {
            "title": title,
            "description": description,
            "language": language,
            "source_type": source_type,
            "file_name": file_name,
            "file_path": file_path,
            "mime_type": mime_type,
            "file_size_bytes": file_size_bytes,
            "version": version,
            "uploaded_by": uploaded_by,
        },
    )
    return ket_qua.scalar_one()


# ── UC019 — vòng đời nạp: nhận việc, ghi chặng, kết thúc (ADR-0024) ─────────
#
# Mọi hàm ghi SAU bước nhận việc đều có điều kiện "status = 'PROCESSING' AND attempt_count = :lan"
# — THẺ SỞ HỮU. Bộ quét trả tài liệu về hàng đợi và lượt khác nhận lại thì attempt_count tăng; lượt
# cũ (tiến trình treo rồi tỉnh lại) cập nhật 0 dòng và phải dừng, không được ghi đè lượt mới.
#
# Câu UPDATE có điều kiện đó còn KHOÁ DÒNG tới hết transaction: bộ quét muốn tước quyền phải chờ,
# và khi nó đọc lại thì updated_at vừa được làm mới — không còn "kẹt" nữa. Nhịp tim và thẻ sở hữu
# vì thế là cùng một câu lệnh.

_DIEU_KIEN_SO_HUU = "id = :id AND status = 'PROCESSING' AND attempt_count = :lan"


@dataclass(frozen=True, slots=True)
class TaiLieuCanNap:
    """Những gì lượt nạp cần biết về một tài liệu vừa nhận xử lý."""

    id: UUID
    file_path: str
    source_type: str
    # attempt_count SAU khi tăng — lượt thứ mấy, và là thẻ sở hữu của lượt này.
    lan: int


async def nhan_xu_ly(session: AsyncSession, document_id: UUID) -> TaiLieuCanNap | None:
    """Chuyển ``PENDING → PROCESSING`` CÓ ĐIỀU KIỆN, tăng ``attempt_count``; ``None`` nếu không
    chuyển được.

    ``None`` nghĩa là tài liệu không còn ``PENDING`` (một lượt khác đã nhận, hoặc đã xong),
    hoặc không nhìn thấy được qua RLS (không thuộc tenant của phiên). Cả hai trường hợp nơi gọi
    đều phải BỎ QUA, không báo lỗi.

    Một câu ``UPDATE … WHERE status = 'PENDING' RETURNING`` thay vì ``SELECT`` rồi ``UPDATE``:
    hai lượt cùng nhận một tài liệu (Kafka giao ít nhất một lần — nhận trùng là chắc chắn) thì
    Postgres khoá dòng cho lượt đầu; lượt sau chờ, đọc lại dòng sau khi lượt đầu commit, thấy
    ``status`` đã khác ``PENDING`` và cập nhật 0 dòng. SELECT-rồi-UPDATE thì cả hai cùng đọc
    thấy ``PENDING`` và cùng xử lý.

    Xoá sạch dấu vết lượt trước (``error_message``, ``chunk_count``, ``indexed_at``) ngay tại đây:
    lượt thử lại bắt đầu từ trang trắng.
    """
    ket_qua = await session.execute(
        text(
            """
            UPDATE knowledge.knowledge_documents
               SET status = 'PROCESSING', error_message = NULL,
                   attempt_count = attempt_count + 1, ingest_step = 'EXTRACTING',
                   ingest_started_at = now(), chunk_count = 0, indexed_at = NULL
             WHERE id = :id AND status = 'PENDING'
            RETURNING id, file_path, source_type, attempt_count
            """
        ),
        {"id": document_id},
    )
    dong = ket_qua.one_or_none()
    return TaiLieuCanNap(*dong) if dong else None


async def danh_dau_buoc(
    session: AsyncSession,
    document_id: UUID,
    lan: int,
    buoc: str,
    *,
    chunk_count: int | None = None,
) -> None:
    """Ghi chặng đang chạy — đồng thời là NHỊP TIM (trigger V207 làm mới ``updated_at``) và phép
    kiểm thẻ sở hữu. Ném ``IngestOwnershipLostError`` nếu lượt này đã bị tước quyền.

    ``chunk_count`` trong lúc nạp là số đoạn DỰ KIẾN — mẫu số của thanh tiến độ SCR033. Tới
    ``READY`` nó bằng số đoạn thật đã kiểm đếm (``hoan_tat``).
    """
    ket_qua = await session.execute(
        text(
            f"""
            UPDATE knowledge.knowledge_documents
               SET ingest_step = :buoc, chunk_count = COALESCE(:chunk_count, chunk_count)
             WHERE {_DIEU_KIEN_SO_HUU}
            """
        ),
        {"id": document_id, "lan": lan, "buoc": buoc, "chunk_count": chunk_count},
    )
    if ket_qua.rowcount == 0:
        raise IngestOwnershipLostError(f"Lượt {lan} không còn giữ tài liệu {document_id}")


async def hoan_tat(
    session: AsyncSession, document_id: UUID, lan: int, so_doan: int
) -> UUID | None:
    """``PROCESSING → READY`` + ``chunk_count`` + ``indexed_at``. Có thẻ sở hữu.

    Nếu dòng này là BẢN BÓNG của một lượt nạp lại (``replaces_document_id``, V213, ADR-0031): cũng
    trong ``session`` này — tức CÙNG transaction — xoá đoạn của bản cũ rồi chuyển nó ``ARCHIVED``.
    Người đọc khác (truy hồi) thấy hoặc trạng thái trước (bản cũ READY + đoạn cũ), hoặc trạng thái
    sau (bản mới READY + đoạn mới): không có khoảnh khắc nào tài liệu vắng khỏi kho, và không có
    khoảnh khắc nào hai bản cùng được truy hồi. Trả ``id`` bản cũ vừa thay, hoặc ``None``.

    Bản cũ chỉ bị thay khi nó còn ``READY`` — gỡ bản cũ trong lúc đang nạp lại đã bị chặn bằng 409
    (``xoa_khoi_chi_muc``), điều kiện này là lưới đỡ thứ hai.
    """
    ket_qua = await session.execute(
        text(
            f"""
            UPDATE knowledge.knowledge_documents
               SET status = 'READY', ingest_step = NULL, chunk_count = :so_doan,
                   indexed_at = now(), error_message = NULL
             WHERE {_DIEU_KIEN_SO_HUU}
            RETURNING replaces_document_id
            """
        ),
        {"id": document_id, "lan": lan, "so_doan": so_doan},
    )
    dong = ket_qua.one_or_none()
    if dong is None:
        raise IngestOwnershipLostError(f"Lượt {lan} không còn giữ tài liệu {document_id}")
    ban_cu = dong[0]
    if ban_cu is None:
        return None
    # Xoá đoạn TRƯỚC, rồi mới ARCHIVED — cùng thứ tự với gỡ thủ công (xoa_khoi_chi_muc).
    await session.execute(
        text(
            """
            DELETE FROM knowledge.knowledge_chunks c
             USING knowledge.knowledge_documents d
             WHERE c.document_id = d.id AND d.id = :cu AND d.status = 'READY'
            """
        ),
        {"cu": ban_cu},
    )
    da_thay = await session.execute(
        text(
            """
            UPDATE knowledge.knowledge_documents
               SET status = 'ARCHIVED', chunk_count = 0
             WHERE id = :cu AND status = 'READY'
            """
        ),
        {"cu": ban_cu},
    )
    return ban_cu if da_thay.rowcount else None


async def tra_ve_hang_doi(session: AsyncSession, document_id: UUID, lan: int) -> bool:
    """``PROCESSING → PENDING`` sau lỗi tạm thời, giữ nguyên ``attempt_count``. Có thẻ sở hữu.

    ``False`` nếu lượt này đã mất quyền — khi đó KHÔNG đụng vào tài liệu.
    """
    ket_qua = await session.execute(
        text(
            f"""
            UPDATE knowledge.knowledge_documents
               SET status = 'PENDING', ingest_step = NULL, chunk_count = 0
             WHERE {_DIEU_KIEN_SO_HUU}
            """
        ),
        {"id": document_id, "lan": lan},
    )
    return ket_qua.rowcount > 0


async def danh_dau_that_bai(
    session: AsyncSession, document_id: UUID, loi: AiServiceError, *, lan: int
) -> bool:
    """``FAILED`` kèm ``error_message = "{code}: {thông điệp}"``. Có thẻ sở hữu; ``False`` nếu đã
    mất quyền.

    Mã đứng ĐẦU chuỗi để dashboard và báo cáo lọc được theo tiền tố
    (``error_message LIKE 'PARSE_NO_TEXT_EXTRACTED%'``) mà không cần thêm cột; phần sau là câu
    hiển thị nguyên văn cho người dùng sửa tệp. ``ck_doc_failed`` (V202) được thoả vì chuỗi
    không bao giờ rỗng.

    GIỮ NGUYÊN ``ingest_step``: nó cho biết tài liệu hỏng ở chặng nào (SCR033 tô đỏ đúng bước đó).
    """
    ket_qua = await session.execute(
        text(
            f"""
            UPDATE knowledge.knowledge_documents
               SET status = 'FAILED', error_message = :loi, chunk_count = 0
             WHERE {_DIEU_KIEN_SO_HUU}
            """
        ),
        {"id": document_id, "lan": lan, "loi": f"{loi.code}: {loi}"},
    )
    return ket_qua.rowcount > 0


# ── Bộ quét job kẹt (ADR-0024) ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class JobKet:
    """Một dòng của ``knowledge.tim_job_ket`` — chỉ định danh, không nội dung."""

    tenant_id: UUID
    document_id: UUID
    status: str
    attempt_count: int


async def tim_job_ket(session: AsyncSession, qua_han_s: float, toi_da: int) -> list[JobKet]:
    """Gọi hàm ``SECURITY DEFINER`` của V211 — chỗ DUY NHẤT nhìn xuyên tenant.

    ``session`` phải là phiên KHÔNG gắn tenant (``get_system_session``): hàm tự vượt RLS bằng
    quyền chủ hàm, còn mọi bảng khác trong phiên đó vẫn ném 42501.
    """
    ket_qua = await session.execute(
        text("SELECT * FROM knowledge.tim_job_ket(make_interval(secs => :s), :n)"),
        {"s": qua_han_s, "n": toi_da},
    )
    return [JobKet(*dong) for dong in ket_qua.all()]


async def xu_ly_job_ket(
    session: AsyncSession,
    document_id: UUID,
    *,
    qua_han_s: float,
    tran_luot: int,
    loi: AiServiceError,
) -> str | None:
    """Tài liệu ``PROCESSING`` quá hạn nhịp tim: còn lượt thì về ``PENDING``, hết lượt thì
    ``FAILED``.

    Trả trạng thái mới, hoặc ``None`` nếu tài liệu không còn kẹt — nó đã đổi trạng thái, hoặc
    vừa có nhịp tim, trong khoảng giữa lúc ``tim_job_ket`` đọc và lúc này. Điều kiện quá hạn được
    KIỂM LẠI trong chính câu UPDATE (dòng bị khoá) — không tin kết quả đọc lúc trước.
    """
    ket_qua = await session.execute(
        text(
            """
            UPDATE knowledge.knowledge_documents
               SET status        = CASE WHEN attempt_count < :tran THEN 'PENDING' ELSE 'FAILED' END,
                   error_message = CASE WHEN attempt_count < :tran THEN NULL ELSE :loi END,
                   ingest_step   = CASE WHEN attempt_count < :tran THEN NULL ELSE ingest_step END,
                   chunk_count   = 0
             WHERE id = :id AND status = 'PROCESSING'
               AND updated_at < now() - make_interval(secs => :qua_han)
            RETURNING status
            """
        ),
        {"id": document_id, "tran": tran_luot, "qua_han": qua_han_s, "loi": f"{loi.code}: {loi}"},
    )
    return ket_qua.scalar_one_or_none()


# ── Tiến độ nạp — SCR033 ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TienDoTaiLieu:
    """Ảnh chụp một tài liệu cho endpoint tiến độ. ``so_doan_da_ghi`` đếm thật trong
    ``knowledge_chunks`` — không có cột "đã nhúng bao nhiêu" nào để lệch với dữ liệu."""

    id: UUID
    title: str
    status: str
    ingest_step: str | None
    attempt_count: int
    chunk_count: int
    so_doan_da_ghi: int
    error_message: str | None
    created_at: datetime
    ingest_started_at: datetime | None
    indexed_at: datetime | None
    updated_at: datetime


async def lay_tien_do(session: AsyncSession, document_id: UUID) -> TienDoTaiLieu | None:
    """``None`` nếu không thấy — không tồn tại HOẶC thuộc tenant khác (RLS che cả hai như nhau).

    Đếm đoạn không lọc ``tenant_id`` bằng tay: đây không phải truy vấn vector (ADR-0007 không áp),
    RLS của ``knowledge_chunks`` lọc thay, và chỉ mục ``ix_chunk_tenant_doc`` phủ được câu đếm.
    """
    ket_qua = await session.execute(
        text(
            """
            SELECT d.id, d.title, d.status, d.ingest_step, d.attempt_count, d.chunk_count,
                   (SELECT count(*) FROM knowledge.knowledge_chunks c WHERE c.document_id = d.id),
                   d.error_message, d.created_at, d.ingest_started_at, d.indexed_at, d.updated_at
              FROM knowledge.knowledge_documents d
             WHERE d.id = :id
            """
        ),
        {"id": document_id},
    )
    dong = ket_qua.one_or_none()
    return TienDoTaiLieu(*dong) if dong else None


# ── UC020 — quản lý kho tri thức (ADR-0031) ─────────────────────────────────


@dataclass(frozen=True, slots=True)
class TaiLieu:
    """Một tài liệu cho SCR030/SCR031 — KHÔNG có ``file_path`` (đường dẫn kho S3 là chi tiết nội
    bộ, java-core đã biết từ lúc tải lên)."""

    id: UUID
    title: str
    description: str | None
    language: str
    source_type: str
    file_name: str | None
    mime_type: str | None
    file_size_bytes: int | None
    status: str
    version: int
    chunk_count: int
    error_message: str | None
    uploaded_by: UUID | None
    indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Dòng này là bản bóng nạp lại của tài liệu nào (V213), nếu có.
    replaces_document_id: UUID | None
    # Khách hàng mà tài liệu này mang dữ liệu cá nhân của họ (V214, UC041), nếu có.
    contact_id: UUID | None
    # Bản bóng ĐANG nạp lại tài liệu này (PENDING/PROCESSING), nếu có — job_id để xem tiến độ.
    reindex_document_id: UUID | None


_COT_TAI_LIEU = """
    d.id, d.title, d.description, d.language, d.source_type, d.file_name, d.mime_type,
    d.file_size_bytes, d.status, d.version, d.chunk_count, d.error_message, d.uploaded_by,
    d.indexed_at, d.created_at, d.updated_at, d.replaces_document_id, d.contact_id,
    (SELECT b.id FROM knowledge.knowledge_documents b
      WHERE b.replaces_document_id = d.id AND b.status IN ('PENDING', 'PROCESSING'))
"""

# Biểu thức PHẢI trùng từng ký tự với chỉ mục ix_doc_tim_kiem (V213) — lệch là quét toàn bảng.
_BIEU_THUC_TIM = (
    "lower(knowledge.f_unaccent("
    "d.title || ' ' || coalesce(d.description, '') || ' ' || coalesce(d.file_name, '')))"
)


def thoat_like(tu_khoa: str) -> str:
    """``%`` và ``_`` trong từ khoá là ký tự thường, không phải ký tự đại diện của LIKE."""
    return tu_khoa.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def danh_sach(
    session: AsyncSession,
    *,
    tu_khoa: str | None,
    status: str | None,
    source_type: str | None,
    gioi_han: int,
    bo_qua: int,
) -> tuple[list[TaiLieu], int]:
    """SCR030 — phân trang, lọc, tìm trên tiêu đề + mô tả + tên tệp, không phân biệt hoa thường
    và dấu. Mới nhất trước (đặc tả UC020).

    Không lọc ``status`` thì ẨN ``ARCHIVED``: tài liệu đã gỡ không còn chi phối câu trả lời nào,
    để chúng lẫn vào danh sách là làm quản trị viên tưởng chúng vẫn đang được dùng. Muốn xem thì
    lọc ``status=ARCHIVED``.

    ``tu_khoa`` phải ĐÃ qua ``normalize_vi`` (tầng service) — cùng hàm chuẩn hoá lúc nạp.
    """
    dieu_kien = ["d.status <> 'ARCHIVED'" if status is None else "d.status = :status"]
    tham_so: dict[str, object] = {"gioi_han": gioi_han, "bo_qua": bo_qua}
    if status is not None:
        tham_so["status"] = status
    if source_type is not None:
        dieu_kien.append("d.source_type = :source_type")
        tham_so["source_type"] = source_type
    if tu_khoa:
        dieu_kien.append(
            f"{_BIEU_THUC_TIM} LIKE '%' || lower(knowledge.f_unaccent(:tu_khoa)) || '%' "
            "ESCAPE '\\'"
        )
        tham_so["tu_khoa"] = thoat_like(tu_khoa)
    ket_qua = await session.execute(
        text(
            f"""
            SELECT {_COT_TAI_LIEU}, count(*) OVER ()
              FROM knowledge.knowledge_documents d
             WHERE {' AND '.join(dieu_kien)}
             ORDER BY d.created_at DESC, d.id
             LIMIT :gioi_han OFFSET :bo_qua
            """
        ),
        tham_so,
    )
    dong = ket_qua.all()
    return [TaiLieu(*d[:-1]) for d in dong], (dong[0][-1] if dong else 0)


async def lay_tai_lieu(
    session: AsyncSession, document_id: UUID, *, khoa: bool = False
) -> TaiLieu | None:
    """``None`` = không tồn tại HOẶC thuộc tenant khác — RLS che cả hai như nhau (404 cho cả hai).

    ``khoa=True``: ``FOR UPDATE`` — thao tác đổi trạng thái (gỡ, nạp lại) khoá dòng tới hết
    transaction, để một lượt nạp không chen vào giữa lúc kiểm và lúc ghi.
    """
    ket_qua = await session.execute(
        text(
            f"SELECT {_COT_TAI_LIEU} FROM knowledge.knowledge_documents d WHERE d.id = :id"
            + (" FOR UPDATE OF d" if khoa else "")
        ),
        {"id": document_id},
    )
    dong = ket_qua.one_or_none()
    return TaiLieu(*dong) if dong else None


async def cap_nhat_sieu_du_lieu(
    session: AsyncSession, document_id: UUID, thay_doi: dict[str, object]
) -> None:
    """``title``, ``description`` và ``contact_id`` (V214) — KHÔNG đụng ``knowledge_chunks`` (chỉ
    mục vector giữ nguyên). Trùng ``(tenant, title, version)`` thì ``uq_doc_title_version`` nổ
    ``IntegrityError`` ngay tại câu lệnh — tầng service dịch thành 422.
    """
    cot = [c for c in ("title", "description", "contact_id") if c in thay_doi]
    if not cot:
        return
    await session.execute(
        text(
            "UPDATE knowledge.knowledge_documents SET "
            + ", ".join(f"{c} = :{c}" for c in cot)
            + " WHERE id = :id"
        ),
        {"id": document_id, **{c: thay_doi[c] for c in cot}},
    )


async def xoa_khoi_chi_muc(session: AsyncSession, document_id: UUID) -> int:
    """Gỡ một tài liệu khỏi chỉ mục: xoá ĐOẠN trước, rồi mới ``ARCHIVED``. Trả số đoạn đã xoá.

    Hai câu lệnh trong CÙNG transaction của ``session``: xoá đoạn hỏng thì câu thứ hai không bao
    giờ chạy và transaction rollback — tài liệu giữ nguyên trạng thái (đặc tả UC020 luồng phụ 7.2).
    Thứ tự vẫn có nghĩa với người đọc log và với người viết lại hàm này thành hai transaction: đánh
    dấu ``ARCHIVED`` trước rồi xoá hỏng là tài liệu biến khỏi giao diện trong khi vector vẫn nằm
    trong chỉ mục và vẫn chi phối câu trả lời.

    Nơi gọi đã khoá dòng (``lay_tai_lieu(khoa=True)``) và đã kiểm trạng thái.
    """
    xoa = await session.execute(
        text("DELETE FROM knowledge.knowledge_chunks WHERE document_id = :id"),
        {"id": document_id},
    )
    await session.execute(
        text(
            """
            UPDATE knowledge.knowledge_documents
               SET status = 'ARCHIVED', chunk_count = 0, ingest_step = NULL
             WHERE id = :id
            """
        ),
        {"id": document_id},
    )
    return xoa.rowcount


async def tao_ban_bong(session: AsyncSession, cu: TaiLieu) -> tuple[UUID, int]:
    """Bản bóng ``PENDING`` của tài liệu ``cu`` (ADR-0031): cùng tệp, cùng siêu dữ liệu, version kế
    tiếp, ``replaces_document_id = cu.id``. Trả ``(id, version)``.

    Chép cả ``contact_id`` (V214): bản bóng mang đúng dữ liệu của bản cũ — mất liên kết ở đây là
    UC041 bỏ sót bản mới nhất của một tài liệu chứa dữ liệu cá nhân.

    Bộ quét job kẹt nhặt nó trong ≤ 1 chu kỳ (V213). Đã có một lượt nạp lại đang chạy thì
    ``uq_doc_mot_luot_nap_lai`` nổ ``IntegrityError`` — tầng service dịch thành 409.
    """
    version = await tinh_version_ke_tiep(session, cu.title)
    ket_qua = await session.execute(
        text(
            """
            INSERT INTO knowledge.knowledge_documents (
                tenant_id, title, description, language, source_type, file_name, file_path,
                source_url, mime_type, file_size_bytes, status, version, uploaded_by,
                replaces_document_id, contact_id
            )
            SELECT ai.current_tenant(), d.title, d.description, d.language, d.source_type,
                   d.file_name, d.file_path, d.source_url, d.mime_type, d.file_size_bytes,
                   'PENDING', :version, d.uploaded_by, d.id, d.contact_id
              FROM knowledge.knowledge_documents d
             WHERE d.id = :id
            RETURNING id
            """
        ),
        {"id": cu.id, "version": version},
    )
    return ket_qua.scalar_one(), version


async def tai_lieu_can_nap_lai(session: AsyncSession) -> list[TaiLieu]:
    """Mọi tài liệu ``READY`` của tenant chưa có lượt nạp lại đang chạy — đầu vào của nạp lại toàn
    kho khi đổi mô hình nhúng (UC020 luồng phụ 6.1). Khoá dòng cho tới khi bản bóng được tạo."""
    ket_qua = await session.execute(
        text(
            f"""
            SELECT {_COT_TAI_LIEU}
              FROM knowledge.knowledge_documents d
             WHERE d.status = 'READY'
               AND NOT EXISTS (
                   SELECT 1 FROM knowledge.knowledge_documents b
                    WHERE b.replaces_document_id = d.id AND b.status IN ('PENDING', 'PROCESSING'))
             ORDER BY d.created_at
               FOR UPDATE OF d
            """
        ),
    )
    return [TaiLieu(*d) for d in ket_qua.all()]


# ── UC041 — xoá dữ liệu cá nhân (ADR-0033) ───────────────────────────────────


@dataclass(frozen=True, slots=True)
class KetQuaXoaTaiLieu:
    so_tai_lieu: int
    so_doan: int
    # Đường dẫn tệp gốc (``s3://…``) đã mất dòng trỏ tới — nơi gọi xoá object SAU khi commit.
    cac_tep: list[str]


async def xoa_tai_lieu_theo_khach(session: AsyncSession, contact_id: UUID) -> KetQuaXoaTaiLieu:
    """Xoá CỨNG mọi tài liệu gắn ``contact_id`` + mọi đoạn của chúng, trong transaction của
    ``session``. Gỡ khỏi chỉ mục (``ARCHIVED``) không đủ: tiêu đề, mô tả và tệp gốc vẫn còn.

    Tính cả CÙNG DÒNG DÕI — mọi dòng trỏ cùng ``file_path`` với một dòng của khách (bản bóng nạp
    lại, bản cũ đã ``ARCHIVED``): chúng là cùng một tệp, và ``contact_id`` có thể chỉ được gắn lên
    bản mới nhất sau khi bản cũ đã lưu trữ.

    Xoá đoạn TRƯỚC rồi xoá tài liệu — ``ON DELETE CASCADE`` của V203 cũng làm được, nhưng đếm
    tường minh mới có số đoạn cho biên bản xoá (đặc tả UC041: tiến độ theo từng bảng). RLS chặn
    tenant khác; ``contact_id`` của tenant khác không khớp dòng nào.
    """
    muc_tieu = """
        SELECT d.id FROM knowledge.knowledge_documents d
         WHERE d.contact_id = :contact_id
            OR d.file_path IN (SELECT k.file_path FROM knowledge.knowledge_documents k
                                WHERE k.contact_id = :contact_id)
    """
    doan = await session.execute(
        text(f"DELETE FROM knowledge.knowledge_chunks WHERE document_id IN ({muc_tieu})"),
        {"contact_id": contact_id},
    )
    tai_lieu = await session.execute(
        text(
            f"""
            DELETE FROM knowledge.knowledge_documents
             WHERE id IN ({muc_tieu})
            RETURNING file_path
            """
        ),
        {"contact_id": contact_id},
    )
    dong = tai_lieu.all()
    return KetQuaXoaTaiLieu(len(dong), doan.rowcount, sorted({d[0] for d in dong if d[0]}))
