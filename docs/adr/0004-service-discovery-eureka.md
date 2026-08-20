# ADR-0004 — Khám phá dịch vụ bằng Eureka Server

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-19
- **Làn sở hữu:** Track A

## Bối cảnh

<!-- TODO: điền khi thiết kế chi tiết. Nguồn: kế hoạch mục 4.2 -->

## Quyết định

Chạy Eureka Server; gateway định tuyến qua `lb://`. Mọi dịch vụ bật `prefer-ip-address`; `ai-service` (Python) đăng ký bằng `py-eureka-client`.

## Lập luận

Cho phép thêm bản sao dịch vụ mà không sửa cấu hình gateway, và là nền để tách microservice thật sự trong tương lai.

## Đánh đổi

Thêm một điểm hỏng và độ trễ hội tụ khi khởi động lại. Ở môi trường phát triển phải hạ `lease-renewal-interval` xuống 10s, `lease-expiration-duration` xuống 30s và tắt `enable-self-preservation`, nếu không mỗi lần restart gateway sẽ định tuyến lỗi khoảng một phút rưỡi.

## Hệ quả

<!-- TODO: ảnh hưởng lên schema / giao ước hai làn / vận hành / chương báo cáo -->
