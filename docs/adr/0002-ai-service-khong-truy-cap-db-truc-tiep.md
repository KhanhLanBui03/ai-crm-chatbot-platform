# ADR-0002 — ai-service không truy cập trực tiếp bảng nghiệp vụ

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-19
- **Làn sở hữu:** Cả hai

## Bối cảnh

<!-- TODO: điền khi thiết kế chi tiết. Nguồn: kế hoạch mục 4.2 -->

## Quyết định

`ai-service` không kết nối thẳng tới bảng nghiệp vụ của `java-core`; mọi thao tác đọc/ghi đi qua API nội bộ theo giao ước OpenAPI ở `docs/openapi/`.

## Lập luận

Ngăn mô hình ngôn ngữ trở thành đường vòng qua RLS. Đây cũng là biện pháp phòng thủ chính chống rò rỉ chéo tenant khi bị tấn công tiêm chỉ thị.

## Đánh đổi

Thêm một chặng mạng cho mỗi thao tác dữ liệu, và buộc hai làn phải chốt giao ước sớm (hạn 07/09) thay vì để ai-service tự truy vấn.

## Hệ quả

<!-- TODO: ảnh hưởng lên schema / giao ước hai làn / vận hành / chương báo cáo -->
