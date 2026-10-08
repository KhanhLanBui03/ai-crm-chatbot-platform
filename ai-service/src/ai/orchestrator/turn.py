"""[PRODUCTION] Một lượt hội thoại — UC022 luồng chính, bước 3 đến 10.

    3. guardrails (thuần Python)  ->  4. ai-classify  ->  5. so ngưỡng
    6. mẫu câu đường nhanh | 7. nhánh truy hồi (UC023)  ->  9–10. ghi lượt xử lý

Bước ghi (``TurnRecorder``) đặt trong ``finally`` và LUÔN chạy, kể cả khi nhánh xử lý ném
lỗi: nếu chỉ ghi ở nhánh thành công, báo cáo UC039 thiếu đúng những trường hợp đáng quan
tâm nhất (đặc tả UC022, ràng buộc chung).

Hai phụ thuộc là Protocol để test được không cần CSDL hay mô hình ngôn ngữ:
- ``KnowledgeAnswerer`` — nhánh truy hồi tri thức (UC023, ``rag/``).
- ``TurnRecorder`` — ghi ``ai.ai_interactions`` + phát ``ai.turn.completed``.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Protocol

from src.ai.guardrails import detect_injection, mask_pii, normalize_vietnamese_text
from src.ai.inference.clients import ClassifyClient
from src.ai.orchestrator.router import (
    Branch,
    Classification,
    classify_with_retry,
    decide_route,
)
from src.ai.orchestrator.templates import template_reply
from src.ai.schemas import ChatRequest, ChatResponse, Citation
from src.ai.telemetry.metrics import chat_turns

logger = logging.getLogger(__name__)

# Lượt trả bằng mẫu câu không gọi LLM — model_name là NOT NULL ở V204 nên cần một nhãn.
TEMPLATE_MODEL_NAME = "template"


@dataclass(frozen=True)
class KnowledgeAnswer:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    refused: bool = False
    # Một trong NOT_COVERED · OUT_OF_SCOPE_DATA · LOW_CONFIDENCE · SAFETY_PROBE (V204)
    refusal_reason: str | None = None
    groundedness_score: float | None = None
    model_name: str = TEMPLATE_MODEL_NAME
    llm_called: bool = False
    cost_vnd: float = 0.0
    # LLM không phục vụ được (mạch mở, quá hạn) ⇒ câu trả lời trích nguyên văn, HTTP vẫn 200.
    degraded: bool = False
    # Cosine cao nhất câu hỏi ↔ đoạn — KHÁC groundedness_score (xem rag/generate/hau_kiem.py).
    retrieval_top_score: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    # Thời gian từng chặng của nhánh trả lời (ms), gộp vào latency_breakdown của response.
    latency_breakdown: dict[str, int] = field(default_factory=dict)


class KnowledgeAnswerer(Protocol):
    async def answer(
        self, *, tenant_id: str, question: str, request: ChatRequest
    ) -> KnowledgeAnswer: ...


@dataclass
class TurnRecord:
    """Một dòng ai.ai_interactions (V204 + V208). ``user_query`` đã che PII ở tầng ghi."""

    tenant_id: str
    conversation_id: str
    branch: str
    intent: str | None
    intent_confidence: float
    user_query: str
    response_text: str | None
    retrieved_chunk_ids: list[str]
    is_answered: bool
    refusal_reason: str | None
    model_name: str
    model_version: str | None
    cost_vnd: float
    latency_ms: int
    status: str
    error_message: str | None
    safety_flag: str | None
    # Không phải cột V204 — dùng cho KPI ">= 55% lượt không gọi LLM" và log
    llm_called: bool
    route_reason: str
    # Cột V209 — đã có sẵn trong ai.ai_interactions, lược đồ không phải sửa
    retrieval_top_score: float | None = None
    groundedness_score: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    # Không phải cột — tỉ lệ suy giảm là một trong bốn tín hiệu rẻ của UC027
    degraded: bool = False


class TurnRecorder(Protocol):
    async def record(self, rec: TurnRecord) -> None: ...


class PendingKnowledgeAnswerer:
    """Chỗ giữ cho nhánh truy hồi khi ``rag/`` chưa nối.

    Từ chối có lý do NOT_COVERED thay vì bịa câu trả lời — từ chối là hành vi đúng (E7).
    Thay bằng đường ống RAG thật khi UC023 xong.
    """

    REPLY = (
        "Dạ hiện em chưa tìm thấy thông tin phù hợp cho câu hỏi này. "
        "Anh/chị có muốn em chuyển cho nhân viên tư vấn không ạ?"
    )

    async def answer(
        self, *, tenant_id: str, question: str, request: ChatRequest
    ) -> KnowledgeAnswer:
        logger.warning("Nhánh RAG chưa nối — trả từ chối NOT_COVERED")
        return KnowledgeAnswer(answer=self.REPLY, refused=True, refusal_reason="NOT_COVERED")


class LogTurnRecorder:
    """Ghi lượt xử lý ra log JSON và Prometheus.

    TODO(UC022 bước 9–10): ghi ai.ai_interactions (SET LOCAL app.tenant_id cùng
    transaction) và phát ai.turn.completed khi tầng db/ và events/ có.
    """

    async def record(self, rec: TurnRecord) -> None:
        chat_turns.labels(branch=rec.branch, llm_called=str(rec.llm_called).lower()).inc()
        logger.info("ai_turn %s", json.dumps(asdict(rec), ensure_ascii=False))


async def run_turn(
    *,
    tenant_id: str,
    request: ChatRequest,
    classifier: ClassifyClient,
    answerer: KnowledgeAnswerer,
    recorder: TurnRecorder,
    fast_path_threshold: float,
    abstention_threshold: float,
    classify_timeout_s: float,
    classify_retries: int,
) -> ChatResponse:
    started = time.perf_counter()

    # Bước 3 — guardrails. Phát hiện tiêm chỉ thị KHÔNG dừng luồng (luồng phụ 5.2).
    normalized = normalize_vietnamese_text(request.message)
    injection = detect_injection(normalized)
    if injection.is_injected:
        logger.warning("Phát hiện tiêm chỉ thị nhóm %s", injection.matched_category)
    guard_xong = time.perf_counter()

    # Bước 4 — phân loại. Gửi câu GỐC, không gửi câu đã chuẩn hoá: router học trên văn bản
    # thô, và đo trên 200 câu test người thật hai cách cho Macro-F1 gần như bằng nhau
    # (0,712 thô · 0,709 chuẩn hoá) — giữ đúng phân phối lúc huấn luyện.
    classification: Classification = await classify_with_retry(
        classifier, request.message, timeout_s=classify_timeout_s, retries=classify_retries
    )
    classify_xong = time.perf_counter()

    # Bước 5 — so ngưỡng
    decision = decide_route(
        classification,
        fast_path_threshold=fast_path_threshold,
        abstention_threshold=abstention_threshold,
    )

    result: KnowledgeAnswer | None = None
    status, error_message = "SUCCESS", None
    try:
        # Bước 6 — mẫu câu (đường nhanh, hỏi lại, chuyển giao): 0 LLM
        reply = template_reply(decision.branch, request.message)
        if reply is not None:
            result = KnowledgeAnswer(answer=reply)
        else:
            # Bước 7 — nhánh truy hồi tri thức (UC023)
            result = await answerer.answer(
                tenant_id=tenant_id, question=normalized, request=request
            )
    except Exception as exc:
        status, error_message = "FAILED", f"{type(exc).__name__}: {exc}"[:500]
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await recorder.record(
            _build_record(
                tenant_id=tenant_id,
                request=request,
                branch=decision.branch,
                route_reason=decision.reason,
                classification=classification,
                result=result,
                latency_ms=latency_ms,
                status=status,
                error_message=error_message,
                safety_flag=injection.safety_flag,
            )
        )

    return ChatResponse(
        answer=result.answer,
        citations=result.citations,
        route=decision.route,
        refused=result.refused,
        handoff=decision.branch in (Branch.HANDOFF, Branch.TOOL_CALL),
        groundedness_score=result.groundedness_score,
        latency_ms=latency_ms,
        cost_vnd=result.cost_vnd,
        degraded=result.degraded,
        latency_breakdown={
            "guard_ms": int((guard_xong - started) * 1000),
            "classify_ms": int((classify_xong - guard_xong) * 1000),
            **result.latency_breakdown,
            "total_ms": latency_ms,
        },
    )


def _build_record(
    *,
    tenant_id: str,
    request: ChatRequest,
    branch: Branch,
    route_reason: str,
    classification: Classification,
    result: KnowledgeAnswer | None,
    latency_ms: int,
    status: str,
    error_message: str | None,
    safety_flag: str | None,
) -> TurnRecord:
    # Che PII ở TẦNG GHI (UC040, NĐ 13/2023) — redact, không partial.
    masked_query, _ = mask_pii(request.message, mode="redact")
    refused = result.refused if result else False
    refusal_reason = result.refusal_reason if result else None
    if result is None or (refused and refusal_reason is None):
        # V204 ck_interaction_refusal: không trả lời thì phải có lý do
        refusal_reason = "LOW_CONFIDENCE"
    is_answered = result is not None and not refused
    return TurnRecord(
        tenant_id=tenant_id,
        conversation_id=str(request.conversation_id),
        branch=branch.value,
        intent=classification.intent,
        # numeric(4,3) — ba chữ số thập phân
        intent_confidence=round(classification.confidence, 3),
        user_query=masked_query,
        response_text=result.answer if result else None,
        retrieved_chunk_ids=[str(c.chunk_id) for c in result.citations] if result else [],
        is_answered=is_answered,
        refusal_reason=None if is_answered else refusal_reason,
        model_name=result.model_name if result else TEMPLATE_MODEL_NAME,
        # model_name/model_version mô tả mô hình SINH câu trả lời, không phải router
        model_version=None,
        cost_vnd=result.cost_vnd if result else 0.0,
        latency_ms=latency_ms,
        status=status,
        error_message=error_message,
        safety_flag=safety_flag,
        llm_called=result.llm_called if result else False,
        route_reason=route_reason,
        retrieval_top_score=result.retrieval_top_score if result else None,
        groundedness_score=result.groundedness_score if result else None,
        prompt_tokens=result.prompt_tokens if result else None,
        completion_tokens=result.completion_tokens if result else None,
        degraded=result.degraded if result else False,
    )
