# ADR-0011 — Dựng 58 màn hình bằng shadcn/ui trên Tailwind v4, thiết kế canvas trước khi code

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-21
- **Làn sở hữu:** Track A

## Bối cảnh

Đặc tả UC001–UC042 dẫn ra **58 màn hình** trên 15 module, nhưng repo không có một wireframe
nào và `web-dashboard/` hoàn toàn trống. Kế hoạch mục 1.2 ước lượng dashboard là hạng mục nặng
nhất của Track A (**4 tuần-người**) và gợi ý dùng bộ khối dựng sẵn để rút xuống ~2,5 tuần-người
— nhưng con số đó tính cho một dashboard thông thường, không phải 58 màn hình. Nhóm có 2 người
và 19 tuần cho **toàn bộ** đồ án, không riêng frontend.

Hai ràng buộc kỹ thuật phát sinh khi bắt tay:

- `package.json` ghim `tailwindcss ^3.4.17`, nhưng **shadcn CLI 4.x đã bỏ hỗ trợ Tailwind v3**.
- Đặc tả use case mô tả màn hình **gián tiếp** qua luồng sự kiện; toàn bộ 6 file `.docx` chỉ
  nhắc chữ "màn hình" 19 lần. Không đủ để dựng giao diện — phải suy ra từ luồng sự kiện cộng
  ma trận UC ↔ bảng ở `docs/erd-ai-crm.md` mục 16.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| **A.** Vẽ đủ 58 màn trên canvas rồi chuyển tay từng màn | Bộ ảnh báo cáo đầy đủ nhất | Canvas không xuất ra React; 58 lần chuyển tay vượt ngân sách thời gian |
| **B.** Bỏ qua thiết kế, code thẳng bằng shadcn | Nhanh nhất | Không có ảnh cho chương giao diện; 58 màn không có ngôn ngữ chung, mỗi màn một kiểu |
| **C.** Phân tầng: 21 màn chữ ký vẽ chi tiết + 37 màn sinh từ 6 mẫu lặp | Đủ ảnh cho báo cáo, và 6 mẫu là đòn bẩy thật | Phải chốt token **trước** khi vẽ, nếu không việc chuyển đổi thành dịch tay |
| **D.** Giữ Tailwind v3, ghim `shadcn@2` mãi mãi | Không đụng `package.json` | CLI bản cũ lệch dần khỏi tài liệu shadcn; mọi lệnh `add` về sau phải nhớ ghim |

## Quyết định

Chọn **C**, và nâng lên **Tailwind v4** để dùng shadcn CLI hiện tại (preset `radix-nova`).

21 màn hình "chữ ký" vẽ chi tiết trên canvas Claude Design; 37 màn còn lại sinh trong mã nguồn
từ **6 mẫu lặp** — `ListPage` (19 màn), `DetailPage` (4), `FormDialog` (7), `SettingsPage` (3),
`KpiDashboard` (1), `StatusPage` (3). Bộ token Tailwind chốt **trước** khi vẽ và ghim vào mọi
prompt thiết kế, để mỗi khối trên artboard có sẵn một component tương ứng.

## Lập luận

Canvas **không có nút xuất sang React** — việc chuyển là đọc `.dc.html` rồi viết `.tsx` bằng
tay. Đó là lý do thứ tự "chốt token trước, vẽ theo sau" quyết định toàn bộ chi phí: nó biến
việc chuyển từ *dịch tay* thành *ánh xạ 1-1*. Phương án A trả giá đúng chỗ này 58 lần.

Sáu mẫu lặp là đòn bẩy duy nhất đưa 58 màn về gần mốc 2,5 tuần-người: làm xong sáu file thì mỗi
màn tầng hai chỉ còn một object cấu hình cộng một route, không phải một màn hình viết tay.
Phương án B bỏ luôn đòn bẩy này vì không có bước nào buộc phải rút ra mẫu chung.

Về Tailwind: `.claude/rules/frontend.md` và `web-dashboard/README.md` chỉ nhắc **tên gói** chứ
không ghim số phiên bản, nên nâng v3 → v4 không kéo theo phải viết lại tài liệu. Đổi lấy việc
ghim `shadcn@2` vĩnh viễn (phương án D) là cái giá đắt hơn nhiều cho một đồ án còn 17 tuần.

## Đánh đổi

- **Mất `tailwind.config.js`.** Tailwind v4 khai token bằng `@theme` trong CSS. Ai quen v3 sẽ
  tìm file cấu hình không thấy. Bù lại bằng `docs/design/tokens.md`.
- **37 màn hình sẽ trông giống nhau.** Đó là chủ đích, nhưng hội đồng có thể đọc là đơn điệu.
  Nếu một màn trong nhóm đó thực sự cần bố cục riêng thì phải nâng nó lên tầng một, và ngân
  sách thời gian tăng theo.
- **Canvas và mã nguồn có thể lệch nhau.** Không có cơ chế tự động nào giữ chúng đồng bộ; sửa
  giao diện trong mã mà quên cập nhật artboard thì ảnh trong báo cáo sẽ sai so với sản phẩm.
- **shadcn 4.x đã bỏ `Form`.** Biểu mẫu phải dựng bằng `Field` ghép react-hook-form — khác với
  hầu hết ví dụ shadcn tìm được trên mạng, sẽ tốn thời gian tra cứu.
- **Ba màu chuỗi dữ liệu dưới 3:1 trên nền trắng.** Mọi biểu đồ dùng chúng **bắt buộc** có nhãn
  trực tiếp hoặc bảng dữ liệu kèm theo. Đây là nghĩa vụ thường trực, không phải việc làm một lần.
- Gói build hiện vượt 500 kB, chưa tách chunk.

## Hệ quả

- **Schema:** không ảnh hưởng. Mọi giá trị enum trên giao diện lấy từ `docs/erd-ai-crm.md`.
- **Giao ước hai làn:** làm lộ ra khoảng trống lớn nhất của repo — `docs/openapi/` chỉ có giao
  ước nội bộ java-core ↔ ai-service, **chưa có đặc tả nào cho `/api/v1/**`** mà dashboard gọi.
  Phải viết `docs/openapi/dashboard-api.yaml`, dẫn xuất từ ma trận UC ↔ bảng.
- **Vận hành:** dashboard chạy được độc lập với backend nhờ tầng mock MSW
  (`VITE_USE_MOCK=true`), nên hai làn không chặn nhau.
- **Lệch với đặc tả:** SCR010 nêu 4 vai trò nhưng `platform.roles` chỉ có 2 (`TENANT_ADMIN`,
  `AGENT`). Chốt giữ 2 vai trò, phân quyền chi tiết đọc từ `roles.permissions` (jsonb).
  SCR014 nêu hạn mức dung lượng — ERD không có; bốn hạn mức thật là hội thoại, token, người
  dùng, tài liệu.
- **Báo cáo:** chương 3 lấy ADR này; chương giao diện lấy ảnh ở `docs/report/` (chụp từ ứng
  dụng chạy thật, không phải từ artboard) và các canvas ở `docs/design/canvas/`.
