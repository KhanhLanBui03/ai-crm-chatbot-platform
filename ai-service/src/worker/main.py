"""Tiến trình Kafka consumer — chạy khi ``RUN_MODE=worker`` (Master Plan §6.6). [PRODUCTION]

Hiện tiêu thụ một topic do java-core phát:

    crm.kb.document.uploaded  → UC018/UC019  nạp và lập chỉ mục tài liệu   (group ingestion-cg)

``crm.conversation.closed`` → UC026 (tóm tắt) sẽ thêm ở Ngày 13 theo cùng khuôn.

BỐN LUẬT KHÔNG ĐƯỢC BỎ — mỗi luật ứng với một cách hỏng đã biết trước
---------------------------------------------------------------------
1. ``enable_auto_commit=False``. Xác nhận offset **sau khi** xử lý xong. Bật tự động thì client
   xác nhận theo NHỊP THỜI GIAN (5 s một lần) cho mọi bản tin đã ĐỌC — kể cả bản tin đang xử lý
   dở. Pod chết ngay sau lần xác nhận đó là bản tin mất: Kafka tin rằng nó xong, không giao lại,
   không log nào ghi — tài liệu nằm ``PENDING`` mãi mãi.

2. **Chống trùng theo ``event_id``** (``ai.processed_events``, V211) có SẴN trước consumer đầu
   tiên. Luật 1 đổi "mất bản tin" lấy "nhận trùng bản tin" — nhận trùng là CHẮC CHẮN xảy ra
   (pod chết sau khi xử lý nhưng trước khi xác nhận), và bảng này biến nó thành vô hại.

3. ``max_poll_interval_ms=600000``. Một job nạp chạy vài phút; để mặc định 5 phút thì Kafka coi
   consumer đã chết và rebalance ngay giữa lúc đang nạp — partition sang consumer khác, bản tin
   bị giao lại, và lần xác nhận offset của mình bị từ chối.

4. **Bắt SIGTERM, rời group sạch.** Xử lý nốt bản tin đang dở, xác nhận, rồi mới thoát;
   ``terminationGracePeriodSeconds=60`` ở §3.10.6 dành đúng cho việc này. Job dài hơn 60 s thì
   Kubernetes giết cứng — bộ quét job kẹt (ADR-0024) nhặt lại tài liệu đó.

Bẫy hai listener: worker chạy TỪ MÁY CHỦ thì ``KAFKA_BOOTSTRAP=localhost:29092``; trong mạng
Docker thì ``kafka:9092``. Nhầm thì client treo rồi hết thời gian chờ, không thông báo nào chỉ ra.
"""

import asyncio
import logging
import signal
from contextlib import suppress

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord, TopicPartition
from aiokafka.errors import CommitFailedError

from src.ai import service
from src.ai.config import Settings, get_settings
from src.ai.db import session as db_session
from src.ai.events.dlq import dung_header_dlq
from src.ai.inference.clients import EmbedClient, tao_embed_client
from src.ai.rag.ingest.tien_trinh import bo_phan_tich
from src.ai.telemetry.logging import setup_logging
from src.worker.consumers.tai_lieu import XuLyTaiLieu

logger = logging.getLogger(__name__)


