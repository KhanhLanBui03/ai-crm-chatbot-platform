# web-dashboard — Track A

Bảng điều khiển quản trị cho nhân viên doanh nghiệp. **React 19 + Vite** — không phải Next.js.
Lý do lệch so với kế hoạch: xem `docs/adr/0008-web-dashboard-react-vite-thay-nextjs.md`.

- Cổng dev: **5173**
- Mọi lời gọi API đi qua **gateway** (`:8080`), không gọi thẳng `java-core` / `ai-service`.

## Cấu trúc

```
src/
├── app/          router · providers · config
├── api/          axiosClient + một file mỗi nhóm endpoint
├── components/   ui/ (nguyên thủy dùng chung) · layout/
├── features/     mỗi màn hình nghiệp vụ một thư mục, tự chứa
│   ├── auth/ conversations/ contacts/ leads/
│   └── deals/ documents/ analytics/ settings/
├── hooks/  styles/  types/  utils/
```

Quy tắc: `features/*` được import từ `components/`, `hooks/`, `api/`, `utils/` —
nhưng **không import chéo giữa các feature**. Cần dùng chung thì nâng lên `components/`.

## Ghi chú về khối lượng

Kế hoạch mục 1.2 ước lượng dashboard là hạng mục nặng nhất của Track A (4 tuần-người) và
gợi ý dùng **bộ khối giao diện dựng sẵn (shadcn/ui)** thay vì tự dựng từng màn hình để rút
xuống ~2,5 tuần-người. Đây không phải cắt phạm vi — chức năng vẫn đủ. `tailwindcss`,
`clsx`, `tailwind-merge`, `lucide-react` trong `package.json` đã chuẩn bị sẵn cho hướng này.

## TODO

- [ ] `npm install` rồi dựng `main.tsx`, `App.tsx`
- [ ] `npx shadcn@latest init`
- [ ] `axiosClient` — gắn JWT, gắn `X-Trace-Id`, xử lý 401 làm mới token
- [ ] Router + layout có bảo vệ đăng nhập
- [ ] WebSocket cho hội thoại thời gian thực
