"""Ngoại lệ của tầng ứng dụng.

MẪU. Mỗi ngoại lệ mang một ``code`` nghiệp vụ; tầng ``api/`` dịch nó sang mã HTTP ở
``src/api/errors.py``. Không ném ``HTTPException`` từ trong ``src/ai/`` — tầng này không được
biết mình đang chạy sau HTTP hay sau một consumer Kafka.

``code`` thuộc về nghiệp vụ, mã HTTP thì không: worker cũng dùng ``code`` để ghi
``error_message`` khi chuyển tài liệu sang ``FAILED``, mà worker không có mã HTTP nào cả.
"""


class AiServiceError(Exception):
    """Gốc của mọi ngoại lệ do ai-service chủ động ném ra."""

    code: str = "INTERNAL_ERROR"


class TenantContextMissingError(AiServiceError):
    """Không xác định được tenant cho request. KHÔNG được xử lý tiếp khi thiếu (ADR-0001)."""

    code = "TENANT_CONTEXT_MISSING"


class InsufficientGroundingError(AiServiceError):
    """Không đủ căn cứ để trả lời — chuyển sang hành vi từ chối (thí nghiệm E7)."""


class ToolCallBlockedError(AiServiceError):
    """Lớp bảo vệ chặn một lượt gọi tool. Ghi kiểm toán rồi mới ném (bề mặt T4)."""


# ── Kho tri thức — UC018 ─────────────────────────────────────────────────────
# Mã lấy nguyên văn từ mục "Ngoại lệ và mã lỗi" của đặc tả UC018, trừ hai mã đánh dấu
# [CẦN XÁC NHẬN] — đặc tả chưa nói tới hai tình huống đó.


class FileTooLargeError(AiServiceError):
    """Tệp vượt hạn dung lượng. java-core đã chặn trước; đây là lớp phòng thủ thứ hai."""

    code = "FILE_TOO_LARGE"


class UnsupportedFormatError(AiServiceError):
    """Đuôi tệp không nằm trong danh sách nhận, hoặc nội dung thật không khớp với đuôi."""

    code = "UNSUPPORTED_FORMAT"


class ForbiddenFileUriError(AiServiceError):
    """URI trỏ ra ngoài vùng của tenant đang gọi. [CẦN XÁC NHẬN] mã — đặc tả chưa có.

    Đây là dấu hiệu tấn công (hoặc lỗi nghiêm trọng ở java-core), không phải lỗi nhập liệu —
    nên tách khỏi ``INVALID_METADATA`` và luôn ghi log cảnh báo.
    """

    code = "FORBIDDEN_FILE_URI"


class StoredFileNotFoundError(AiServiceError):
    """URI hợp lệ nhưng kho S3 không có object đó. [CẦN XÁC NHẬN] mã — đặc tả chưa có.

    java-core ghi tệp XONG mới gọi ai-service, nên ca này nghĩa là hai bên lệch nhau
    (sai bucket, sai key, hoặc object bị xoá giữa chừng).
    """

    code = "FILE_NOT_FOUND"


class StorageUnavailableError(AiServiceError):
    """Không nói chuyện được với kho S3: mất kết nối, hết thời gian chờ, sai quyền truy cập.

    Lỗi của hạ tầng, không phải của phía gọi — tách riêng để java-core biết nên thử lại sau
    thay vì báo người dùng sửa tệp.
    """

    code = "STORAGE_UNAVAILABLE"
