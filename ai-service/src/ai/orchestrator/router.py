"""[PRODUCTION] Định tuyến ý định — UC022 bước 4–7.

Hai việc, tách riêng để quyết định nhánh test được mà không cần mạng:

1. ``classify_with_retry`` — gọi ai-classify, hạn chờ 1.000 ms, thử lại một lần.
   Vẫn hỏng thì coi confidence = 0 và đi nhánh truy hồi (mã CLASSIFIER_TIMEOUT).
2. ``decide_route`` — thuần hàm: (ý định, confidence) -> nhánh.

THỨ TỰ QUYẾT ĐỊNH (đặc tả UC022)
--------------------------------
    phân loại hỏng                       -> RAG       (luồng phụ CLASSIFIER_TIMEOUT)
    HANDOFF_HUMAN, conf >= τ             -> HANDOFF   (luồng phụ 6.1, UC014)
    conf < τ                             -> CLARIFY   (luồng phụ 5.1 — hỏi lại, không đoán)
    ý định đi nhanh, conf >= 0,85        -> SMALL_TALK (bước 6 — mẫu câu, 0 LLM)
    BUYING_INTENT                        -> TOOL_CALL (chuyển giao: cần duyệt thao tác ghi)
    còn lại                              -> RAG       (bước 7, UC023)

``TOOL_CALL`` giữ nguyên trong telemetry dù nhóm MCP (UC021/024/028) đã hoãn: bỏ nhánh
khỏi taxonomy 7 nhánh là làm lệch toàn bộ số liệu. Trong phạm vi đồ án nó được thực thi
như một lượt chuyển giao.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum

from src.ai.inference.clients import ClassifyClient
from src.ai.schemas import ChatRoute

logger = logging.getLogger(__name__)


class Branch(StrEnum):
    """Bảy nhánh — khớp TỪNG CHỮ với CHECK của ai.ai_interactions.branch (V204)."""

    SMALL_TALK = "SMALL_TALK"
    RAG = "RAG"
    TOOL_CALL = "TOOL_CALL"
    CLARIFY = "CLARIFY"
    HANDOFF = "HANDOFF"
    SUMMARY = "SUMMARY"
    EXTRACTION = "EXTRACTION"


# Nhóm đi nhanh: ý định trả được bằng mẫu câu soạn sẵn mà không mất thông tin.
FAST_PATH_INTENTS = frozenset({"GREETING"})

# Bảy nhánh chiếu xuống bốn giá trị route của hợp đồng (ChatResponse.route).
# SUMMARY và EXTRACTION chạy bất đồng bộ từ Kafka, không bao giờ đi qua /v1/ai/chat.
BRANCH_TO_ROUTE: dict[Branch, ChatRoute] = {
    Branch.SMALL_TALK: "FAST_PATH",
    Branch.RAG: "RAG",
    Branch.CLARIFY: "FALLBACK",
    Branch.HANDOFF: "HANDOFF",
    Branch.TOOL_CALL: "HANDOFF",
}


@dataclass(frozen=True)
class Classification:
    intent: str | None
    confidence: float
    model_id: str | None
    # None khi gọi thành công; mã lỗi theo đặc tả UC022 khi hỏng
    error_code: str | None = None


@dataclass(frozen=True)
class RouteDecision:
    branch: Branch
    route: ChatRoute
    # Lý do chọn nhánh — để log và để giải thích được từng quyết định khi hội đồng hỏi
    reason: str


async def classify_with_retry(
    client: ClassifyClient,
    text: str,
    *,
    timeout_s: float,
    retries: int,
) -> Classification:
    """Gọi ai-classify với hạn chờ và thử lại. KHÔNG ném lỗi — hỏng thì trả confidence 0."""
    last_error = "CLASSIFIER_UNAVAILABLE"
    for attempt in range(retries + 1):
        try:
            res = await asyncio.wait_for(client.classify(text), timeout=timeout_s)
            conf = min(1.0, max(0.0, float(res["confidence"])))
            return Classification(
                intent=str(res["intent"]),
                confidence=conf,
                model_id=res.get("model_id"),
            )
        except TimeoutError:
            last_error = "CLASSIFIER_TIMEOUT"
            logger.warning("ai-classify quá hạn %.0f ms (lần %d)", timeout_s * 1000, attempt + 1)
        except Exception as exc:  # noqa: BLE001 — mọi lỗi mạng/định dạng đều suy về cùng một hướng
            last_error = "CLASSIFIER_UNAVAILABLE"
            logger.warning("ai-classify lỗi (lần %d): %s", attempt + 1, exc)
    return Classification(intent=None, confidence=0.0, model_id=None, error_code=last_error)


def decide_route(
    c: Classification,
    *,
    fast_path_threshold: float,
    abstention_threshold: float,
) -> RouteDecision:
    """Chọn nhánh từ kết quả phân loại. Thuần hàm, không I/O."""

    def _d(branch: Branch, reason: str) -> RouteDecision:
        return RouteDecision(branch=branch, route=BRANCH_TO_ROUTE[branch], reason=reason)

    if c.error_code is not None:
        return _d(Branch.RAG, c.error_code)
    if c.intent == "HANDOFF_HUMAN" and c.confidence >= abstention_threshold:
        return _d(Branch.HANDOFF, "CUSTOMER_REQUESTED_HUMAN")
    if c.confidence < abstention_threshold:
        return _d(Branch.CLARIFY, "BELOW_ABSTENTION_THRESHOLD")
    if c.intent in FAST_PATH_INTENTS and c.confidence >= fast_path_threshold:
        return _d(Branch.SMALL_TALK, "FAST_PATH")
    if c.intent == "BUYING_INTENT":
        return _d(Branch.TOOL_CALL, "WRITE_APPROVAL_REQUIRED")
    return _d(Branch.RAG, "KNOWLEDGE_QUERY")
