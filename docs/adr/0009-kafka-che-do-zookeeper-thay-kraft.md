# ADR-0009 — Kafka chạy ở chế độ ZooKeeper thay vì KRaft

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-20
- **Làn sở hữu:** Track A
- **Quan hệ:** bổ sung cho [ADR-0003](0003-outbox-pattern-kafka.md) (Outbox Pattern trên Kafka)

> ⚠️ **CẦN ĐIỀN:** phần *Lập luận* dưới đây là suy đoán, chưa phải lý do thật của nhóm.
> Đây là ADR mà hội đồng nhiều khả năng sẽ hỏi tới. Viết lại bằng lý do thật trước khi nộp.

## Bối cảnh

Kế hoạch (mục 4.3) chốt Kafka chạy ở **chế độ KRaft, không cần ZooKeeper**. Nhóm quyết định
đổi sang chế độ ZooKeeper.

Cần biết trước khi đọc tiếp — đây là ràng buộc cứng, không phải ý kiến:

| Mốc | Sự kiện |
|---|---|
| Kafka 2.8 | KRaft ra mắt ở dạng thử nghiệm (KIP-500) |
| Kafka 3.3 | KRaft đạt mức sẵn sàng vận hành |
| **Kafka 3.5** | **ZooKeeper bị đánh dấu lỗi thời (deprecated)** |
| **Kafka 4.0** | **ZooKeeper bị XÓA HẲN — không còn tùy chọn** |

Kafka 3.9 (Confluent Platform 7.9) là dòng **cuối cùng** còn hỗ trợ ZooKeeper.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| **KRaft** (kế hoạch ban đầu) | Một tiến trình thay vì hai; ít RAM hơn; là hướng đi duy nhất còn tương lai; khởi động nhanh hơn | Cấu hình listener rắc rối hơn ở chế độ gộp broker+controller; ít tài liệu tiếng Việt và ít bài hướng dẫn cũ |
| **ZooKeeper** (đã chọn) | Rất nhiều tài liệu, hướng dẫn và câu hỏi StackOverflow; mô hình vận hành quen thuộc; tách bạch rõ "ai giữ metadata" nên dễ trình bày trên slide | Thêm một tiến trình phải chạy và phải theo dõi; **ghim cứng ở Kafka ≤ 3.9, không nâng cấp được**; là công nghệ đang bị loại bỏ |

## Quyết định

Chạy Kafka ở chế độ ZooKeeper, dùng `confluentinc/cp-kafka:7.9.0` và
`confluentinc/cp-zookeeper:7.9.0`. Một broker, một nút ZooKeeper (`Mode: standalone`)
cho môi trường phát triển.

Image `apache/kafka` **không dùng được** cho phương án này: script khởi động của nó luôn
chạy `KafkaDockerWrapper setup` để format KRaft storage, tức là image đó chỉ hỗ trợ KRaft.
Đó là lý do chuyển sang bộ image của Confluent.

## Lập luận

*(Suy đoán — thay bằng lý do thật của nhóm.)*

Với nhóm 2 người và quỹ thời gian đã ở mức 145%, chi phí học một mô hình vận hành mới không
phải là chi phí trung lập. ZooKeeper có khối lượng tài liệu, bài hướng dẫn và câu hỏi đã được
trả lời lớn hơn nhiều lần so với KRaft, nên khi gặp sự cố thì thời gian gỡ ngắn hơn. Với một
đồ án mà Kafka chỉ là **hạ tầng phụ trợ** cho analytics, chấm điểm và đo lường mức sử dụng —
chứ không phải đối tượng nghiên cứu — chọn phương án ít rủi ro vận hành hơn là hợp lý.

Việc tách bạch "ZooKeeper giữ metadata, Kafka giữ dữ liệu" cũng dễ vẽ và dễ trình bày hơn
mô hình quorum nội bộ của KRaft.

## Đánh đổi

Ba điều phải nói thẳng trong báo cáo, vì che giấu sẽ bị trừ điểm nặng hơn là thừa nhận:

1. **Đây là công nghệ đang bị loại bỏ.** ZooKeeper lỗi thời từ Kafka 3.5 và bị xóa ở Kafka 4.0.
   Hệ thống bị ghim ở dòng 3.9 và không nâng cấp lên 4.x được nếu không chuyển đổi trước.
   Đây là **món nợ kỹ thuật đã biết trước**, không phải phát hiện bất ngờ.
2. **Thêm một điểm hỏng và thêm tài nguyên.** ZooKeeper chết thì Kafka không bầu được
   controller. Vận hành thật cần ensemble **3 nút** (số lẻ để bầu được đa số), tức là ba tiến
   trình nữa bên cạnh 3 broker.
3. **Mất lợi thế về độ trễ khởi động và số tiến trình** mà KRaft mang lại.

**Nợ này thuộc Tầng 3.** Nếu còn thời gian, chuyển sang KRaft là một hạng mục gọn: chỉ đụng
`docker-compose.yml`, không đụng một dòng mã ứng dụng nào (xem phần Hệ quả). Nếu không kịp,
viết thành một mục **Hướng phát triển** ở chương 6 với đúng nội dung này.

## Hệ quả

**Không ảnh hưởng tới mã ứng dụng.** Producer và consumer hiện đại chỉ nói chuyện với broker
qua `bootstrap.servers`; chúng không kết nối tới ZooKeeper. Nên `spring-kafka` ở `java-core`
và `aiokafka` ở `ai-service` giữ nguyên cấu hình `KAFKA_BOOTSTRAP=kafka:9092`. ADR-0003
(Outbox Pattern), thiết kế topic, khóa phân vùng `tenant_id` và cơ chế chống trùng bằng
`analytics.processed_events` đều không đổi.

Ảnh hưởng gói gọn trong:

- `docker-compose.yml` — thêm service `zookeeper`, đổi `kafka` sang bộ image Confluent
- `scripts/create-topics.sh` — Confluent để binary trên `PATH` (`kafka-topics`), khác
  `apache/kafka` (`/opt/kafka/bin/kafka-topics.sh`)
- Cổng **2181** thêm vào bảng cổng ở README

**Một điểm cộng ngoài dự tính:** ở chế độ ZooKeeper, Kafka không có listener `CONTROLLER`
(controller do ZooKeeper bầu). Nhờ vậy tránh được luôn lỗi *"advertised.listeners cannot use
the nonroutable meta-address 0.0.0.0"* mà chế độ KRaft gộp broker+controller hay gặp — lỗi
này đã thực sự xảy ra khi dựng khung bằng KRaft.

Cảnh báo về **hai listener** ở mục 4.3 của kế hoạch **vẫn nguyên giá trị**: `INTERNAL` cho
mạng Docker (`kafka:9092`), `EXTERNAL` cho máy chủ (`localhost:29092`).

## Kiểm chứng đã chạy

- `/brokers/ids` trong ZooKeeper hiện `[1]` — broker có đăng ký thật
- `/brokers/topics` hiện đủ 5 topic — metadata do ZooKeeper giữ
- Bản ghi đăng ký của broker chứa cả hai endpoint:
  `INTERNAL://kafka:9092`, `EXTERNAL://localhost:29092`
- Gửi/nhận thật một sự kiện `ConversationStarted` với khóa là `tenant_id`
