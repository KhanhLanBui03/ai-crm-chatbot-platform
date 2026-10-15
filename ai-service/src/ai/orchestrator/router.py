"""[PRODUCTION] Định tuyến ý định — UC022 bước 4–7.

Hai việc, tách riêng để quyết định nhánh test được mà không cần mạng:

1. ``classify_with_retry`` — gọi ai-classify, hạn chờ 1.000 ms, thử lại một lần.
   Vẫn hỏng thì coi confidence = 0 và đi nhánh truy hồi (mã CLASSIFIER_TIMEOUT).
2. ``decide_route`` — thuần hàm: (bảy xác suất) -> nhánh.

CỘNG XÁC SUẤT THEO Ô (ADR-0035)
-------------------------------
Router chỉ cần chọn đúng Ô, không cần đúng ý định: phân vân giữa "khiếu nại" và "tra cứu" không
sao, vì cả hai cùng đi RAG. Bảy ý định dẫn về ba ô; xác suất một ô = tổng xác suất các ý định
trong ô.

    ô chuyển giao   HANDOFF_HUMAN · BUYING_INTENT
    ô mẫu câu       GREETING
    ô tra tri thức  mọi ý định còn lại (KB_SEARCH · PRICING_POLICY · COMPLAINT_SUPPORT · TECH_ERROR)

THỨ TỰ QUYẾT ĐỊNH (đặc tả UC022, ngưỡng theo ô từ ADR-0035)
----------------------------------------------------------
    phân loại hỏng                       -> RAG       (luồng phụ CLASSIFIER_TIMEOUT)
    ô chuyển giao >= τ                   -> HANDOFF   (luồng phụ 6.1, UC014), nếu HANDOFF_HUMAN
                                                      >= BUYING_INTENT; ngược lại TOOL_CALL
                                                      (chuyển giao: cần duyệt thao tác ghi)
    ô mẫu câu >= 0,85                    -> SMALL_TALK (bước 6 — mẫu câu, 0 LLM)
    ô tra tri thức >= τ                  -> RAG       (bước 7, UC023)
    ô mẫu câu >= τ                       -> RAG       (giữ hành vi cũ: chào chưa đủ chắc thì đi RAG)
    không ô nào đạt                      -> CLARIFY   (luồng phụ 5.1 — hỏi lại, không đoán)

Với τ > 0,5 không thể có hai ô cùng >= τ, nên thứ tự các dòng không đổi kết quả; và mọi câu mà
luật cũ (ngưỡng trên ý định đứng đầu) đã quyết thì luật mới quyết y hệt — luật mới chỉ cứu những câu
luật cũ hỏi lại. Đo 15/10: hỏi lại trên 200 câu người thật 40% -> 14%; bộ vàng có đáp án tới RAG
14 -> 60.

``TOOL_CALL`` giữ nguyên trong telemetry dù nhóm MCP (UC021/024/028) đã hoãn: bỏ nhánh
khỏi taxonomy 7 nhánh là làm lệch toàn bộ số liệu. Trong phạm vi đồ án nó được thực thi
như một lượt chuyển giao.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
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


# Nhóm đi nhanh: ý định trả được bằng mẫu câu soạn sẵn mà không mất thông tin — cũng là ô mẫu câu.
FAST_PATH_INTENTS = frozenset({"GREETING"})
# Ô chuyển giao (ADR-0035). Ý định không thuộc ô này hay ô mẫu câu tính vào ô tra tri thức — giữ
# đúng mặc định "còn lại đi RAG" của luật cũ, kể cả khi router sau này thêm ý định mới.
HANDOFF_INTENTS = frozenset({"HANDOFF_HUMAN", "BUYING_INTENT"})
_NGOAI_O_TRI_THUC = HANDOFF_INTENTS | FAST_PATH_INTENTS

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
    # Bảy xác suất ai-classify trả về, để cộng theo ô (ADR-0035). None khi client không trả (bản
    # giả) — khi đó coi như chỉ có ý định đứng đầu, kết quả trùng luật cũ.
    probabilities: Mapping[str, float] | None = field(default=None, hash=False)


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
                probabilities=_doc_xac_suat(res.get("probabilities")),
            )
        except TimeoutError:
            last_error = "CLASSIFIER_TIMEOUT"
            logger.warning("ai-classify quá hạn %.0f ms (lần %d)", timeout_s * 1000, attempt + 1)
        except Exception as exc:  # noqa: BLE001 — mọi lỗi mạng/định dạng đều suy về cùng một hướng
            last_error = "CLASSIFIER_UNAVAILABLE"
            logger.warning("ai-classify lỗi (lần %d): %s", attempt + 1, exc)
    return Classification(intent=None, confidence=0.0, model_id=None, error_code=last_error)


def _doc_xac_suat(raw: object) -> dict[str, float] | None:
    """Bảy xác suất từ ai-classify. Thiếu hay hỏng định dạng thì bỏ — định tuyến vẫn chạy được
    bằng ý định đứng đầu, không biến một trường phụ thành lỗi phân loại."""
    if not isinstance(raw, Mapping) or not raw:
        return None
    try:
        return {str(k): min(1.0, max(0.0, float(v))) for k, v in raw.items()}
    except (TypeError, ValueError):
        return None


def decide_route(
    c: Classification,
    *,
    fast_path_threshold: float,
    abstention_threshold: float,
) -> RouteDecision:
    """Chọn nhánh bằng xác suất của từng Ô (ADR-0035). Thuần hàm, không I/O."""

    def _d(branch: Branch, reason: str) -> RouteDecision:
        return RouteDecision(branch=branch, route=BRANCH_TO_ROUTE[branch], reason=reason)

    if c.error_code is not None:
        return _d(Branch.RAG, c.error_code)

    p = c.probabilities or ({c.intent: c.confidence} if c.intent else {})
    o_chuyen_giao = sum(v for k, v in p.items() if k in HANDOFF_INTENTS)
    o_mau_cau = sum(v for k, v in p.items() if k in FAST_PATH_INTENTS)
    o_tri_thuc = sum(v for k, v in p.items() if k not in _NGOAI_O_TRI_THUC)

    if o_chuyen_giao >= abstention_threshold:
        if p.get("HANDOFF_HUMAN", 0.0) >= p.get("BUYING_INTENT", 0.0):
            return _d(Branch.HANDOFF, "CUSTOMER_REQUESTED_HUMAN")
        return _d(Branch.TOOL_CALL, "WRITE_APPROVAL_REQUIRED")
    if o_mau_cau >= fast_path_threshold:
        return _d(Branch.SMALL_TALK, "FAST_PATH")
    # Câu chào đủ τ nhưng chưa đủ ngưỡng đi nhanh vẫn đi RAG — giữ đúng hành vi của luật cũ.
    if o_tri_thuc >= abstention_threshold or o_mau_cau >= abstention_threshold:
        return _d(Branch.RAG, "KNOWLEDGE_QUERY")
    return _d(Branch.CLARIFY, "BELOW_ABSTENTION_THRESHOLD")
