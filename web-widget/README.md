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

## Cấu trúc

- [x] `src/main.ts` — điểm vào, đọc `data-widget-key` (và `data-api-url` tuỳ chọn) từ thẻ script
- [x] `src/ui.ts` + `src/styles.ts` — dựng Shadow DOM; nội dung tin luôn gán bằng `textContent` (chống XSS)
- [x] `src/api.ts`, `src/session.ts` — gọi `/api/v1/widget/**`, giữ token phiên ở localStorage theo từng khoá

## Chạy thử

```bash
npm install && npm run dev        # mở http://localhost:5174/?key=<widget_key>&api=http://localhost:8080
npm run build                     # ra dist/widget.js (một file IIFE)
```

`index.html` là trang giả "Cửa hàng Demo" — chỉ dùng khi phát triển và quay video. Tên miền
`localhost` phải được khai trong danh sách tên miền của widget thì mới chạy (không có ngoại lệ ngầm).
