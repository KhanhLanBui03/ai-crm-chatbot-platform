"""Worker nạp tài liệu trên Kafka THẬT — cổng ra Ngày 5: DLQ hoạt động, khởi động lại không mất job.

Kafka chạy ĐÚNG image của ``docker-compose.yml`` (``confluentinc/cp-kafka:7.9.0``, chế độ
ZooKeeper — ADR-0009) bằng testcontainers; Postgres và RustFS như các test tích hợp khác. Mỗi test
dùng topic và consumer group riêng để offset của test này không lẫn sang test kia.

Bốn kịch bản:
1. Bản tin hỏng lược đồ → ``ai.dlq`` nguyên byte + header ``dlq.*``, offset được xác nhận, worker
   đi tiếp sang bản tin sau.
2. SIGTERM giữa lúc đang nạp → worker nạp NỐT tài liệu, xác nhận offset, rồi mới thoát (luật 4).
3. Worker CHẾT CỨNG giữa lúc đang nạp (không kịp dọn gì) → offset chưa xác nhận, tài liệu kẹt
   PROCESSING → worker mới nhận lại bản tin (TRUNG, vì bước nhận việc đã ghi processed_events) →
   bộ quét trả tài liệu về hàng đợi → nạp lại tới READY, không mất, không đoạn trùng.
4. (Ngày 12, UC026) Kênh thứ hai: ``crm.conversation.closed`` → tóm tắt → PATCH sang java-core
   (giả) đúng một lần → offset của ``summarizer-cg`` được xác nhận, độc lập với ``ingestion-cg``.
"""

import asyncio
import json
import time
from uuid import UUID, uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from testcontainers.community.kafka import KafkaContainer

from src.ai.events.dlq import doc_header
from src.ai.inference.clients import MockEmbedClient
from src.ai.integrations.java_core import MockJavaCoreClient, TinNhanHoiThoai
from src.worker.main import Worker
from tests.integration.nap_chung import cac_doan, tai_lieu_pending, trang_thai

KAFKA_IMAGE = "confluentinc/cp-kafka:7.9.0"  # trùng docker-compose.yml


@pytest.fixture(scope="session")
def kafka_bootstrap():
    with KafkaContainer(KAFKA_IMAGE) as kafka:
        yield kafka.get_bootstrap_server()


@pytest.fixture
async def kenh(kafka_bootstrap, doi_cau_hinh):
    """Topic nguồn + DLQ + group riêng cho một test; cấu hình worker trỏ vào đó."""
    hau_to = uuid4().hex[:8]
    topic, dlq, nhom = f"kb-uploaded-{hau_to}", f"ai-dlq-{hau_to}", f"ingestion-cg-{hau_to}"
    topic_dong, nhom_tom_tat = f"conv-closed-{hau_to}", f"summarizer-cg-{hau_to}"
    admin = AIOKafkaAdminClient(bootstrap_servers=kafka_bootstrap)
    await admin.start()
    try:
        # MỘT partition: thứ tự bản tin trong test là thứ tự xử lý, offset đọc được bằng mắt.
        await admin.create_topics(
            [NewTopic(topic, 1, 1), NewTopic(dlq, 1, 1), NewTopic(topic_dong, 1, 1)]
        )
    finally:
        await admin.close()
    # Bộ quét TẮT trên thực tế (chu kỳ 1 giờ): CSDL test dùng chung cả lượt chạy, còn tài liệu kẹt
    # do test khác cố ý để lại — bộ quét nhặt chúng thì kịch bản của test này không còn tất định.
    # Chỉ test "chết giữa chừng" bật nó, cho riêng worker thứ hai.
    cau_hinh = doi_cau_hinh(
        kafka_bootstrap=kafka_bootstrap,
        kafka_topic_tai_lieu=topic,
        kafka_topic_dlq=dlq,
        kafka_consumer_group=nhom,
        kafka_topic_hoi_thoai_dong=topic_dong,
        kafka_consumer_group_tom_tat=nhom_tom_tat,
        kb_chu_ky_quet_s=3600.0,
    )
    return cau_hinh


def _vo(tenant: UUID, doc: UUID) -> bytes:
    return json.dumps({
        "event_id": int(time.time_ns() % 10**15), "event_version": 1,
        "event_type": "DocumentUploaded", "tenant_id": str(tenant), "aggregate_id": str(doc),
        "occurred_at": "2026-09-27T08:00:00Z", "payload": {"document_id": str(doc)},
    }).encode()


async def _phat(cau_hinh, *ban_tins: tuple[bytes, bytes]) -> None:
    producer = AIOKafkaProducer(bootstrap_servers=cau_hinh.kafka_bootstrap)
    await producer.start()
    try:
        for khoa, gia_tri in ban_tins:
            await producer.send_and_wait(
                cau_hinh.kafka_topic_tai_lieu, gia_tri, key=khoa,
                headers=[("X-Trace-Id", b"trace-ngay5")],
            )
    finally:
        await producer.stop()


