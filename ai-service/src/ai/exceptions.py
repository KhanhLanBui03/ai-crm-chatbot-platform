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


# ── Nạp tài liệu — UC019 ─────────────────────────────────────────────────────
# Ba mã này KHÔNG có mã HTTP: phân tích chạy nền sau khi UC018 đã trả 202. Chúng chỉ đi vào
# ``knowledge_documents.error_message`` dạng "{code}: {thông điệp}" khi tài liệu chuyển
# ``FAILED`` (ràng buộc ``ck_doc_failed`` của V202 bắt buộc phải có lý do).


class NoTextExtractedError(AiServiceError):
    """Tệp hợp lệ nhưng không có chữ nào để lấy — điển hình là PDF scan chỉ có ảnh.

    Mã lấy nguyên văn từ đặc tả UC018 ("Mười một điểm cần chốt", điểm 1). Thông điệp phải nói
    được cho người dùng cách sửa (OCR rồi tải lại), vì nó hiển thị nguyên văn trên dashboard.
    """

    code = "PARSE_NO_TEXT_EXTRACTED"


class ParseFailedError(AiServiceError):
    """Thư viện không đọc được tệp (hỏng cấu trúc), hoặc tiến trình phân tích chết giữa chừng.
    [CẦN XÁC NHẬN] mã — đặc tả chưa có."""

    code = "PARSE_FAILED"


class ParseTimeoutError(AiServiceError):
    """Phân tích vượt ``kb_parse_timeout_s`` — tiến trình con đã bị giết. [CẦN XÁC NHẬN] mã."""

    code = "PARSE_TIMEOUT"


# ── Nạp tài liệu — UC019 (2/2), ADR-0024 ─────────────────────────────────────


class DocumentNotFoundError(AiServiceError):
    """Không thấy tài liệu/job — không tồn tại, hoặc thuộc tenant khác (RLS che, không phân biệt
    hai trường hợp: phân biệt được là lộ ra id đó CÓ tồn tại ở tenant khác)."""

    code = "DOCUMENT_NOT_FOUND"


class EmbeddingUnavailableError(AiServiceError):
    """Tầng suy luận ``ai-embed`` không trả lời: mất kết nối, hết thời gian chờ, 429, 5xx.

    TẠM THỜI — thử lại sau là có thể được. Không đẩy tài liệu vào ``FAILED`` ngay.
    """

    code = "EMBEDDING_UNAVAILABLE"


class EmbeddingRejectedError(AiServiceError):
    """``ai-embed`` từ chối yêu cầu (400/422) hoặc trả kết quả sai hình dạng (số vector, số chiều).

    VĨNH VIỄN với lượt nạp này — gửi lại đúng yêu cầu đó sẽ bị từ chối y như vậy.
    """

    code = "EMBEDDING_REJECTED"


class EmbeddingModelMismatchError(AiServiceError):
    """``model_id`` mà ``ai-embed`` đang phục vụ khác ``embedding_model`` đã ghim — bất biến 1,
    §3.4.2.

    Nạp tiếp là ghi vào kho những vector thuộc một không gian khác với vector câu hỏi: truy hồi
    vẫn chạy, vẫn trả 5 đoạn, nhưng 5 đoạn đó vô nghĩa. Dừng ngay, không thử lại.
    """

    code = "EMBEDDING_MODEL_MISMATCH"


class IngestOwnershipLostError(AiServiceError):
    """Lượt nạp này không còn giữ tài liệu — bộ quét đã trả nó về hàng đợi và lượt khác đã nhận.

    Không phải lỗi của tài liệu: lượt hiện tại chỉ việc dừng, không ghi gì thêm (ADR-0024).
    """

    code = "INGEST_OWNERSHIP_LOST"


class IngestRetryExhaustedError(AiServiceError):
    """Lỗi tạm thời lặp lại đủ ``kb_so_luot_toi_da`` lượt — thôi thử, tài liệu chuyển ``FAILED``.

    Thông điệp mang theo mã của lỗi tạm thời cuối cùng (``STORAGE_UNAVAILABLE``,
    ``EMBEDDING_UNAVAILABLE``…) để người vận hành biết hạ tầng nào đã chết.
    """

    code = "INGEST_RETRY_EXHAUSTED"