class Worker:
    """Vòng đời consumer + bộ quét job kẹt. Dựng từ ``Settings`` để test trỏ được vào Kafka và
    Postgres dùng một lần mà không sửa tệp này."""

    def __init__(
        self,
        settings: Settings,
        *,
        embed: EmbedClient,
        factory=None,
    ) -> None:
        self.settings = settings
        self.embed = embed
        self.factory = factory
        self.xu_ly = XuLyTaiLieu(
            embed=embed,
            consumer_group=settings.kafka_consumer_group,
            so_luot_toi_da=settings.kb_so_luot_toi_da,
            cho_thu_lai_s=settings.kb_cho_thu_lai_s,
            factory=factory,
        )
        self.dung = asyncio.Event()

    def _tao_consumer(self) -> AIOKafkaConsumer:
        s = self.settings
        return AIOKafkaConsumer(
            s.kafka_topic_tai_lieu,
            bootstrap_servers=s.kafka_bootstrap,
            group_id=s.kafka_consumer_group,
            enable_auto_commit=False,          # luật 1
            max_poll_interval_ms=600_000,      # luật 3
            # Group mới (lần đầu triển khai) đọc từ ĐẦU topic: sự kiện phát trước khi worker có mặt
            # vẫn phải được nạp. "latest" là bỏ rơi mọi tài liệu tải lên trước lần triển khai đầu.
            auto_offset_reset="earliest",
        )

    def _tao_producer(self) -> AIOKafkaProducer:
        # acks=all + idempotence: bản tin DLQ phải CHẮC CHẮN đã ghi trước khi xác nhận offset gốc —
        # nếu không thì sự kiện hỏng biến mất ở cả hai nơi.
        return AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap,
            acks="all",
            enable_idempotence=True,
        )

    async def _xu_ly_mot(
        self, ban_tin: ConsumerRecord, consumer: AIOKafkaConsumer, producer: AIOKafkaProducer
    ) -> None:
        ket_qua = await self.xu_ly.xu_ly_ban_tin(ban_tin.value, ban_tin.headers)

        if ket_qua.hanh_dong == "DLQ":
            # send_and_wait: chờ broker xác nhận. Hỏng ở đây thì ném ra — offset KHÔNG được xác
            # nhận, tiến trình thoát, bản tin được giao lại sau khi khởi động lại.
            await producer.send_and_wait(
                self.settings.kafka_topic_dlq,
                value=ban_tin.value,
                key=ban_tin.key,
                headers=dung_header_dlq(
                    list(ban_tin.headers),
                    topic=ban_tin.topic,
                    partition=ban_tin.partition,
                    offset=ban_tin.offset,
                    consumer_group=self.settings.kafka_consumer_group,
                    ma_loi=ket_qua.ma_loi or "UNKNOWN",
                    thong_diep=ket_qua.thong_diep or "",
                ),
            )
            logger.error(
                "Đã đẩy %s[%s]@%s sang %s: %s",
                ban_tin.topic, ban_tin.partition, ban_tin.offset,
                self.settings.kafka_topic_dlq, ket_qua.ma_loi,
            )

        # Luật 1: xác nhận SAU khi xử lý (hoặc sau khi DLQ đã nhận). Offset xác nhận là offset
        # của bản tin KẾ TIẾP — quy ước của Kafka, +1 sai là bản tin này được giao lại mãi.
        try:
            await consumer.commit(
                {TopicPartition(ban_tin.topic, ban_tin.partition): ban_tin.offset + 1}
            )
        except CommitFailedError:
            # Rebalance giữa chừng: partition đã sang consumer khác, nó sẽ nhận lại bản tin này —
            # và ai.processed_events biến lần nhận lại đó thành TRUNG. Không mất gì.
            logger.warning(
                "Không xác nhận được offset %s[%s]@%s (rebalance) — bản tin sẽ được giao lại",
                ban_tin.topic, ban_tin.partition, ban_tin.offset,
            )

    async def _vong_kafka(self, consumer: AIOKafkaConsumer, producer: AIOKafkaProducer) -> None:
        while not self.dung.is_set():
            # getmany có timeout thay vì getone: getone chặn tới khi có bản tin, nên SIGTERM phải
            # chờ bản tin kế tiếp mới được nhìn thấy. max_records=1: xử lý và xác nhận từng bản
            # tin một — không có "lô đã đọc mà chưa xử lý" nào để mất khi tắt.
            lo = await consumer.getmany(timeout_ms=1000, max_records=1)
            for ban_tins in lo.values():
                for ban_tin in ban_tins:
                    await self._xu_ly_mot(ban_tin, consumer, producer)

    async def _vong_quet(self) -> None:
        """Bộ quét job kẹt (ADR-0024): mỗi ``kb_chu_ky_quet_s`` giây một lần.

        Chờ MỘT chu kỳ rồi mới quét lần đầu: vừa khởi động thì Kafka đang giao lại các bản tin
        chưa xác nhận của lần chạy trước — để chúng đi trước qua semaphore, bộ quét chỉ nhặt những
        gì không còn bản tin nào mang tới.
        """
        while not self.dung.is_set():
            with suppress(TimeoutError):
                await asyncio.wait_for(self.dung.wait(), timeout=self.settings.kb_chu_ky_quet_s)
            if self.dung.is_set():
                break
            try:
                for job in await service.quet_job_ket(factory=self.factory):
                    if self.dung.is_set():
                        break
                    await self.xu_ly.chay_job(job.tenant_id, job.document_id)
            except Exception:  # noqa: BLE001 — bộ quét không được chết vì một lượt hỏng
                logger.exception("Bộ quét job kẹt hỏng một lượt — thử lại ở chu kỳ sau")

    async def chay(self) -> None:
        """Chạy tới khi ``self.dung`` được đặt, rồi dừng sạch: xong việc dở → rời group → trả tài
        nguyên."""
        consumer = self._tao_consumer()
        producer = self._tao_producer()
        await producer.start()
        try:
            await consumer.start()
            try:
                quet = asyncio.create_task(self._vong_quet(), name="quet-job-ket")
                try:
                    await self._vong_kafka(consumer, producer)
                except asyncio.CancelledError:
                    # Bị HUỶ (không phải SIGTERM): không chờ ai làm nốt gì — job đang treo của bộ
                    # quét sẽ giữ tiến trình sống mãi. Tài liệu dở dang để bộ quét lần sau nhặt.
                    quet.cancel()
                    raise
                finally:
                    self.dung.set()
                    # SIGTERM: bộ quét đang giữa một job thì chờ nó xong — cùng tinh thần luật 4.
                    with suppress(asyncio.CancelledError):
                        await quet
            finally:
                # stop() rời group ngay (không chờ session timeout) — partition được chia lại cho
                # replica khác trong vài giây. KHÔNG tự xác nhận offset nào (luật 1).
                await consumer.stop()
        finally:
            await producer.stop()


async def run_worker() -> None:
    """Điểm vào của ``RUN_MODE=worker``: dựng Worker từ cấu hình, gắn SIGTERM/SIGINT, chạy."""
    settings = get_settings()
    setup_logging(settings.log_level)
    embed = tao_embed_client(settings)
    worker = Worker(settings, embed=embed)

    vong_lap = asyncio.get_running_loop()
    for tin_hieu in (signal.SIGTERM, signal.SIGINT):
        vong_lap.add_signal_handler(tin_hieu, worker.dung.set)

    logger.info(
        "Worker nạp tài liệu: topic %s, group %s, Kafka %s, AI_MODE=%s",
        settings.kafka_topic_tai_lieu, settings.kafka_consumer_group,
        settings.kafka_bootstrap, settings.ai_mode,
    )
    try:
        await worker.chay()
    finally:
        await embed.aclose()
        # Tiến trình con phân tích tệp (spawn) phải được đóng, nếu không nó sống sót sau worker.
        bo_phan_tich.dong()
        await db_session.dispose()
        logger.info("Worker đã dừng sạch")
