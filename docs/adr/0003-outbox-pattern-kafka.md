# ADR-0003 — Xử lý bất đồng bộ bằng Outbox Pattern trên Kafka

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-19
- **Làn sở hữu:** Track A

## Bối cảnh

<!-- TODO: điền khi thiết kế chi tiết. Nguồn: kế hoạch mục 4.2 -->

## Quyết định

Ghi sự kiện vào bảng `outbox_events` trong cùng transaction nghiệp vụ, một tiến trình `@Scheduled` phát lên Kafka; consumer riêng cho analytics và scoring. Khóa phân vùng là `tenant_id`.

## Lập luận

Bắn sự kiện trực tiếp trong transaction thì khi rollback vẫn có sự kiện đã gửi. Bắn sau commit thì tiến trình chết giữa chừng là mất sự kiện. Outbox đảm bảo giao nhận ít nhất một lần và cách ly hoàn toàn lỗi của khối phân tích khỏi luồng phục vụ khách. Khóa `tenant_id` giữ đúng thứ tự trong phạm vi một khách hàng và vẫn cho phép mở rộng bằng cách tăng số phân vùng.

## Đánh đổi

Giao nhận ít nhất một lần nghĩa là consumer chắc chắn sẽ nhận trùng — bắt buộc phải có bảng `processed_events` chống trùng, nếu không dashboard đếm sai và Lead bị tạo hai lần.

## Hệ quả

<!-- TODO: ảnh hưởng lên schema / giao ước hai làn / vận hành / chương báo cáo -->
