"""Phát ``ai.turn.completed`` sau mỗi lượt xử lý — UC039 bước 1–2, UC022 bước 10. [PRODUCTION]

Lược đồ: ``docs/events/ai.turn.completed.v1.json``. Consumer ``analytics-cg`` (java-core) cộng dồn vào
``analytics.metrics_daily`` để trang "Hiệu quả tác tử AI" đọc. java-core KHÔNG đọc thẳng
``ai.ai_interactions`` (ADR-0002) — nên đây là đường DUY NHẤT để số liệu chi phí, token và độ trễ
sang được phía CRM.

PHÁT NỀN, KHÔNG ĐỂ KHÁCH CHỜ
----------------------------
``aiokafka`` chờ broker tới ``request_timeout_ms`` (mặc định 40 s) khi Kafka chậm hoặc chết. Chặn lượt
chat chờ số liệu là đổi một câu trả lời đúng thành một câu trả lời trễ 40 giây vì telemetry. Nên
``phat_nen`` chỉ tạo một task asyncio rồi trả về ngay; lỗi được nuốt nhưng KHÔNG im lặng — log ERROR và
tăng ``ai_turn_event_failures_total``.

Đánh đổi chấp nhận: ai-service sập giữa lúc task đang chạy thì mất sự kiện của đúng lượt đó (không có
outbox như java-core). Dòng ``ai.ai_interactions`` vẫn còn để đối soát.

``dung_su_kien`` là hàm thuần — test lược đồ không cần Kafka.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from aiokafka import AIOKafkaProducer

from src.ai.orchestrator.turn import TurnRecord
from src.ai.telemetry.logging import trace_id_var
from src.ai.telemetry.metrics import turn_event_failures

logger = logging.getLogger(__name__)

TOPIC = "ai.turn.completed"
LOAI_SU_KIEN = "TurnCompleted"
PHIEN_BAN = 1
# total_ms đã có ở latency_ms — không lặp lại trong latency_breakdown
_BO_CHANG = frozenset({"total_ms"})
# Bảy ý định của taxonomy UC022 — khớp enum ``payload.intent`` trong lược đồ sự kiện
Y_DINH = frozenset({
    "GREETING", "KB_SEARCH", "PRICING_POLICY", "COMPLAINT_SUPPORT", "TECH_ERROR", "HANDOFF_HUMAN", "BUYING_INTENT",
})


def dung_su_kien(rec: TurnRecord, occurred_at: datetime | None = None) -> dict:
    """Vỏ sự kiện đúng lược đồ ``ai.turn.completed.v1``. Không chứa ``user_query``/``response_text``:
    sự kiện nằm trên Kafka 7 ngày, nội dung chat là dữ liệu cá nhân (NĐ 13) và báo cáo không cần nó."""
    return {
        "event_id": str(rec.interaction_id),
        "event_version": PHIEN_BAN,
        "event_type": LOAI_SU_KIEN,
        "tenant_id": rec.tenant_id,
        "aggregate_id": rec.conversation_id,
        "occurred_at": (occurred_at or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
        "payload": {
            "conversation_id": rec.conversation_id,
            "branch": rec.branch,
            # UC038 lớp 1 — thống kê chủ đề theo ý định. Ngoài 7 nhãn đã cam kết thì gửi null, không gửi
            # chuỗi lạ: tầng tổng hợp sẽ mở một "chủ đề" mới cho mỗi chuỗi lạ.
            "intent": rec.intent if rec.intent in Y_DINH else None,
            "status": rec.status,
            "is_answered": rec.is_answered,
            "refusal_reason": rec.refusal_reason,
            "llm_called": rec.llm_called,
            "is_cached": rec.cached,
            "is_degraded": rec.degraded,
            "is_handoff": rec.handoff,
            "safety_flag": rec.safety_flag,
            "model_name": rec.model_name,
            "model_version": rec.model_version,
            "prompt_tokens": rec.prompt_tokens or 0,
            "completion_tokens": rec.completion_tokens or 0,
            # numeric(16,4) ở cả hai làn — làm tròn 4 chữ số, không sớm hơn
            "cost_vnd": round(float(rec.cost_vnd or 0.0), 4),
            "latency_ms": max(int(rec.latency_ms), 0),
            "latency_breakdown": {
                k: max(int(v), 0) for k, v in (rec.latency_breakdown or {}).items() if k not in _BO_CHANG
            },
            "groundedness_score": rec.groundedness_score,
        },
    }


class TurnEventPublisher:
    """Producer dùng chung, khởi động lười ở lượt đầu tiên. Không có Kafka thì từng lần phát hỏng
    riêng lẻ (log + đếm), lần sau thử khởi động lại — không làm hỏng cả tiến trình."""

    def __init__(self, bootstrap: str, *, request_timeout_ms: int = 5_000) -> None:
        self._bootstrap = bootstrap
        self._request_timeout_ms = request_timeout_ms
        self._producer: AIOKafkaProducer | None = None
        self._khoa = asyncio.Lock()
        self._dang_chay: set[asyncio.Task] = set()

    async def _lay_producer(self) -> AIOKafkaProducer:
        async with self._khoa:
            if self._producer is None:
                p = AIOKafkaProducer(
                    bootstrap_servers=self._bootstrap,
                    # acks=all + idempotence: gửi lại sau lỗi mạng không thành hai sự kiện; consumer
                    # vẫn chống trùng theo event_id cho trường hợp còn lại
                    acks="all",
                    enable_idempotence=True,
                    request_timeout_ms=self._request_timeout_ms,
                )
                await p.start()
                self._producer = p
            return self._producer

    async def phat(self, rec: TurnRecord) -> None:
        """Gửi và chờ broker xác nhận. Ném lỗi khi hỏng — ``phat_nen`` là nơi nuốt lỗi."""
        su_kien = dung_su_kien(rec)
        producer = await self._lay_producer()
        await producer.send_and_wait(
            TOPIC,
            value=json.dumps(su_kien, ensure_ascii=False).encode("utf-8"),
            key=rec.tenant_id.encode("utf-8"),
            headers=[("X-Trace-Id", trace_id_var.get().encode("utf-8"))],
        )

    def phat_nen(self, rec: TurnRecord) -> None:
        """Phát trên một task nền rồi trả về ngay — lượt chat không chờ Kafka."""
        task = asyncio.create_task(self._phat_an_toan(rec))
        # Giữ tham chiếu: task không ai giữ có thể bị bộ thu gom rác huỷ giữa chừng
        self._dang_chay.add(task)
        task.add_done_callback(self._dang_chay.discard)

    async def _phat_an_toan(self, rec: TurnRecord) -> None:
        try:
            await self.phat(rec)
        except Exception:  # noqa: BLE001 — telemetry hỏng không được làm hỏng lượt chat
            turn_event_failures.inc()
            logger.exception("Không phát được %s cho lượt %s (nhánh %s)", TOPIC, rec.interaction_id, rec.branch)
            await self._bo_producer_hong()

    async def _bo_producer_hong(self) -> None:
        """Producer hỏng kết nối thì bỏ đi — lần phát sau dựng lại thay vì kẹt mãi với producer chết."""
        async with self._khoa:
            p, self._producer = self._producer, None
        if p is not None:
            try:
                await p.stop()
            except Exception:  # noqa: BLE001
                logger.warning("Dừng producer hỏng không trọn vẹn", exc_info=True)

    async def aclose(self) -> None:
        """Gọi lúc tắt ứng dụng: chờ nốt các sự kiện đang gửi (tối đa vài giây) rồi dừng producer."""
        if self._dang_chay:
            await asyncio.wait(self._dang_chay, timeout=self._request_timeout_ms / 1000)
        async with self._khoa:
            p, self._producer = self._producer, None
        if p is not None:
            await p.stop()