async def _offset_da_xac_nhan(cau_hinh, *, nhom=None, topic=None) -> int | None:
    admin = AIOKafkaAdminClient(bootstrap_servers=cau_hinh.kafka_bootstrap)
    await admin.start()
    try:
        offsets = await admin.list_consumer_group_offsets(nhom or cau_hinh.kafka_consumer_group)
    finally:
        await admin.close()
    meta = offsets.get(TopicPartition(topic or cau_hinh.kafka_topic_tai_lieu, 0))
    return meta.offset if meta else None


async def _cho(dieu_kien, han_s: float = 60.0, buoc_s: float = 0.2):
    """Chờ tới khi ``await dieu_kien()`` trả giá trị truthy; quá hạn thì trượt test."""
    het = time.monotonic() + han_s
    while time.monotonic() < het:
        if gia_tri := await dieu_kien():
            return gia_tri
        await asyncio.sleep(buoc_s)
    pytest.fail(f"Quá {han_s}s mà điều kiện chưa đạt")


async def _doc_dlq(cau_hinh) -> list:
    consumer = AIOKafkaConsumer(
        cau_hinh.kafka_topic_dlq, bootstrap_servers=cau_hinh.kafka_bootstrap,
        auto_offset_reset="earliest", enable_auto_commit=False,
    )
    await consumer.start()
    try:
        lo = await consumer.getmany(timeout_ms=5000)
        return [bt for bts in lo.values() for bt in bts]
    finally:
        await consumer.stop()


def _worker(cau_hinh, factory, embed=None, java_core=None) -> Worker:
    return Worker(
        cau_hinh, embed=embed or MockEmbedClient(1024), factory=factory, java_core=java_core
    )


# ── 1. DLQ ───────────────────────────────────────────────────────────────────


async def test_ban_tin_hong_luoc_do_vao_dlq_nguyen_byte_va_worker_di_tiep(
    ha_tang, kho_s3, tenant_a, kenh
):
    factory, _ = ha_tang
    cau_hinh = kenh
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    hong = b'{"event_id": "khong-phai-so", "tenant_id": "x"}'
    khoa = str(tenant_a).encode()
    await _phat(cau_hinh, (khoa, hong), (khoa, _vo(tenant_a, doc)))

    worker = _worker(cau_hinh, factory)
    tac_vu = asyncio.create_task(worker.chay())
    try:
        await _cho(lambda: _la_ready(factory, tenant_a, doc))
        await _cho(lambda: _bang(_offset_da_xac_nhan(cau_hinh), 2))
    finally:
        worker.dung.set()
        await tac_vu

    (ban_tin,) = await _doc_dlq(cau_hinh)
    assert ban_tin.value == hong  # nguyên byte — phát lại được đúng thứ đã hỏng
    assert ban_tin.key == str(tenant_a).encode()
    assert doc_header(ban_tin.headers, "dlq.error_code") == "EVENT_SCHEMA_INVALID"
    assert doc_header(ban_tin.headers, "dlq.original_topic") == cau_hinh.kafka_topic_tai_lieu
    assert doc_header(ban_tin.headers, "dlq.original_offset") == "0"
    assert doc_header(ban_tin.headers, "X-Trace-Id") == "trace-ngay5"


# ── 2. SIGTERM giữa chừng: làm nốt rồi mới thoát ─────────────────────────────


async def test_sigterm_giua_luc_nap_thi_nap_not_xac_nhan_roi_moi_thoat(
    ha_tang, kho_s3, tenant_a, kenh
):
    factory, _ = ha_tang
    cau_hinh = kenh
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "chinh-sach-bao-hanh.pdf", "PDF")
    await _phat(cau_hinh, (str(tenant_a).encode(), _vo(tenant_a, doc)))

    worker = None

    class _SigtermOLo2(MockEmbedClient):
        da_goi = 0

        async def embed_batch(self, texts):
            self.da_goi += 1
            if self.da_goi == 2:
                worker.dung.set()  # đúng việc handler SIGTERM làm
            return await super().embed_batch(texts)

    worker = _worker(cau_hinh, factory, _SigtermOLo2(1024))
    await asyncio.wait_for(worker.chay(), timeout=60)

    assert (await trang_thai(factory, tenant_a, doc))[0] == "READY"
    assert await _offset_da_xac_nhan(cau_hinh) == 1


# ── 3. Chết cứng giữa chừng: khởi động lại không mất job ─────────────────────


