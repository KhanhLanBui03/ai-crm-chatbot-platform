# ADR-0005 — Truy xuất hệ thống nghiệp vụ qua Model Context Protocol

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-19
- **Làn sở hữu:** Track B

## Bối cảnh

<!-- TODO: điền khi thiết kế chi tiết. Nguồn: kế hoạch mục 4.2 -->

## Quyết định

Dùng Model Context Protocol làm giao thức chuẩn ở giữa, thay vì viết adapter riêng cho từng khách hàng. Bản giả lập nằm ở **repository riêng** `mcp-server-mock` (xem README gốc).

## Lập luận

Với N khách hàng và M hệ thống, adapter riêng cho ra N×M tích hợp và mỗi lần thêm khách phải sửa lõi. Giao thức chuẩn ở giữa đưa về N+M. Việc tách `mcp-server-mock` thành repo riêng là cố ý: nó chứng minh đây là hệ thống ngoài, không thuộc CRM.

## Đánh đổi

Thêm một chặng mạng, và phụ thuộc vào một đặc tả đang tiến hóa nhanh — bắt buộc ghim phiên bản (`spec_version` trong bảng `integration.MCP_SERVERS`).

## Hệ quả

<!-- TODO: ảnh hưởng lên schema / giao ước hai làn / vận hành / chương báo cáo -->
