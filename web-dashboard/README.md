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
│   ├── auth/ conversations/ contacts/ leads/ deals/
│   ├── analytics/ settings/ knowledge/ ai-agent/
│   └── audit/
├── mocks/        dữ liệu giả + handler MSW, một file mỗi nhóm endpoint
├── hooks/  styles/  types/  utils/
```

Quy tắc: `features/*` được import từ `components/`, `hooks/`, `api/`, `utils/` —
nhưng **không import chéo giữa các feature**. Cần dùng chung thì nâng lên `components/`.

## Ghi chú về khối lượng

Kế hoạch mục 1.2 ước lượng dashboard là hạng mục nặng nhất của Track A (4 tuần-người) và
gợi ý dùng **bộ khối giao diện dựng sẵn (shadcn/ui)** thay vì tự dựng từng màn hình để rút
xuống ~2,5 tuần-người. Đây không phải cắt phạm vi — chức năng vẫn đủ. `tailwindcss`,
`clsx`, `tailwind-merge`, `lucide-react` trong `package.json` đã chuẩn bị sẵn cho hướng này.

## Chạy thử

```bash
cp .env.example .env   # BƯỚC ĐẦU TIÊN, không bỏ qua được — xem ghi chú ngay dưới
npm install
npm run dev            # :5173 — VITE_USE_MOCK=true là chạy trên tầng mock MSW
npm run typecheck
npm run build
npm run gen:api        # sinh lại src/types/api-schema.d.ts từ docs/openapi/dashboard-api.yaml
```

> **Quên `cp .env.example .env` thì đăng nhập hỏng mà không hiểu vì sao.** `.env` không được
> commit (`.gitignore`), nên bản vừa clone về chưa có nó. Thiếu `VITE_USE_MOCK=true` thì tầng
> mock **không khởi động**, mọi lời gọi đi thẳng qua Vite proxy tới gateway `:8080` — mà gateway
> chưa chạy. Màn đăng nhập hiện đúng một dòng `Request failed with status code 500`, không có
> chữ nào chỉ ra nguyên nhân. Đã dựng lại đúng tình huống này trên một bản clone sạch.

Tầng mock chặn ở **tầng mạng** (Service Worker), không phải tầng axios — nên `axiosClient` viết
y hệt như khi gọi backend thật. Đặt `VITE_USE_MOCK=false` trong `.env` là gọi gateway `:8080`,
không sửa component nào.

## Quản lý state — Redux Toolkit

ADR-0012. **Một cơ chế duy nhất**, không dùng zustand hay TanStack Query.

```
src/app/store/
├── index.ts          configureStore · RootState · AppDispatch
├── hooks.ts          useAppDispatch / useAppSelector đã gắn kiểu — dùng hai hook này, không dùng bản trần
├── authSlice.ts      phiên đăng nhập + listener lưu xuống localStorage
└── truyCapStore.ts   trao store cho axiosClient (chạy ngoài cây React)

src/api/
├── axiosClient.ts    JWT · X-Trace-Id · bóc ApiResponse · làm mới token khi 401
├── baseQuery.ts      cầu nối RTK Query → axiosClient
├── apiSlice.ts       createApi gốc, tagTypes theo nhóm bảng của ERD
├── realtime/         WebSocket (ADR-0013)
└── <nhóm>.ts         một file mỗi nhóm endpoint, gọi apiSlice.injectEndpoints
```

**Bẫy `data` vs `currentData`:** `data` giữ kết quả của tham số cũ khi tham số đổi. Tốt cho danh
sách (không nháy trắng), **sai cho nội dung một bản ghi** — nó hiện tin nhắn của khách A dưới tên
khách B trong khoảnh khắc chuyển. Màn chi tiết dùng `currentData` + `isFetching`.

## Kiểu dữ liệu API — sinh, không gõ tay

`docs/openapi/dashboard-api.yaml` là nguồn duy nhất (85 đường dẫn, 109 thao tác, phủ
SCR001–SCR058). `npm run gen:api` sinh ra `src/types/api-schema.d.ts`; `src/types/schema.ts` đặt
tên ngắn cho những schema màn hình thật sự dùng.

Đổi hình dạng dữ liệu là **sửa file YAML rồi sinh lại** — không sửa `.d.ts`, không khai lại
interface trong `features/`. Dữ liệu giả trong `src/mocks/` cũng dùng chính các kiểu đó, nên lệch
giữa mock và giao ước nổ ra lúc `tsc` chứ không phải lúc nối backend thật.

## Thời gian thực — WebSocket

ADR-0013. Giao ước: `docs/openapi/dashboard-realtime.md`.

```
src/api/realtime/
├── sukien.ts     phong bì khung tin + mã đóng  (phần thân dùng type sinh từ OpenAPI)
└── ketNoi.ts     một kết nối cho cả ứng dụng: bắt tay · nhịp tim · nối lại · chống trùng

src/mocks/ws.ts   máy chủ giả bằng ws.link() của MSW, cài đủ cả bắt tay và mã đóng
```

Ba điều dễ làm sai:

1. **Xác thực bằng khung `AUTH` đầu tiên, không phải `?access_token=`.** Trình duyệt không đặt
   được header cho `new WebSocket(...)`, nhưng token trên URL thì đi vào access log của gateway —
   một dòng log là một token dùng lại được cho tới khi hết hạn.
2. **Một tin nhắn mới sinh ra hai khung**: `MESSAGE_CREATED` cho cột giữa, `CONVERSATION_UPDATED`
   cho dòng danh sách. Trình duyệt không tự suy ra `unreadCount` được.
3. **Khung đi thẳng vào cache RTK Query** bằng `onCacheEntryAdded` — không có slice trung gian,
   nên một dòng dữ liệu chỉ có một chỗ chứa. `realtimeSlice` chỉ giữ trạng thái đường truyền.

Thử tay trong console khi `VITE_USE_MOCK=true`:

```js
window.mockThoiGianThuc.guiTinNhan()      // khách nhắn thêm một tin vào hội thoại mới nhất
window.mockThoiGianThuc.guiDangGo()       // chấm "đang gõ"
window.mockThoiGianThuc.ngatKetNoi()      // rớt kết nối để xem chu trình nối lại
window.mockThoiGianThuc.soClient()        // số kết nối đang mở — phải luôn là 1
```

> `kenh.clients` của MSW **không** đếm được số kết nối đang mở: nó chỉ thêm chứ không gỡ khi
> socket đóng, lại lưu qua IndexedDB nên số đếm sống sót cả sau khi tải lại trang. `soClient()`
> tự dọn theo `readyState` — dùng thẳng `clients.size` sẽ báo động giả về rò kết nối.

## Sáu mẫu lặp — đòn bẩy của 37 màn hình

ADR-0011. Làm xong sáu file này thì mỗi màn tầng hai chỉ còn **một object cấu hình cộng một
route**, không phải một màn hình viết tay.

| Mẫu | File | Phủ | Bố cục |
|---|---|---|---|
| M1 | `layout/ListPage.tsx` | **19 màn** | tiêu đề + thao tác · tìm kiếm (đã trì hoãn) + bộ lọc · bảng · phân trang · thanh thao tác hàng loạt |
| M2 | `layout/DetailPage.tsx` | 4 màn | đường quay lại · tiêu đề + trạng thái + thao tác · tab · hai cột |
| M3 | `layout/FormDialog.tsx` | 7 màn | hộp thoại · vùng lỗi cấp biểu mẫu · `FieldGroup` · hai nút chân |
| M4 | `layout/SettingsPage.tsx` | 3 màn | các mục cài đặt · thanh lưu dính đáy, **chỉ hiện khi có thay đổi** |
| M5 | `layout/KpiDashboard.tsx` | 1 màn | hàng thẻ chỉ số · bộ chọn khoảng thời gian · lưới biểu đồ |
| M6 | `layout/StatusPage.tsx` | 3 màn | trạng thái đơn: đang xử lý · thành công · thất bại · **chờ thao tác** |

Dùng chung: `ui/data-table.tsx` (TanStack Table v9), `ui/pagination.tsx`, `ui/empty-state.tsx`.

**Hai chỗ cố ý làm ở tầng dùng chung, không để từng màn tự lo** — vì 19 lần là 19 cơ hội quên:
trì hoãn ô tìm kiếm (`useTriHoan`), và cột hộp kiểm tự sinh khi màn khai `thaoTacHangLoat`.

`EmptyState` phân biệt **rỗng vì chưa có dữ liệu** (lối thoát: tạo bản ghi đầu tiên) với **rỗng vì
bộ lọc** (lối thoát: gỡ lọc). Dùng nhầm là chỉ sai đường cho người dùng.

## Đã dựng

- [x] `npm install`, `main.tsx`, `App.tsx`
- [x] `npx shadcn@latest init` — preset **`radix-nova`**, **Tailwind v4** (xem ADR-0011)
- [x] `axiosClient` — gắn JWT, gắn `X-Trace-Id`, bóc `ApiResponse`, xếp hàng khi làm mới token
- [x] Redux Toolkit + RTK Query (ADR-0012)
- [x] Router + `AppShell` có bảo vệ đăng nhập
- [x] `docs/openapi/dashboard-api.yaml` + sinh type bằng `openapi-typescript`
- [x] Tầng mock MSW + dữ liệu giả gắn kiểu theo giao ước
- [x] Sáu mẫu lặp + `DataTable` trên TanStack Table v9
- [x] WebSocket thời gian thực + máy chủ giả bằng `ws.link()` (ADR-0013)
- [x] **54/54 màn hình thật** (SCR012+013 và SCR019+020 mỗi cặp chung một trang; SCR006 và
      SCR048 chung một component, khác khung dẫn theo người đọc)

### Màn hình đã dựng

Thứ tự dựng theo plan bước 9 — rủi ro giảm dần: C3 → C4 → C5 → C2 → Kiểm toán.

| Nhóm | Màn | Mẫu |
|---|---|---|
| Xác thực | SCR003 Đăng nhập | chữ ký |
| **C3** Hộp thư | SCR019+020 Hộp thư · SCR021 Phân công & chuyển giao | chữ ký |
| **C3** Khách hàng | SCR024 Hồ sơ · SCR025 Hợp nhất · SCR026 Danh bạ · SCR027 Tạo · SCR028 Ghi chú | chữ ký ×2 · M1 · M3 ×2 |
| **C4** Bán hàng | SCR041 DS Lead · SCR042 Chi tiết Lead · SCR043 Tạo Lead · SCR044 Kanban · SCR045 Chi tiết Deal · SCR046 Tạo Deal · SCR047 Hoạt động | chữ ký ×4 · M3 ×2 · M1 |
| **C4** Phân tích | SCR048 Tổng quan · SCR049 Hội thoại/ngày · SCR050 Phễu · SCR052 Chủ đề | chữ ký ×2 · M5 · M1 |
| **C5** Tri thức | SCR029 Tải lên · SCR030 DS tài liệu · SCR031 Tìm thử · SCR032 Các đoạn · SCR033 Tiến độ nạp · SCR034 Khoảng trống | chữ ký ×2 · M1 ×3 · M6 |
| **C5** Tác tử AI | SCR035 Nhật ký gọi công cụ · SCR036 Giám sát lượt xử lý · SCR037 Máy chủ MCP · SCR038 Thêm máy chủ · SCR039 Sổ đăng ký công cụ · SCR040 Duyệt lời gọi · SCR051 Hiệu quả & chi phí | chữ ký ×3 · M1 ×2 · M3 ×2 |
| **C2** Nền tảng | SCR001 Đăng ký · SCR002 Xác thực thư · SCR004 Quên mật khẩu · SCR005 Đặt lại mật khẩu · SCR006 Bảng điều khiển quản trị | chữ ký · M6 · M3 dạng trang ×2 · dùng lại SCR048 |
| **Kiểm toán** | SCR054 Nhật ký · SCR055 Xem trước phạm vi xoá · SCR056 Yêu cầu xoá · SCR057 Tiến độ theo bảng · SCR058 Thực thi | M1 ×2 · M6 · M2 · M3 |
| Doanh nghiệp | SCR007 Hồ sơ · SCR008 Người dùng · SCR009 Mời · SCR010 Phân quyền | M4 · M1 · M3 · riêng |
| Gói dịch vụ | SCR012+013 Thuê bao · SCR014 Hạn mức · SCR015 Mức dùng theo ngày | M2 · chữ ký · M1 |
| Kênh | SCR016 Kênh · SCR017 Kết nối · SCR018 Web Widget | M1 · M3 · M4 |

Mỗi màn kiểm bằng chuột thật qua Chrome DevTools Protocol trước khi coi là xong: **292 mục
kiểm, tất cả đạt, console sạch** — 134 mục của C3/C4 cộng 158 mục của C5, C2, Kiểm toán và
một bộ hồi quy cho các màn cũ.

### Bốn màn đã gỡ — 58 → 54

Đợt rà soát truy vết ngược 42 use case (`docs/traceability-uc-db-api-screen.md`) cho thấy bốn
màn không truy vết được tới luồng chính hay hậu điều kiện của use case nào:

| Màn | Vì sao gỡ |
|---|---|
| SCR011 Phiên đăng nhập | Không use case nào cho người dùng tự xem hay thu hồi phiên. UC003 3a và UC007 b10 chỉ đòi **hệ thống** thu hồi khi vô hiệu hoá tài khoản hoặc tạm ngưng doanh nghiệp |
| SCR022 · SCR023 Quy tắc phân công | Chỉ có ở UC015 2b, luồng **thay thế**. Luồng chính UC014 b6 / UC031 b5 chỉ cần "người ít việc nhất" → gộp thành một khối `assignmentMode` trong **SCR007** |
| SCR053 Tệp báo cáo | UC042 hiện thực theo nhánh **4.2** của chính use case (xuất đồng bộ, trả tệp ngay), nên không có tệp nào được lưu lại để liệt kê |

Ngoài ra SCR034 bỏ thao tác "đánh dấu đã xử lý": danh sách khoảng trống là truy vấn gộp trên
`ai_interactions`, không phải bảng có trạng thái riêng, và không use case nào cho phép đóng một
mục bằng tay.

**SCR007 gỡ ba khối ở đợt rà soát thứ hai** (25/08/2026): "Số lần từ chối liên tiếp", "Giới hạn
mỗi ngày" và "Lưu trữ dữ liệu". UC004 bước 2 liệt kê **đúng sáu trường** của màn này — tên, lĩnh
vực, múi giờ, ngôn ngữ mặc định, giờ làm việc, giọng điệu tác tử AI — và `platform.tenants` không
có cột nào giữ ba thứ kia, nên chúng chỉ tồn tại ở tầng mock. Hai ngưỡng của tác tử là hằng số
hiệu chỉnh ở tầng ứng dụng (bản đặc tả gọi là *"ngưỡng đã hiệu chỉnh"*), phạm vi nhân viên đọc từ
`roles.permissions`, còn xoá theo Nghị định 13 nằm ở SCR055–SCR058.

**13 màn của C5 và SCR054 đọc dữ liệu Track B** (`knowledge`, `ai`, `integration`). Chúng vẫn gọi
`/api/v1/*` như mọi màn khác, nhưng java-core **không** đọc thẳng ba schema đó — nó gọi xuống bề
mặt đọc nội bộ của ai-service rồi làm giàu tên người trước khi trả về (**ADR-0014**). Cho tới khi
java-core hiện thực phần proxy, chúng chạy trên MSW.

> **Kiểm thử qua CDP — ba cái bẫy của môi trường này.** Cửa sổ Chrome ở máy phát triển bị che
> (`document.visibilityState === 'hidden'`), nên (1) animation đóng băng: hộp thoại đã đóng vẫn
> nằm lại DOM ở `data-state="closed"` — phải hỏi `data-state`, đừng hỏi phần tử còn tồn tại;
> (2) bộ lập lịch của React bị bóp, chuỗi mutation → nạp lại → render mất tới ~3 giây, nên phải
> chờ theo **điều kiện** chứ không chờ cứng theo ms; (3) `querySelectorAll('button')` bắt cả nút
> sắp xếp ở tiêu đề cột — nút thao tác phải lấy trong `tbody`, nút hộp thoại trong `[role=dialog]`.
>
> Hai cái bẫy nữa lộ ra ở đợt C5: (4) **chờ chuỗi tĩnh không phải là chờ dữ liệu** — `choChu` bắt
> trúng tiêu đề hay dòng mô tả của trang rồi trả về ngay, trong khi bảng vẫn đang là xương; phải
> chờ một chuỗi chỉ có khi dữ liệu đã về (tên khách, tên công cụ); (5) **MSW dùng chung một
> Service Worker cho cả origin**, nên chạy hai bộ kiểm song song trên nhiều tab thì trạng thái
> giả của tab này rò sang tab kia — chạy từng bộ một.

## TODO

- [x] **C5 AI & Tri thức** — SCR029–SCR040, SCR051 (13 màn)
- [x] **C2 Nền tảng** — SCR001, 002, 004, 005, 006 (5 màn)
- [x] **Kiểm toán** — SCR054–SCR058 (5 màn)
- [x] Rà soát truy vết 42 UC — gỡ 4 màn, 7 endpoint; `assignmentMode` vào SCR007
- [x] **Rà soát truy vết đợt hai** — diff 365 thuộc tính hợp đồng với tên cột trong migration.
      Gỡ 6 trường không có cột và không có use case (5 ở SCR007, `usedOcr` ở SCR033); 6 cột mới
      ở V114/V115/V209 phục vụ UC017 · UC018 · UC023 · UC026 · UC028. **Không bảng mới.**
      Đường đọc dữ liệu Track B: **ADR-0014**
- [ ] Tách gói khi build — gói chính đang vượt 500 kB
- [ ] `web-widget` vẫn trống — TypeScript thuần, không kéo React vào

## Ghi chú

Số đo của preset `radix-nova` **đặc hơn** shadcn cổ điển: nút cao 32px, badge bo viên thuốc,
thẻ dùng vòng viền 1px thay vì đổ bóng, `destructive` là nền pha loãng chứ không phải nền đỏ
đặc. shadcn 4.x cũng **đã bỏ `Form`** — biểu mẫu dựng bằng `Field` ghép react-hook-form.
Hàm `cn` nằm ở `@/utils/cn`, không phải `@/lib/utils` mặc định (đã chỉnh `components.json`).
Bộ token đầy đủ: `docs/design/tokens.md`.

**`DialogContent` đã thêm `max-h-[calc(100dvh-2rem)]` + `overflow-y-auto` — đừng gỡ ra.** Bản
gốc của preset căn giữa hộp thoại bằng `top-1/2` cộng `-translate-y-1/2` mà không giới hạn chiều
cao, nên biểu mẫu dài tràn ra **cả hai đầu** khung nhìn và hàng nút ở chân trôi xuống dưới mép
màn hình: không cuộn tới được, không bấm được, và không có gì báo hiệu. Đo được ở SCR040 — hộp
thoại cao 1050px trong khung nhìn 813px, nút "Đồng ý cho gọi công cụ" nằm ở y = 883. Lỗi này
không nổ ở `tsc` và chỉ lộ ra khi biểu mẫu đủ dài, nên nó ẩn được rất lâu.
