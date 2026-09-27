"""Cô lập tenant ở TẦNG KHO LƯU TRỮ — UC018. [PRODUCTION]

java-core lưu tệp vào ``{kb_storage_root}/{tenant_id}/…`` trên volume dùng chung rồi gửi URI
sang đây. RLS chỉ bảo vệ các dòng trong CSDL — nó không biết gì về hệ thống tệp. Nếu
ai-service mở bất cứ đường dẫn nào được gửi tới, thì một URI trỏ sang thư mục của tenant
khác sẽ được đọc, cắt đoạn, nhúng vector rồi ghi vào kho tri thức của tenant đang gọi —
đúng kiểu rò rỉ chéo tenant mà chỉ số "rò rỉ = 0" (§1.6) phải chặn.
"""

from pathlib import Path


def kiem_uri_thuoc_tenant(file_uri: str, tenant_id: str, storage_root: Path) -> Path:
    """🖐 TỰ GÕ — Ngày 3, mục B. AI không viết thân hàm này.

    Hợp đồng:
        Vào:
            ``file_uri``      chuỗi java-core gửi (``KbDocumentCreate.file_uri``) — KHÔNG tin
            ``tenant_id``     tenant đã xác thực, từ header ``X-Tenant-Id``
            ``storage_root``  ``Settings.kb_storage_root``
        Ra:
            ``Path`` đã chuẩn hoá, chắc chắn nằm dưới ``storage_root / tenant_id``.
            Hàm gọi phía sau (``mime.nhan_dien_tep``) mở đúng đường dẫn này.
        Ném:
            ``ForbiddenFileUriError`` (``src/ai/exceptions.py``) cho MỌI ca dưới đây.

    Các ca phải chặn — test tích hợp Ngày 3 sẽ kiểm từng ca:
        1. URI trỏ vào thư mục của tenant KHÁC
        2. URI có ``..`` thoát ra khỏi thư mục của tenant
        3. Symlink nằm trong thư mục tenant nhưng trỏ ra ngoài
        4. Scheme không phải tệp cục bộ (``http://``, ``s3://``…)
        5. Tên thư mục chỉ TRÙNG TIỀN TỐ chuỗi với tenant (``/data/kb/1111…1111-evil/…``)

    Chưa quyết (ghi vào docstring khi bạn quyết): nhận cả ``file://…`` lẫn đường dẫn tuyệt
    đối trần, hay chỉ một dạng? Chốt cùng phần java-core ở mục C.

    Câu hội đồng sẽ hỏi: truy vấn đã lọc ``tenant_id`` rồi, vì sao còn cần hàm này?
    """
    raise NotImplementedError("🖐 Ngày 3 — tự gõ theo docstring")