class IngestStalledError(AiServiceError):
    """Tiến trình nạp chết giữa chừng đủ ``kb_so_luot_toi_da`` lượt — bộ quét chuyển ``FAILED``.

    Một tệp làm worker chết (hết bộ nhớ, bị OOM-kill) sẽ làm chết mọi lượt thử; không có trần thì
    nó kéo worker vào vòng lặp khởi động lại vô hạn.
    """

    code = "INGEST_STALLED"


# ── Sự kiện Kafka — worker nạp tài liệu ──────────────────────────────────────
# Hai mã này KHÔNG bao giờ gắn lên tài liệu: không giải mã được sự kiện thì cũng không biết chắc
# nó nói về tài liệu nào. Chúng đi vào header ``dlq.error_code`` của bản tin trong ``ai.dlq``.


class EventSchemaInvalidError(AiServiceError):
    """Bản tin không đúng lược đồ: không phải JSON, thiếu trường, sai kiểu, id tài liệu ở vỏ và ở
    payload lệch nhau. Thử lại không giúp gì — sang DLQ ngay."""

    code = "EVENT_SCHEMA_INVALID"


class EventUnsupportedError(AiServiceError):
    """Đúng khuôn vỏ nhưng ``event_type``/``event_version`` mà bản worker này chưa biết.

    Sang DLQ chứ không bỏ qua: đó thường là java-core đã nâng lược đồ trước ai-service. Nâng
    worker xong thì phát lại từ DLQ — bỏ qua là mất sự kiện vĩnh viễn.
    """

    code = "EVENT_UNSUPPORTED"


# ── Đánh giá chất lượng — UC027 (Ngày 10) ────────────────────────────────────


class InteractionNotFoundError(AiServiceError):
    """Lượt không tồn tại hoặc thuộc tenant khác — RLS che, không phân biệt hai trường hợp (như
    ``DocumentNotFoundError``): 403 là xác nhận cho kẻ dò rằng id đó có thật ở tenant khác."""

    code = "INTERACTION_NOT_FOUND"


class FeedbackReasonRequiredError(AiServiceError):
    """Chê mà không chọn lý do — đặc tả UC027 ``422 REASON_REQUIRED``. CSDL cũng chặn
    (``ck_feedback_reason``, V204); kiểm ở ứng dụng trước để trả mã có nghĩa thay vì 500."""

    code = "REASON_REQUIRED"


class InvalidRaterError(AiServiceError):
    """Nhân viên thiếu mã người dùng, khách kèm mã người dùng, hoặc khách gửi câu sửa
    (``ck_feedback_rater`` của V204; câu sửa là quyền của nhân viên — đặc tả UC027 bước 4)."""

    code = "INVALID_RATER"


class FeedbackInteractionMissingError(AiServiceError):
    """Thiếu ``interaction_id``, hai nguồn (đường dẫn, body) mâu thuẫn, hoặc khen mà kèm lý do
    chê."""

    code = "INVALID_FEEDBACK"


# ── Quản lý kho tri thức — UC020 (Ngày 11) ───────────────────────────────────


class DocumentBusyError(AiServiceError):
    """Tài liệu đang nạp (``PENDING``/``PROCESSING``) hoặc đang có lượt nạp lại — đặc tả UC020
    luồng phụ 5.1. Gỡ giữa chừng là để lại đoạn mồ côi; nạp lại chồng là hai bản bóng tranh nhau."""

    code = "DOCUMENT_BUSY"


class DocumentNotReadyError(AiServiceError):
    """Nạp lại chỉ cho tài liệu ``READY`` (ADR-0031). Tài liệu lỗi thì tải lên lại (UC018)."""

    code = "DOCUMENT_NOT_READY"


class DocumentArchivedError(AiServiceError):
    """Tài liệu đã gỡ khỏi chỉ mục — chỉ còn để đọc."""

    code = "DOCUMENT_ARCHIVED"


class InvalidMetadataError(AiServiceError):
    """Tiêu đề mới trùng một tài liệu khác cùng version (``uq_doc_title_version``) — đặc tả UC020
    ``422 INVALID_METADATA``; cùng mã với lỗi validate của UC018."""

    code = "INVALID_METADATA"
