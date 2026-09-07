"""DTO cho endpoint sinh câu trả lời.

MẪU cho tầng schemas. Pydantic model ở đây là GIAO ƯỚC với java-core — mọi thay đổi phải
đồng bộ với docs/openapi/ai-service-to-java-core.yaml.

Không dùng lại các model này làm entity CSDL. ORM model nằm ở app/db/models/.
"""

from pydantic import BaseModel, Field


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
