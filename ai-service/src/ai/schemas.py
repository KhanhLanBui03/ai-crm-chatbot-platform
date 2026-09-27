"""DTO vào/ra của ai-service.

MẪU cho tầng schemas. Pydantic model ở đây là GIAO ƯỚC với java-core — mọi thay đổi phải
đồng bộ với docs/openapi/ai-service-to-java-core.yaml.

Không dùng lại các model này làm entity CSDL. ORM model nằm ở src/ai/db/models/.
"""

import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Citation(BaseModel):
    """Một căn cứ mà câu trả lời dựa vào. Bắt buộc có để chống bịa đặt (thí nghiệm E6)."""

    chunk_id: str
    document_title: str
    section_path: str | None = None
    score: float


class AnswerRequest(BaseModel):
    """java-core yêu cầu ai-service trả lời một lượt hội thoại."""

    conversation_id: str
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)


class AnswerResponse(BaseModel):
    """Kết quả một lượt đi qua đồ thị LangGraph."""

    answer: str | None
    citations: list[Citation] = Field(default_factory=list)
    # Nhánh đã chọn — đo độ chính xác định tuyến ĐỘC LẬP với độ chính xác câu trả lời (E5)
    route: str
    # Từ chối khi không đủ căn cứ. Đây là hành vi đúng, không phải lỗi (E7).
    refused: bool = False
    handoff: bool = False
    groundedness_score: float | None = None
    latency_ms: int
    cost_vnd: float | None = None


# ── Kho tri thức — UC018 ─────────────────────────────────────────────────────


class KbDocumentCreate(BaseModel):
    """java-core báo: tệp đã nằm trong kho dùng chung, hãy tạo bản ghi ``PENDING``.

    KHÔNG có trường ``tenant_id``: tenant chỉ đến từ header ``X-Tenant-Id`` (ADR-0001).
    ``extra="forbid"`` biến việc lén gửi ``tenant_id`` trong body thành lỗi 422 ồn ào, thay vì
    bị bỏ qua trong im lặng — bỏ qua thì không ai biết phía gọi đang hiểu sai hợp đồng.

    ``title`` tối đa 255 chứ không phải 300 như đặc tả: khớp ``varchar(255)`` của V202, để
    tiêu đề dài bị 422 ở đây thay vì nổ 500 ở CSDL. Độ lệch ghi ở ADR-0017.
    """

    model_config = ConfigDict(extra="forbid")

    # URI object trong kho S3: s3://{bucket}/{tenant_id}/…/{ten-tep} (ADR-0019).
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
