# web-widget — Track A

Widget chat nhúng vào website khách hàng. **Vite + TypeScript thuần**, không framework.

- Cổng dev: **5174**
- Build ra **một file IIFE** `dist/widget.js` — khách nhúng bằng một thẻ `<script>`.

## Vì sao không dùng React ở đây

Widget chạy trên website của người khác. Kèm theo một framework là bắt trang chủ nhà tải thêm
vài chục KB và có nguy cơ xung đột phiên bản với thứ họ đang dùng. TypeScript thuần + Shadow DOM
cho CSS là đủ và an toàn hơn.

## Ràng buộc

- CSS đặt trong **Shadow DOM** để không rò rỉ style ra/vào trang chủ nhà.
- Không gọi thẳng `ai-service`; mọi request qua **gateway** (`/api/v1/**`).
- Ô nhập của widget là bề mặt tấn công **T2** trong `docs/threat-model.md` (tiêm chỉ thị).
  Lọc đầu vào ở phía máy chủ, không tin phía trình duyệt.

## TODO

- [ ] `src/main.ts` — điểm vào, đọc cấu hình từ thuộc tính `data-*` của thẻ script
- [ ] `src/ui.ts` — dựng Shadow DOM
- [ ] `src/api.ts`, `src/session.ts` — giữ phiên hội thoại qua nhiều lần tải trang
