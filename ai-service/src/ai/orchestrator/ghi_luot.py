"""[PRODUCTION] Ghi lượt xử lý vào ``ai.ai_interactions`` — UC022 bước 9, nền của UC025/UC027.

Thay ``LogTurnRecorder`` làm recorder mặc định từ Ngày 10. Trước đó lượt chat chỉ ra log, nên
không có gì để gắn đánh giá (UC027, khoá ngoại ``ai_feedback.ai_interaction_id``), không có
danh sách khoảng trống tri thức (UC025), không đếm được tín hiệu rẻ nào.

GHI HỎNG KHÔNG LÀM HỎNG LƯỢT CHAT
--------------------------------
``record`` chạy trong ``finally`` của ``run_turn`` — câu trả lời đã có. Ném lỗi ở đây là đổi một
câu trả lời đúng thành HTTP 500 chỉ vì telemetry hỏng. Nên nuốt lỗi, nhưng KHÔNG im lặng: log
ERROR kèm ``interaction_id`` và tăng ``ai_turn_record_failures_total`` — số liệu thiếu dòng phải
nhìn thấy được trên Grafana, không phát hiện lúc viết báo cáo.

Hệ quả cần biết: ``interaction_id`` trong response có thể trỏ vào một dòng không tồn tại ⇒ đánh
giá gửi lên cho lượt đó nhận 404. Chấp nhận: hiếm, và đúng hành vi — không gắn đánh giá vào hư
không.

``Phát ai.turn.completed`` (UC022 bước 10) vẫn là việc của UC039 — chưa làm ở đây.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai.db.repositories import interaction_repository
from src.ai.db.session import get_tenant_session
from src.ai.orchestrator.turn import TurnRecord
from src.ai.telemetry.metrics import chat_turns, refusals, turn_record_failures

logger = logging.getLogger(__name__)


class DbTurnRecorder:
    def __init__(self, factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._factory = factory

    async def record(self, rec: TurnRecord) -> None:
        chat_turns.labels(branch=rec.branch, llm_called=str(rec.llm_called).lower()).inc()
        if not rec.is_answered and rec.refusal_reason and rec.status == "SUCCESS":
            refusals.labels(reason=rec.refusal_reason).inc()
        try:
            async with get_tenant_session(rec.tenant_id, self._factory) as phien:
                await interaction_repository.ghi_luot(
                    phien,
                    id=rec.interaction_id,
                    conversation_id=rec.conversation_id,
                    branch=rec.branch,
                    intent=rec.intent,
                    intent_confidence=rec.intent_confidence,
                    user_query=rec.user_query,
                    response_text=rec.response_text,
                    retrieved_chunk_ids=rec.retrieved_chunk_ids,
                    retrieval_top_score=rec.retrieval_top_score,
                    is_answered=rec.is_answered,
                    refusal_reason=rec.refusal_reason,
                    model_name=rec.model_name,
                    model_version=rec.model_version,
                    prompt_tokens=rec.prompt_tokens,
                    completion_tokens=rec.completion_tokens,
                    cost_vnd=rec.cost_vnd,
                    latency_ms=rec.latency_ms,
                    status=rec.status,
                    error_message=rec.error_message,
                    safety_flag=rec.safety_flag,
                    groundedness_score=rec.groundedness_score,
                    llm_called=rec.llm_called,
                    is_degraded=rec.degraded,
                    is_handoff=rec.handoff,
                )
        except Exception:  # noqa: BLE001 — xem docstring: telemetry hỏng không được làm hỏng lượt chat
            turn_record_failures.inc()
            logger.exception(
                "Không ghi được ai_interactions cho lượt %s (nhánh %s)",
                rec.interaction_id, rec.branch,
            )
            return
        logger.info(
            "ai_turn id=%s branch=%s answered=%s reason=%s llm=%s handoff=%s latency_ms=%s",
            rec.interaction_id, rec.branch, rec.is_answered, rec.refusal_reason,
            rec.llm_called, rec.handoff, rec.latency_ms,
        )
