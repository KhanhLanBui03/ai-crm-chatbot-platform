"""DTO cho endpoint sinh câu trả lời.

MẪU cho tầng schemas. Pydantic model ở đây là GIAO ƯỚC với java-core — mọi thay đổi phải
đồng bộ với docs/openapi/ai-service-to-java-core.yaml (``ChatRequest``, ``ChatResponse``,
``Citation``). Sửa ở đây mà không sửa ở đó là đơn phương đổi hợp đồng liên làn.

Không dùng lại các model này làm entity CSDL. ORM model nằm ở src/ai/db/models/.
"""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Bốn giá trị route của hợp đồng. Bảy nhánh nội bộ (ai_interactions.branch, V204) được
# chiếu xuống bốn giá trị này ở orchestrator/router.py — java-core không cần biết bảy nhánh.
ChatRoute = Literal["FAST_PATH", "RAG", "FALLBACK", "HANDOFF"]


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

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    route: ChatRoute
    # Từ chối khi không đủ căn cứ. Đây là hành vi đúng, không phải lỗi (E7).
    refused: bool = False
    handoff: bool = False
    groundedness_score: float | None = None
    latency_ms: int
    cost_vnd: float | None = None