async def test_worker_chet_giua_chung_khoi_dong_lai_khong_mat_job(
    ha_tang, kho_s3, tenant_a, kenh, doi_cau_hinh
):
    factory, _ = ha_tang
    cau_hinh = kenh
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "chinh-sach-bao-hanh.pdf", "PDF")
    await _phat(cau_hinh, (str(tenant_a).encode(), _vo(tenant_a, doc)))

    toi_lo_2 = asyncio.Event()

    class _TreoOLo2(MockEmbedClient):
        da_goi = 0

        async def embed_batch(self, texts):
            self.da_goi += 1
            if self.da_goi == 2:
                toi_lo_2.set()
                await asyncio.Event().wait()  # treo tới khi bị giết
            return await super().embed_batch(texts)

    # Worker 1: nhận việc, ghi lô 1, treo ở lô 2 — rồi bị giết (cancel = không kịp làm gì).
    worker_1 = _worker(cau_hinh, factory, _TreoOLo2(1024))
    tac_vu_1 = asyncio.create_task(worker_1.chay())
    await asyncio.wait_for(toi_lo_2.wait(), timeout=60)
    tac_vu_1.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tac_vu_1

    status, _, lan, buoc = await trang_thai(factory, tenant_a, doc)
    assert (status, lan, buoc) == ("PROCESSING", 1, "EMBEDDING")
    assert len(await cac_doan(factory, tenant_a, doc)) == 4  # lô 1 dở dang còn trong kho
    assert await _offset_da_xac_nhan(cau_hinh) is None  # luật 1: chưa xử lý xong thì chưa xác nhận

    # Worker 2: nhận lại bản tin (TRUNG), bộ quét thấy tài liệu kẹt quá 2 s → nạp lại. Bộ quét
    # nhặt cả tài liệu kẹt test khác để lại (CSDL dùng chung) — đúng việc của nó, chỉ chậm hơn.
    cau_hinh = doi_cau_hinh(**{**kenh.model_dump(), "kb_job_ket_sau_s": 2.0,
                               "kb_chu_ky_quet_s": 0.5})
    worker_2 = _worker(cau_hinh, factory)
    tac_vu_2 = asyncio.create_task(worker_2.chay())
    try:
        await _cho(lambda: _la_ready(factory, tenant_a, doc), han_s=60)
        await _cho(lambda: _bang(_offset_da_xac_nhan(cau_hinh), 1))
    finally:
        worker_2.dung.set()
        await tac_vu_2

    status, loi, lan, buoc = await trang_thai(factory, tenant_a, doc)
    assert (status, loi, lan, buoc) == ("READY", None, 2, None)
    doan = await cac_doan(factory, tenant_a, doc)
    assert [d.chunk_index for d in doan] == list(range(len(doan)))  # không sót, không trùng


# ── 4. Kênh tóm tắt (UC026) ──────────────────────────────────────────────────


async def test_hoi_thoai_dong_qua_kafka_thi_tom_tat_patch_mot_lan_va_xac_nhan(ha_tang, kenh):
    factory, _ = ha_tang
    cau_hinh = kenh
    tenant, conv = str(uuid4()), uuid4()
    gia = MockJavaCoreClient()
    gia.nap_hoi_thoai(tenant, conv, [
        TinNhanHoiThoai("CUSTOMER", "Nồi cơm điện bị lỗi E3"),
        TinNhanHoiThoai("BOT", "Dạ anh mua ở chi nhánh nào ạ?"),
        TinNhanHoiThoai("CUSTOMER", "Chi nhánh Quận 7, tuần trước"),
    ])
    vo = json.dumps({
        "event_id": int(time.time_ns() % 10**15), "event_version": 1,
        "event_type": "ConversationClosed", "tenant_id": tenant, "aggregate_id": str(conv),
        "occurred_at": "2026-10-09T08:00:00Z",
        "payload": {"conversation_id": str(conv), "closed_by": str(uuid4()),
                    "closed_at": "2026-10-09T08:00:00Z"},
    }).encode()
    producer = AIOKafkaProducer(bootstrap_servers=cau_hinh.kafka_bootstrap)
    await producer.start()
    try:
        # Gửi HAI LẦN cùng bản tin — outbox phát lại là chuyện chắc chắn xảy ra.
        for _ in range(2):
            await producer.send_and_wait(cau_hinh.kafka_topic_hoi_thoai_dong, vo,
                                         key=tenant.encode())
    finally:
        await producer.stop()

    worker = _worker(cau_hinh, factory, java_core=gia)
    tac_vu = asyncio.create_task(worker.chay())
    try:
        await _cho(lambda: _bang(_offset_da_xac_nhan(
            cau_hinh, nhom=cau_hinh.kafka_consumer_group_tom_tat,
            topic=cau_hinh.kafka_topic_hoi_thoai_dong), 2))
    finally:
        worker.dung.set()
        await tac_vu

    [(t, c, ban_ghi)] = gia.tom_tat_da_ghi
    assert (t, c, ban_ghi.trigger) == (tenant, conv, "CLOSING")
    assert ban_ghi.model_version.endswith("@tt2")
    # Kênh nạp tài liệu không bị kênh tóm tắt xác nhận hộ.
    assert await _offset_da_xac_nhan(cau_hinh) is None


async def _la_ready(factory, tenant, doc) -> bool:
    return (await trang_thai(factory, tenant, doc))[0] == "READY"


async def _bang(coro, gia_tri) -> bool:
    return (await coro) == gia_tri
