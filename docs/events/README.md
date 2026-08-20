# Lược đồ sự kiện Kafka

Giao ước giữa hai làn cho luồng bất đồng bộ. Hạn chốt: **14/09** (mốc M1).
Nguồn: kế hoạch mục 4.3.

## Bảng topic

| Topic | Người sản xuất | Người tiêu thụ | Khóa phân vùng |
|---|---|---|---|
| `crm.conversation.v1` | java-core | `analytics-cg`, `scoring-cg` | `tenant_id` |
| `crm.lead.v1` | java-core | `analytics-cg`, `notification-cg` | `tenant_id` |
| `crm.ai-interaction.v1` | ai-service | `analytics-cg` | `tenant_id` |
| `crm.usage.v1` | java-core | `billing-cg` | `tenant_id` |
| `crm.document.v1` | java-core | `ingestion-cg` (ai-service) | `tenant_id` |

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
