# ADR-0008 — web-dashboard dùng React + Vite thay vì Next.js 15

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-19
- **Làn sở hữu:** Track A

## Bối cảnh

<!-- TODO: điền khi thiết kế chi tiết. Nguồn: kế hoạch mục 4.2 -->

## Quyết định

Dashboard quản trị xây bằng React + Vite (SPA), không dùng Next.js 15 như phương án ban đầu trong kế hoạch.

## Lập luận

Dashboard nằm sau đăng nhập nên không cần SEO và không cần render phía máy chủ — hai lý do chính để chọn Next.js đều không áp dụng. Dùng chung một công cụ build với `web-widget` (cũng là Vite) giảm số thứ phải học và bảo trì cho nhóm 2 người. Vite khởi động dev server nhanh hơn đáng kể, ảnh hưởng trực tiếp tới nhịp làm việc hằng ngày.

## Đánh đổi

Mất SSR và route handler sẵn có của Next.js; nếu sau này cần trang công khai có SEO thì phải thêm một ứng dụng riêng. Ghi vào Hướng phát triển.

## Hệ quả

<!-- TODO: ảnh hưởng lên schema / giao ước hai làn / vận hành / chương báo cáo -->
