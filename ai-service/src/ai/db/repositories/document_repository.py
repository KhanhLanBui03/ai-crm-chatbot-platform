"""Truy cập ``knowledge.knowledge_documents`` — UC018. [PRODUCTION]

Mọi hàm nhận một ``AsyncSession`` ĐÃ gắn tenant (``src.ai.db.session.get_tenant_session``).

Hai điều cố ý:

- **Không có ``WHERE tenant_id = …``** trong các câu đọc. RLS của V207 lọc thay
  (``.claude/rules/database.md``); tự lọc ở tầng ứng dụng tạo cảm giác an toàn giả và che mất
  lỗi cấu hình RLS. (Luật "lọc ``tenant_id`` ngay trong câu SQL" của ADR-0007 là cho truy vấn
  VECTOR ở ``knowledge_chunks`` — không áp cho bảng này.)
- **``tenant_id`` khi INSERT lấy từ ``ai.current_tenant()``**, không nhận làm tham số. Tenant
  của dòng mới vì thế LUÔN là tenant của phiên — không có tham số nào để truyền nhầm, và
  quên đặt tenant thì hàm đó ném 42501 ngay (V201).
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def tinh_version_ke_tiep(session: AsyncSession, title: str) -> int:
    """🖐 TỰ GÕ — Ngày 3, mục B. AI không viết thân hàm này.

    Hợp đồng:
        Vào: phiên đã gắn tenant · ``title`` đã chuẩn hoá NFC + strip (DTO lo việc đó).
        Ra:  ``1`` nếu tenant chưa có tài liệu nào mang tiêu đề này, ngược lại
             ``MAX(version) + 1`` — tức trùng tiêu đề thì TĂNG version, không ghi đè bản cũ.

    Bẫy phải xử lý: hai lượt tải cùng tiêu đề chạy ĐỒNG THỜI đều đọc ra cùng một MAX, cùng
    INSERT cùng version, và lượt sau đụng ``uq_doc_title_version``. Kết quả phải là version
    1 và 2, không phải một lượt 202 và một lượt 500.

    Nhớ: hàm này và ``them_tai_lieu_pending`` chạy trong CÙNG transaction (cùng ``session``).
    """
    raise NotImplementedError("🖐 Ngày 3 — tự gõ theo docstring")


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
