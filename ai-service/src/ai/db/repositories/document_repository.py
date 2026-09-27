"""Truy cập ``knowledge.knowledge_documents`` — UC018 · UC019. [PRODUCTION]

Mọi hàm nhận một ``AsyncSession`` ĐÃ gắn tenant (``src.ai.db.session.get_tenant_session``).

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
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.exceptions import AiServiceError

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


# ── UC019 — nhận xử lý và đánh dấu thất bại ──────────────────────────────────


@dataclass(frozen=True, slots=True)
class TaiLieuCanNap:
    """Những gì bước phân tích cần biết về một tài liệu vừa nhận xử lý."""

    id: UUID
    file_path: str
    source_type: str


async def nhan_xu_ly(session: AsyncSession, document_id: UUID) -> TaiLieuCanNap | None:
    """Chuyển ``PENDING → PROCESSING`` CÓ ĐIỀU KIỆN; trả ``None`` nếu không chuyển được.

    ``None`` nghĩa là tài liệu không còn ``PENDING`` (một lượt khác đã nhận, hoặc đã xong),
    hoặc không nhìn thấy được qua RLS (không thuộc tenant của phiên). Cả hai trường hợp nơi gọi
    đều phải BỎ QUA, không báo lỗi.

    Một câu ``UPDATE … WHERE status = 'PENDING' RETURNING`` thay vì ``SELECT`` rồi ``UPDATE``:
    hai lượt cùng nhận một tài liệu (Kafka giao ít nhất một lần — nhận trùng là chắc chắn) thì
    Postgres khoá dòng cho lượt đầu; lượt sau chờ, đọc lại dòng sau khi lượt đầu commit, thấy
    ``status`` đã khác ``PENDING`` và cập nhật 0 dòng. SELECT-rồi-UPDATE thì cả hai cùng đọc
    thấy ``PENDING`` và cùng xử lý. Cách này dùng được cho cả hai phương án chống trùng đang chờ
    chốt ở ADR-0021 (Ngày 5).
    """
    ket_qua = await session.execute(
        text(
            """
            UPDATE knowledge.knowledge_documents
               SET status = 'PROCESSING', error_message = NULL
             WHERE id = :id AND status = 'PENDING'
            RETURNING id, file_path, source_type
            """
        ),
        {"id": document_id},
    )
    dong = ket_qua.one_or_none()
    return TaiLieuCanNap(*dong) if dong else None


async def danh_dau_that_bai(session: AsyncSession, document_id: UUID, loi: AiServiceError) -> None:
    """``FAILED`` kèm ``error_message = "{code}: {thông điệp}"``.

    Mã đứng ĐẦU chuỗi để dashboard và báo cáo lọc được theo tiền tố
    (``error_message LIKE 'PARSE_NO_TEXT_EXTRACTED%'``) mà không cần thêm cột; phần sau là câu
    hiển thị nguyên văn cho người dùng sửa tệp. ``ck_doc_failed`` (V202) được thoả vì chuỗi
    không bao giờ rỗng.
    """
    await session.execute(
        text(
            """
            UPDATE knowledge.knowledge_documents
               SET status = 'FAILED', error_message = :loi
             WHERE id = :id
            """
        ),
        {"id": document_id, "loi": f"{loi.code}: {loi}"},
    )
