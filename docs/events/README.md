# Lược đồ sự kiện Kafka

Giao ước giữa hai làn cho luồng bất đồng bộ. Hạn chốt: **14/09** (mốc M1).
Nguồn: kế hoạch mục 4.3.

## Bảng topic chính thức (Master Plan §2.6 & ADR-0017)

| Topic | Người sản xuất | Người tiêu thụ | Khóa phân vùng | Ý nghĩa nghiệp vụ |
|---|---|---|---|---|
| `crm.kb.document.uploaded` | java-core | `ingestion-cg` (ai-service) | `tenant_id` | Tài liệu tải lên, kích hoạt nạp & chunking (UC018/019) |
| `crm.conversation.closed` | java-core | `summarizer-cg` (ai-service) | `tenant_id` | Hội thoại kết thúc, kích hoạt tóm tắt (UC026) |
| `crm.deal.closed` | java-core | `scoring-feedback-cg` (ai-service) | `tenant_id` | Khách chốt đơn/thất bại, nhãn outcome cho lead scorer (UC030) |
| `ai.kb.document.indexed` | ai-service | `analytics-cg`, `notification-cg` | `tenant_id` | Báo cáo hoàn tất lập chỉ mục vector tài liệu (UC019) |
| `ai.lead.signal.detected` | ai-service | `sales-cg` (java-core) | `tenant_id` | Phát hiện tín hiệu mua hàng hoặc thông tin lead (UC029) |
| `ai.handoff.requested` | ai-service | `live-agent-cg` (java-core) | `tenant_id` | Yêu cầu chuyển giao phiên chat sang tư vấn viên (UC022) |
| `ai.tool_call.audited` | ai-service | `audit-cg` (java-core) | `tenant_id` | Nhật ký gọi công cụ MCP phục vụ kiểm toán (UC024/028) |
| `ai.turn.completed` | ai-service | `analytics-cg`, `billing-cg` | `tenant_id` | Kết thúc lượt xử lý, ghi nhận số token và chi phí (UC006/039) |
| `ai.dlq` | ai-service | Vận hành / Giám sát | `tenant_id` | Hàng đợi thông điệp chết (Dead-letter queue, giữ 30 ngày) |

*Ghi chú tương thích ngược:* Các topic legacy (`crm.conversation.v1`, `crm.lead.v1`, `crm.ai-interaction.v1`, `crm.usage.v1`, `crm.document.v1`) vẫn được duy trì trên broker để không làm gián đoạn các consumer hiện hữu của kế hoạch giai đoạn đầu.

**Vì sao khóa phân vùng là `tenant_id`:** mọi sự kiện của cùng một khách hàng đi vào cùng một
phân vùng, nên thứ tự được giữ trong phạm vi tenant. Đây là mức đảm bảo thứ tự đúng với nhu cầu
nghiệp vụ, và cho phép mở rộng bằng cách tăng số phân vùng mà không phá vỡ tính nhất quán.

## Quy ước bắt buộc

1. Mọi payload có `event_version` (int) để tiến hóa lược đồ về sau. Đổi trường theo kiểu
   phá vỡ tương thích thì tăng hậu tố topic (`.v2`), không sửa `.v1`.
2. Mọi payload có `tenant_id`, `event_id`, `occurred_at`.
3. **Trace ID đặt ở header của bản tin, không phải trong payload** (kế hoạch mục 4.5).
   Header: `X-Trace-Id`.
4. Consumer xác nhận offset **thủ công** (`enable.auto.commit=false`), xác nhận sau khi đã
   xử lý thành công.
5. Chống trùng bằng bảng `analytics.processed_events (consumer_group, event_id)`,
   `INSERT ... ON CONFLICT DO NOTHING`; nếu số dòng ảnh hưởng bằng 0 thì bỏ qua sự kiện.

## Khai báo topic

Tường minh bằng `scripts/create-topics.sh` để tái lập được, dù môi trường phát triển có bật
tạo topic tự động.

Cụm chạy ở **chế độ ZooKeeper** (ADR-0009), không phải KRaft như kế hoạch mục 4.3 ghi.
Điều này **không ảnh hưởng** tới producer/consumer: client chỉ nói chuyện với broker qua
`bootstrap.servers`, không kết nối ZooKeeper. Lược đồ sự kiện, khóa phân vùng và cơ chế
chống trùng ở trang này giữ nguyên.
