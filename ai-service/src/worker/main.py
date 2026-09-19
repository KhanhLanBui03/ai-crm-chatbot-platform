"""Tiến trình Kafka consumer — chạy khi ``RUN_MODE=worker`` (Master Plan §6.6).

Tiêu thụ hai topic do java-core phát, và phát ngược sáu topic ``ai.*`` (§2.6):

    crm.kb.document.uploaded  → UC018/UC019  nạp và lập chỉ mục tài liệu
    crm.conversation.closed   → UC026        tóm tắt sau khi hội thoại đóng

BỐN LUẬT KHÔNG ĐƯỢC BỎ — mỗi luật ứng với một cách hỏng đã biết trước
---------------------------------------------------------------------
1. ``enable_auto_commit=False``. Xác nhận offset **sau khi** xử lý xong. Bật tự
   động là mất bản tin khi tiến trình chết giữa chừng — mất im lặng, không có log.

2. **Chống trùng theo ``event_id``** phải có SẴN trước consumer đầu tiên, không
   phải thêm sau khi phát hiện dữ liệu nhân đôi (kế hoạch Ngày 32). Giao nhận ít
   nhất một lần nghĩa là nhận trùng là chắc chắn, không phải rủi ro.

3. ``max_poll_interval_ms=600000``. Một job nạp tài liệu chạy vài phút; để mặc
   định 5 phút thì Kafka coi consumer đã chết và rebalance ngay giữa lúc đang nạp.

4. **Bắt SIGTERM, rời group sạch.** Xử lý nốt bản tin đang dở rồi mới thoát;
   ``terminationGracePeriodSeconds=60`` ở §3.10.6 dành đúng cho việc này.

Lỗi vĩnh viễn đẩy sang ``ai.dlq`` (giữ 30 ngày), không retry vô hạn.

[CẦN XÁC NHẬN] Bộ tên topic: §2.6 khai 7 topic nghiệp vụ + ``ai.dlq``; còn
``scripts/create-topics.sh`` và ``docs/events/*.json`` trong repo vẫn ở bộ 5 topic
``crm.*.v1`` cũ. Chốt một bộ trước khi viết producer/consumer thật.
"""


async def run_worker() -> None:
    """Vòng đời consumer: đăng ký topic → poll → xử lý → commit offset.

    TODO: dựng ``AIOKafkaConsumer`` với bốn luật ở docstring đầu tệp.
    TODO: định tuyến theo ``event_type`` trong envelope chuẩn §2.6.
    TODO: bắt SIGTERM/SIGINT, rời group sạch.
    """
    raise NotImplementedError("Worker Kafka — kế hoạch 49 ngày, Ngày 12 và Ngày 32")
