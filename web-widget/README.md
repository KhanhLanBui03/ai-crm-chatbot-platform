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

**Khi sửa code** (Vite dev, nạp thẳng mã nguồn):

```bash
npm install && npm run dev        # http://localhost:5174/?key=<widget_key>&api=http://localhost:8080
npm run typecheck && npm run build   # ra dist/widget.js (một file IIFE ~12 kB)
```

`index.html` là trang dev — nạp `/src/main.ts`, lấy khoá từ địa chỉ trang.

**Như doanh nghiệp thật nhúng** (image Docker — bản đã build):

```bash
docker compose up -d web-widget   # hoặc: docker build -t crm-web-widget . && docker run -p 5174:5174 -p 3000:3000 ...
```

| Cổng | Vai | Nội dung |
|---|---|---|
| `5174` | máy chủ phục vụ widget | chỉ `/widget.js` (+ `/healthz`); mọi đường khác 404, không phục vụ sourcemap |
| `3000` | website doanh nghiệp giả | `demo/index.html` — trang "Cửa hàng Demo" chỉ có MỘT thẻ `<script>` y như mã nhúng |

Biến môi trường của container: `DEMO_WIDGET_KEY` (khoá công khai lấy ở dashboard sau khi "Sinh mã nhúng"),
`WIDGET_SCRIPT_URL`, `WIDGET_PUBLIC_API_URL`. Script `demo/40-dien-ma-nhung.sh` điền chúng vào trang lúc
khởi động và **từ chối khoá có ký tự lạ** (chống chèn mã vào HTML).

Trong dashboard, khai tên miền được phép là `localhost`. Muốn demo tên miền riêng: thêm
`127.0.0.1 cuahangdemo.vn` vào file `hosts` của Windows rồi khai `cuahangdemo.vn`.

**Qua gateway**: gateway phải mở CORS cho `/api/v1/widget/**` (`gateway/.../application.yml`,
`globalcors`) — thiếu thì preflight `OPTIONS` bị 403 và trình duyệt không bao giờ gửi request thật.
