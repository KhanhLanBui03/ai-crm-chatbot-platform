"""DTO vào/ra của ai-service.

MẪU cho tầng schemas. Pydantic model ở đây là GIAO ƯỚC với java-core — mọi thay đổi phải
đồng bộ với docs/openapi/ai-service-to-java-core.yaml (``ChatRequest``, ``ChatResponse``,
``Citation``). Sửa ở đây mà không sửa ở đó là đơn phương đổi hợp đồng liên làn.

Không dùng lại các model này làm entity CSDL. ORM model nằm ở src/ai/db/models/.
"""

import unicodedata
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Bốn giá trị route của hợp đồng. Bảy nhánh nội bộ (ai_interactions.branch, V204) được
# chiếu xuống bốn giá trị này ở orchestrator/router.py — java-core không cần biết bảy nhánh.
ChatRoute = Literal["FAST_PATH", "RAG", "FALLBACK", "HANDOFF"]

# Bốn lý do từ chối — khớp TỪNG CHỮ với CHECK của ai.ai_interactions.refusal_reason (V204).
RefusalReason = Literal["NOT_COVERED", "OUT_OF_SCOPE_DATA", "LOW_CONFIDENCE", "SAFETY_PROBE"]


class Citation(BaseModel):
    """Một căn cứ mà câu trả lời dựa vào. Bắt buộc có để chống bịa đặt (thí nghiệm E6)."""

    chunk_id: UUID
    document_id: UUID
    title: str | None = None
    snippet: str | None = None
    score: float


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """java-core yêu cầu ai-service trả lời một lượt hội thoại."""

    conversation_id: UUID
    message: str = Field(min_length=1)
    history: list[HistoryMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Kết quả một lượt đi qua router ý định và nhánh xử lý."""

    # Khoá của dòng ai.ai_interactions — java-core gửi lại khi khách/nhân viên đánh giá (UC027).
    # None chỉ khi dựng ChatResponse ngoài run_turn (test).
    interaction_id: UUID | None = None
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    route: ChatRoute
    # Từ chối khi không đủ căn cứ. Đây là hành vi đúng, không phải lỗi (E7).
    refused: bool = False
    # Một trong bốn lý do UC025 khi refused = true, ngược lại None.
    refusal_reason: RefusalReason | None = None
    handoff: bool = False
    groundedness_score: float | None = None
    latency_ms: int
    cost_vnd: float | None = None
    # LLM không phục vụ được (circuit breaker mở, quá hạn) ⇒ câu trả lời trích nguyên văn đoạn
    # liên quan nhất. HTTP vẫn 200 — suy giảm không phải lỗi của người gọi (UC023, Ngày 9).
    degraded: bool = False
    # Thời gian từng chặng (ms): guard, classify, embed, retrieve, rerank, generate, postguard,
    # total. Chặng không chạy thì không có khoá.
    latency_breakdown: dict[str, int] = Field(default_factory=dict)


# ── Kho tri thức — UC018 ─────────────────────────────────────────────────────


class KbDocumentCreate(BaseModel):
    """java-core báo: tệp đã nằm trong kho dùng chung, hãy tạo bản ghi ``PENDING``.

    KHÔNG có trường ``tenant_id``: tenant chỉ đến từ header ``X-Tenant-Id`` (ADR-0001).
    ``extra="forbid"`` biến việc lén gửi ``tenant_id`` trong body thành lỗi 422 ồn ào, thay vì
    bị bỏ qua trong im lặng — bỏ qua thì không ai biết phía gọi đang hiểu sai hợp đồng.

    ``title`` tối đa 255 chứ không phải 300 như đặc tả: khớp ``varchar(255)`` của V202, để
    tiêu đề dài bị 422 ở đây thay vì nổ 500 ở CSDL. Độ lệch ghi ở ADR-0020.
    """

    model_config = ConfigDict(extra="forbid")

    # URI object trong kho S3: s3://{bucket}/{tenant_id}/…/{ten-tep} (ADR-0022).
    # Kiểm thuộc tenant ở rag/ingest/luu_tru.py.
    file_uri: str = Field(min_length=1, max_length=2048)
    # Tên gốc để hiển thị và để biết đuôi tệp người dùng khai — không dùng để đọc tệp.
    file_name: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    # Quyết định bộ tách từ ở bước chia đoạn của UC019.
    language: Literal["vi", "en"] = "vi"
    # Người tải lên — java-core biết từ JWT. Chỉ lưu uuid trần, không FK (ADR-0002).
    uploaded_by: UUID | None = None

    @field_validator("file_name", "title", "description", mode="before")
    @classmethod
    def _nfc_roi_strip(cls, v: object) -> object:
        """Chuẩn hoá NFC rồi strip — chạy TRƯỚC khi Pydantic đếm độ dài.

        ``len()`` của Python và ``varchar(n)`` của Postgres đều đếm CODE POINT. Chữ tiếng Việt
        dạng NFD (hay gặp khi dán từ macOS) tách ``ệ`` thành 3 code point, nên một tiêu đề
        nhìn thấy ~150 chữ đã có thể vượt 255. NFC trước thì hai tầng đếm cùng một con số,
        và tiêu đề lưu xuống CSDL cũng ở đúng một dạng — so trùng tiêu đề để tăng ``version``
        mới đúng.
        """
        if isinstance(v, str):
            return unicodedata.normalize("NFC", v).strip()
        return v

    @field_validator("description")
    @classmethod
    def _mo_ta_rong_la_none(cls, v: str | None) -> str | None:
        """Mô tả chỉ toàn khoảng trắng coi như không có — không lưu chuỗi rỗng xuống CSDL."""
        return v or None


class KbDocumentAccepted(BaseModel):
    """Phản hồi 202: tài liệu đã nhận và xếp hàng, CHƯA lập chỉ mục.

    ``job_id`` bằng đúng ``document_id``: cột ``status`` của ``knowledge_documents`` thay cho
    bảng ``ingestion_jobs`` (V202 dòng 4–5) — mỗi tài liệu có đúng một tiến trình nạp.
    """

    document_id: UUID
    job_id: UUID
    title: str
    version: int
    status: Literal["PENDING"] = "PENDING"
    source_type: str
    mime_type: str


# ── Tiến độ nạp — UC019, SCR033 ──────────────────────────────────────────────
# [CẦN XÁC NHẬN] Hợp đồng ai-service → java-core: ``/v1/ingestion-jobs`` của
# ``docs/openapi/ai-service-to-java-core.yaml`` còn TODO. Tên trường ở đây bám ``CongViecNap`` của
# ``dashboard-api.yaml`` (đổi snake_case → camelCase ở java-core) để java-core chỉ phải đổi tên,
# không phải tính lại gì.


class IngestionStep(BaseModel):
    """Một trong sáu bước và trạng thái của nó."""

    step: Literal["QUEUED", "EXTRACTING", "CHUNKING", "EMBEDDING", "INDEXING", "DONE"]
    state: Literal["DONE", "RUNNING", "PENDING", "FAILED", "SKIPPED"]


class IngestionJobProgress(BaseModel):
    """Tiến độ một job nạp — ``job_id`` = ``document_id`` (V202: một tài liệu, một tiến trình nạp).

    ``chunks_created`` đếm THẬT trong ``knowledge_chunks`` lúc đọc; ``chunks_total`` là số đoạn dự
    kiến sau chặng CHUNKING (``null`` trước đó). ``error_code`` tách từ tiền tố của
    ``error_message`` (``"{code}: {câu hiển thị}"``, xem ``document_repository.danh_dau_that_bai``).
    """

    job_id: UUID
    document_id: UUID
    document_title: str
    trigger: Literal["UPLOAD"] = "UPLOAD"
    state: Literal[
        "QUEUED", "EXTRACTING", "CHUNKING", "EMBEDDING", "INDEXING", "DONE", "FAILED"
    ]
    status: str
    attempt: int
    steps: list[IngestionStep]
    chunks_created: int
    chunks_total: int | None
    percent: float = Field(ge=0, le=100)
    error_code: str | None
    error_message: str | None
    duration_ms: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ── Đánh giá chất lượng — UC027 ──────────────────────────────────────────────
# Bám ``FeedbackRequest`` của docs/openapi/ai-service-to-java-core.yaml (interaction_id, rating
# 1/-1, comment, corrected_answer) — THÊM ba trường V204 bắt buộc mà hợp đồng còn thiếu:
# ``reason_code``, ``rater_type``, ``rater_user_id``.
# Nháp hợp đồng: docs/contracts/uc025-uc027-tu-choi-danh-gia.md.

FeedbackReason = Literal["WRONG_INFO", "IRRELEVANT", "INCOMPLETE", "BAD_TONE"]


class FeedbackRequest(BaseModel):
    """Khách (widget) hoặc nhân viên (hộp thư) đánh giá một lượt trả lời.

    ``extra="forbid"``: lén gửi ``tenant_id`` thành 422 ồn ào (ADR-0001), như ``KbDocumentCreate``.
    Hai ràng buộc chéo trường (chê thì có lý do; nhân viên thì có mã người dùng) KHÔNG kiểm ở đây
    mà ở ``service.record_feedback`` — để trả mã lỗi riêng ``REASON_REQUIRED`` / ``INVALID_RATER``
    như đặc tả UC027, thay vì ``INVALID_REQUEST`` chung của lỗi validate.

    ``AUTO_EVAL`` không nhận từ API: nhãn máy chỉ do bộ chấm tự động trong ai-service ghi.
    """

    model_config = ConfigDict(extra="forbid")

    # Có trong body ở POST /v1/ai/feedback; ở POST /v1/ai-interactions/{id}/feedback thì lấy
    # từ đường dẫn — None ở body là bình thường.
    interaction_id: UUID | None = None
    rating: Literal[1, -1]
    reason_code: FeedbackReason | None = None
    rater_type: Literal["CUSTOMER", "AGENT"] = "CUSTOMER"
    # java-core điền từ JWT của nhân viên. KHÔNG phải tenant — tenant chỉ từ X-Tenant-Id.
    rater_user_id: UUID | None = None
    comment: str | None = Field(default=None, max_length=2000)
    # Câu trả lời đúng do nhân viên sửa — nguồn phát hiện khoảng trống tri thức (V204).
    corrected_answer: str | None = Field(default=None, max_length=4000)

    @field_validator("comment", "corrected_answer", mode="before")
    @classmethod
    def _rong_la_none(cls, v: object) -> object:
        if isinstance(v, str):
            v = unicodedata.normalize("NFC", v).strip()
            return v or None
        return v


class FeedbackRecorded(BaseModel):
    """Bám ``ActionSuccessResponse`` (success, message) — thêm id và cờ tạo mới/cập nhật."""

    success: Literal[True] = True
    message: str
    feedback_id: UUID
    # False = phía này đã đánh giá lượt này trước đó, đã CẬP NHẬT dòng cũ (UC027 luồng phụ 2.1).
    created: bool


# ── Khoảng trống tri thức — UC025 bước 8, SCR034 ─────────────────────────────


class KnowledgeGapItem(BaseModel):
    """Bám ``KnowledgeGapItem`` (query_text, unanswered_count, last_occurred_at) — THÊM các trường
    mà ``KhoangTrongTriThuc`` của dashboard-api.yaml cần, để java-core chỉ đổi tên trường."""

    # uuid5 tất định từ (tenant, lý do, câu đã chuẩn hoá) — ổn định giữa các lần gọi để giao diện
    # làm khoá; KHÔNG phải khoá chính của bảng nào (không có bảng knowledge_gaps).
    id: UUID
    query_text: str
    gap_type: Literal["NOT_COVERED", "OUT_OF_SCOPE_DATA", "LOW_CONFIDENCE"]
    unanswered_count: int
    # Số hội thoại khác nhau — xấp xỉ "số khách khác nhau" (ai_interactions không có contact_id).
    distinct_conversation_count: int
    first_occurred_at: datetime
    last_occurred_at: datetime


class KnowledgeGapPage(BaseModel):
    items: list[KnowledgeGapItem]
    total: int
    page: int
    size: int


# ── Tín hiệu chất lượng — UC027 bước 7 ───────────────────────────────────────


class TyLe(BaseModel):
    """Một tỉ lệ luôn đi kèm tử số và MẪU SỐ — để không ai đọc nhầm nó chia cho cái gì."""

    tu_so: int
    mau_so: int
    gia_tri: float | None  # None khi mẫu số = 0, không phải 0


class DanhGiaPhia(BaseModel):
    rater_type: Literal["CUSTOMER", "AGENT", "AUTO_EVAL"]
    # mẫu số = số lượt CÓ đánh giá từ phía này, KHÔNG phải tổng số lượt (đặc tả UC027)
    ty_le_tich_cuc: TyLe
    che_theo_ly_do: dict[str, int]


class QualitySummary(BaseModel):
    """Bảy tín hiệu chất lượng trong một cửa sổ thời gian — mỗi tín hiệu ghi rõ tần suất đo."""

    tu: datetime
    den: datetime
    so_luot: int
    so_luot_loi: int
    # Bốn tín hiệu rẻ — 100% lượt
    ty_le_tu_choi: TyLe
    ty_le_suy_giam: TyLe
    ty_le_chuyen_giao: TyLe
    do_phu_trich_dan: TyLe
    # KPI §1.6 ≥ 55%
    ty_le_khong_goi_llm: TyLe
    # Hậu kiểm — 100% lượt có sinh câu trả lời
    groundedness_trung_binh: float | None
    tu_choi_theo_ly_do: dict[str, int]
    # Người đánh giá (khi có) và bộ chấm LLM (mẫu 5%)
    danh_gia: list[DanhGiaPhia]
