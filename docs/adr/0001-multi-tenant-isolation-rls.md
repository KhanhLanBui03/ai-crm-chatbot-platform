# ADR-0001 — Cô lập dữ liệu đa khách thuê bằng Row-Level Security

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-19
- **Làn sở hữu:** Track A

## Bối cảnh

<!-- TODO: điền khi thiết kế chi tiết. Nguồn: kế hoạch mục 4.2 -->

## Quyết định

Dùng Row-Level Security của PostgreSQL, cột `tenant_id` trên mọi bảng nghiệp vụ.

## Lập luận

Schema riêng cho từng khách làm số schema tăng tuyến tính và biến việc di trú thành ác mộng. Cơ sở dữ liệu riêng quá đắt cho phân khúc SME. RLS đẩy kiểm soát xuống tầng cơ sở dữ liệu, nên một lỗi quên điều kiện WHERE ở tầng ứng dụng không gây rò rỉ chéo.

## Đánh đổi

Phải kỷ luật với biến phiên (`SET LOCAL app.tenant_id`) và tuyệt đối không dùng tài khoản chủ bảng ở runtime — chủ bảng bypass RLS.

## Hệ quả

<!-- TODO: ảnh hưởng lên schema / giao ước hai làn / vận hành / chương báo cáo -->
