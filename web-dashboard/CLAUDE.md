# web-dashboard — CLAUDE.md

Bảng điều khiển quản trị CRM cho nhân viên doanh nghiệp (Track A), nằm sau đăng nhập.
**React 19 + Vite** (SPA, ADR-0008) — không phải Next.js: không `app/`, `pages/`, server component.
Dev chạy ở **:5173**; mọi lời gọi API/WebSocket đi qua **gateway :8080** (proxy `/api` `/ai` `/ws` trong `vite.config.ts`).

## 1. Lệnh
```bash
cp .env.example .env   # BẮT BUỘC lần đầu — .env bị gitignore nên bản clone không có
npm run dev            # :5173
npm run typecheck      # tsc --noEmit
npm run build          # tsc -b && vite build
npm run gen:api        # sinh lại src/types/api-schema.d.ts từ ../docs/openapi/dashboard-api.yaml
```
Quên `.env` → thiếu `VITE_USE_MOCK=true` → `main.tsx` không bật MSW → request đi thẳng qua proxy tới
gateway chưa chạy → màn đăng nhập chỉ hiện `Request failed with status code 500`, không chữ nào chỉ ra nguyên nhân.

## 2. Viết thứ này thì đặt vào đâu
| Thứ cần viết | Chỗ đặt | Ví dụ có sẵn |
|---|---|---|
| Component dùng chung, **không biết nghiệp vụ** | `src/components/ui/` (tên file kebab) | `status-chip.tsx`, `empty-state.tsx`, `data-table.tsx` |
| Khung/mẫu màn hình dùng chung | `src/components/layout/` | `ListPage.tsx`, `AppShell.tsx` |
| Component riêng của một màn | `src/features/<nhom>/` | `features/contacts/CreateContactDialog.tsx` |
| Bảng nhãn enum → chữ + sắc thái + biểu tượng | `src/features/<nhom>/nhan.ts` | `features/conversations/nhan.ts` |
| Gọi API (RTK Query `injectEndpoints`) | `src/api/<nhom>.ts` | `api/contacts.ts` |
| Kiểu dữ liệu API | sửa `docs/openapi/dashboard-api.yaml` → `gen:api`; đặt tên ngắn ở `src/types/schema.ts` | `KhachHang`, `TrangThaiHoiThoai` |
| Vỏ `ApiResponse<T>`, `Page<T>`, `ApiError` | `src/types/api.ts` | |
| Mock MSW | handler `src/mocks/handlers/<nhom>.ts` (gộp ở `index.ts`), dữ liệu `src/mocks/du-lieu-<nhom>.ts` | `handlers/khach-hang.ts` |
| Hook dùng nhiều nơi / chỉ một feature | `src/hooks/` / ngay trong feature | `hooks/useTriHoan.ts` / `features/conversations/useDangGo.ts` |
| Hàm tiện ích | `src/utils/` | `utils/ten.ts` (`chuCaiDau`, `vietTatDoanhNghiep`) |
| Token màu, font, bo góc | **chỉ** `src/styles/index.css` (Tailwind v4, không có `tailwind.config.js`) | |
| Route mới | `src/app/router.tsx` + nhãn breadcrumb ở `NHAN_DUONG_DAN` (`AppShell.tsx`) | |

## 3. Luật import
`features/*` import được `components/`, `hooks/`, `api/`, `utils/`, `types/`, `app/store/hooks` — **không import
feature khác**; cần dùng chung thì nâng lên `components/`. Luôn dùng alias `@/` (repo có 0 import tương đối).
- Sai (đang có thật): `features/contacts/ContactsPage.tsx:13` — `import { NHAN_KENH } from '@/features/conversations/nhan'`.
- Đúng: cùng file, dòng 9–11 — `ListPage` từ `@/components/layout/ListPage`, `StatusChip` từ `@/components/ui/status-chip`.
- `components/`, `hooks/`, `utils/`, `api/` không bao giờ import `@/features` (hiện 0 chỗ — giữ nguyên).

## 4. Đặt tên — quy ước đang dùng
- **Props, biến, state nghiệp vụ: tiếng Việt không dấu, camelCase.** `ListPageProps`: `tieuDe`, `moTa`, `dangTai`,
  `khiChuaCoDuLieu`, `thaoTacHangLoat`. Setter viết `dat…`: `const [moTao, datMoTao] = useState(false)` (`ContactsPage.tsx:31`).
  Callback `onDoi…`/`onChon…`: `onDoiTrang`, `onChonDong`. Prop biểu tượng viết hoa vì được render: `BieuTuong: LucideIcon`.
- **File component: PascalCase tiếng Anh + hậu tố vai trò** — `ContactsPage.tsx`, `CreateContactDialog.tsx`, `AuthLayout.tsx`;
  thư mục feature kebab tiếng Anh (`ai-agent`). File trong `ui/` kebab theo shadcn (`status-chip.tsx`).
- **Hook: `use` + tiếng Việt** — `useTriHoan`, `useCheDo`, `useDangGo`. Ngoại lệ: `use-mobile.ts` (sinh từ shadcn).
- **Endpoint RTK Query tiếng Việt**: `danhSachKhachHang` → `useDanhSachKhachHangQuery`; mutation bằng động từ `taoKhachHang`, `suaKhachHang`.
- **Hằng**: UPPER_SNAKE tiếng Việt — `NHAN_TRANG_THAI`, `NHAN_DUONG_DAN`, `MUC_CHINH`. Tag cache PascalCase: `'KhachHang'`.
- **Giữ nguyên tiếng Anh** tên trường theo hợp đồng OpenAPI (`fullName`, `consentGranted`) và giá trị enum (`PENDING_AGENT`).
- Đường dẫn route kebab tiếng Việt: `/khach-hang/:id`, `/ban-hang/co-hoi-tiem-nang`. Mock kebab tiếng Việt; `api/` tiếng Anh.

## 5. Token và màu
| Token (class) | Dùng cho |
|---|---|
| `background` `foreground` | nền và chữ chính của trang |
| `card` `popover` | thẻ; nền hộp thoại, sheet, tooltip, toast |
| `primary` (chàm) | nút chính, liên kết `text-primary hover:underline`, vùng chọn nhạt `bg-primary/8` (thanh hàng loạt) |
| `muted` `muted-foreground` | nền phụ, xương; chữ mô tả/phụ chú |
| `secondary` | ô chữ cái đầu, chip `neutral` |
| `border` `input` `ring` | viền, viền ô nhập, vòng focus |
| `destructive` `success` `warning` `info` | **chỉ trạng thái** — qua `StatusChip sacThai`, `StatusPage`, mũi tên KPI |
| `chart-1` … `chart-5` | **chỉ chuỗi dữ liệu** biểu đồ |
| `sidebar-*` | chỉ trong `ui/sidebar.tsx` |

Nền pha loãng viết bằng độ mờ trên token: `bg-success/12 text-success` (`status-chip.tsx:14`).

**Cấm hex/rgb/màu Tailwind gốc (`bg-red-500`) trong JSX.** Hiện `src/` có 0 màu Tailwind gốc. Ngoại lệ hợp lệ đang tồn tại:
- `index.css` `--chart-*` giữ **hex** có chủ đích — bảng màu đã kiểm định, quy đổi oklch gây sai số.
- `WidgetConfigPage.tsx:76,186` `'#2a78d6'` + `text-white` ở bản xem trước: đó là **dữ liệu** màu doanh nghiệp chọn cho
  website của họ, không phải theme dashboard; `<input type="color">` cũng chỉ nhận hex.
- `bg-black/10` lớp phủ trong `dialog.tsx`/`sheet.tsx` — nguyên bản preset.
- Recharts và `style={{}}` không nhận class → truyền `'var(--chart-1)'`, `'var(--border)'` (`OverviewPage.tsx:192,218`). Đây là cách đúng.

Màu chuỗi dữ liệu: **gán theo slot cố định, không xoay vòng, màu đi theo thực thể.** Mẫu đúng: hằng `CHANG` giống hệt
nhau ở `AiInteractionsPage.tsx:40` và `AiPerformancePage.tsx:17` (Truy hồi = chart-1 … Gọi công cụ = chart-4). Quá 5
chuỗi thì gộp "Khác", không sinh màu mới; không dùng hai trục y.
Màu trạng thái **luôn kèm biểu tượng + nhãn chữ**: `NHAN_TRANG_THAI` trả `{ nhan, sacThai, BieuTuong }`; chip đồng ý dữ
liệu là `ShieldCheck` + "Đã đồng ý". Biểu đồ dùng màu chuỗi **bắt buộc có nhãn trực tiếp hoặc bảng/thẻ số kèm theo** —
slot 2–5 đo được 3,20 · 2,82 · 2,17 · 2,69 : 1 trên nền trắng. Mẫu: ba thẻ `TheTong` có chấm màu + số + tỉ lệ đặt trên
biểu đồ cột ở `ConversationStatsPage.tsx:92`. Chú giải (`Legend`) thôi là chưa đủ.

## 6. Chữ, khoảng cách, bo góc — thang đang dùng thật
Font **Geist Variable** (`--font-sans`, `--font-heading` trỏ cùng). Chỉ `font-medium` (106) và `font-semibold` (34), không có `font-bold`.

| Class | Vai trò (số lần) |
|---|---|
| `text-xl font-semibold tracking-tight` | tiêu đề trang — cả 5 mẫu layout (15) |
| `text-2xl` | số KPI (`KpiDashboard`), tiêu đề `AuthLayout` (3) · `text-3xl` điểm lead (1) · `text-[34px]` hero đăng nhập (1) |
| `text-base font-medium` | tiêu đề hộp thoại, thẻ, `EmptyState` · `text-[15px] font-medium` tiêu đề mục cài đặt (8) |
| `text-sm` | nội dung mặc định (bảng, nút, card); `Input` là `text-base md:text-sm` |
| `text-[13px]` | mô tả dưới tiêu đề, phụ chú, phân trang, `HangThongTin` (109) |
| `text-xs` | chip, nhãn nhỏ, số phụ (168) · `text-[11px]` / `fontSize: 11` trục biểu đồ (6) |

Khoảng cách: đệm trang `p-4` (mọi mẫu, `StatusPage`/`AuthLayout` dùng `p-6`); tiêu đề ↔ mô tả `gap-0.5`; nhóm nút `gap-1.5`;
lưới thẻ `gap-3`; khối trong trang `gap-4`; mục cài đặt `gap-6`. `Card` tự đệm bằng `--card-spacing` = 16px (`size="sm"` 12px).
Bo góc (`--radius` 10px): `rounded-lg` nút/ô nhập/khối viền (45) · `rounded-full` chip, avatar, chấm (35) · `rounded-md` 8px
thanh, ô biểu tượng (17) · `rounded-xl` 14px card, dialog (6) · `rounded-sm` kbd (1). Không dùng cấp `2xl` trở lên.

## 7. Responsive
Breakpoint đang dùng ở `features/` + `layout/`: `sm` 640px (13) · `lg` 1024px (4) · `xl` 1280px (2). `md` 768px chỉ nằm trong `ui/`.
**Mobile-first: viết class không tiền tố trước rồi mới `sm:`/`lg:`** — `grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`,
`hidden lg:flex`, `p-6 sm:p-12`. Repo có 0 biến thể `max-*:` — đừng thêm.

| Thành phần | Hành vi |
|---|---|
| `AppShell` / sidebar | `< 768px` (`useIsMobile`): sidebar thành `Sheet` 18rem trượt từ trái, mở bằng `SidebarTrigger`. `≥ 768px`: cố định 16rem, thu gọn offcanvas bằng trigger hoặc ⌘/Ctrl+B, nhớ bằng cookie `sidebar_state`. Thanh trên `h-14 px-6` không có breakpoint |
| `DataTable` | không đổi bố cục; bảng cuộn ngang trong khung riêng (`min-w-0 overflow-x-auto`), ô `whitespace-nowrap` |
| Dialog | `< 640px`: `w-full max-w-[calc(100%-2rem)]`, chân `flex-col-reverse` (nút chính lên trên). `≥ 640px`: `sm:max-w-sm`; `FormDialog` `sm:max-w-lg`, `rong="rong"` → `sm:max-w-2xl`; chân `sm:flex-row sm:justify-end` |
| Lưới KPI | 1 cột → `sm` 2 cột → `xl` 4 cột |
| `AuthLayout` | bảng thương hiệu `hidden lg:flex` (560px); biểu mẫu `max-w-md`, đệm `p-6 sm:p-12` |

## 8. Dark mode
`index.css` khai `@custom-variant dark (&:is(.dark *))` và đặt lại toàn bộ token trong khối `.dark`. Hook
`src/hooks/useCheDo.ts` bật/tắt lớp `dark` trên `<html>`, lưu `localStorage['crm-ai-che-do']` (`toi`/`sang`), mặc định theo
`prefers-color-scheme`; nó chỉ được gọi ở `AppShell`. Tối đổi được **chỉ vì màu đi qua biến CSS**: hex hay `text-white` viết
cứng giữ nguyên giá trị sáng — chữ tối trên nền `#171717`, và mất bảng `--chart-*` đã bước lại riêng cho nền tối.
`features/` có 0 lần dùng `dark:` — token đã lo, đừng vá màu bằng `dark:`.

## 9. Sáu mẫu màn hình + DataTable (ADR-0011)
Màn mới **chọn mẫu trước**; bố cục riêng là màn "chữ ký" (như `InboxPage`, `DealsBoardPage`), phải có lý do.
- **M1 `ListPage`** — danh sách. Props: `cot`, `trang: Page<T>`, `dangTai`, `timKiem`, `boLoc`/`giaTriBoLoc`/`onDoiBoLoc`/`onGoHetBoLoc`,
  `sapXep`, `onDoiTrang`, `thaoTacChinh`/`thaoTacPhu`/`thaoTacHangLoat`, `khiChuaCoDuLieu`. **Đã lo sẵn — màn không tự làm lại:**
  trì hoãn ô tìm 300ms (`useTriHoan`), nút "Gỡ bộ lọc", cột hộp kiểm + thanh "Đã chọn N mục" **tự sinh khi khai `thaoTacHangLoat`**,
  chọn đúng loại `EmptyState`, `Pagination` (máy chủ đếm từ 0, hiển thị từ 1). Mẫu copy: `features/contacts/ContactsPage.tsx`.
  Màn chỉ lo reset `trang: 0` khi đổi từ khoá/bộ lọc (`ContactsPage.tsx:151`).
- **`DataTable`** — `cot: CotBang<T>[]`, `duLieu`, `layId` (mặc định `id`), `soDongXuong` (8), `onChonDong`, `chonNhieu`, `sapXep`, `khiRong`.
  TanStack Table **v9**: `tableFeatures()` khai tĩnh (`dacTinhBang` = sắp xếp + chọn dòng), `useTable`, `getAllCells`; sắp xếp chạy ở máy chủ.
- **M2 `DetailPage`** — `quayLai`, `tieuDe`, `phuDe`, `chip`, `thaoTac*`, `tab`/`tabHienTai`/`onDoiTab`, `cotPhu`, `dangTai`. Lo xương hai cột và
  thứ tự cố định quay lại → tiêu đề → tab → nội dung; `HangThongTin` cho cột phụ. Ví dụ `ContactDetailPage.tsx`.
- **M3 `FormDialog`** — `mo`, `onDoiMo`, `form` (react-hook-form), `onGui`, `loi`, `dangGui`, `nhanGui`, `rong`, `children` là các `Field`. Lo `noValidate`,
  `Alert` lỗi cấp biểu mẫu, khoá nút + "Đang lưu…", `FieldGroup`; đóng **không** reset biểu mẫu. Ví dụ `CreateContactDialog.tsx`.
- **M4 `SettingsPage`** — `muc[]`, `coThayDoi`, `dangLuu`, `loi`, `onLuu`, `onHuy`, `dangTai`, `chiDoc`. Thanh lưu dính đáy **chỉ hiện khi `coThayDoi`**;
  `chiDoc` khoá mọi ô bằng `<fieldset disabled>` + `Alert` lý do. Màn tự tính `coThayDoi` (`TenantProfilePage.tsx:61`).
- **M5 `KpiDashboard`** — `kpi: TheKpi[]` (`nhan`, `giaTri`, `phuChu`, `thayDoi`, `tangLaTot`), `khoangThoiGian`, `capNhatLuc`, `onXuatBaoCao`, `children` là
  lưới biểu đồ. Lo lưới thẻ, xương 88px, mũi tên xanh/đỏ theo `tangLaTot` (đặt `false` cho chỉ số giảm-là-tốt). Nhãn biểu đồ do màn lo.
- **M6 `StatusPage`** — `trangThai: 'dang-xu-ly' | 'thanh-cong' | 'that-bai' | 'cho-thao-tac'`, `chiTiet`, `thaoTac*`, `toanManHinh`. Biểu tượng + màu
  đã ghép; "đã gửi thư, mời mở hộp thư" là `cho-thao-tac`, không phải `thanh-cong`.

## 10. Rỗng / đang tải / lỗi
- **Rỗng vì chưa có dữ liệu** → lối thoát là tạo bản ghi đầu tiên (`ListPage` tự gắn `thaoTacChinh` vào `EmptyState`).
  **Rỗng vì bộ lọc** → biểu tượng `SearchX` + nút "Gỡ bộ lọc", **không** có nút tạo mới. Dùng nhầm là chỉ sai đường cho người dùng.
  Ngoài `ListPage` thì dùng thẳng `EmptyState` và tự chọn đúng `thaoTac` (6 file đang làm vậy, vd `ToolCallLogPage.tsx`).
- **Đang tải: `Skeleton` theo đúng hình nội dung** (`XuongBang`, `XuongChiTiet`, thẻ KPI `h-[88px]`), không spinner. `Loader2 animate-spin`
  chỉ dành cho **công việc đang chạy** (`StatusPage` `dang-xu-ly`, bước nạp tài liệu). Nút đang gửi: `disabled` + chữ "Đang lưu…".
- **Lỗi gửi biểu mẫu**: truyền `loi={ketQua.error}` vào `FormDialog`/`SettingsPage`; đọc thông điệp qua `laLoiTruyVan()` (`api/baseQuery.ts`).
- **Thao tác lẻ trên trang**: `await mutation(...).unwrap()` → `toast.success(...)`; lỗi bắt lại rồi
  `toast.error(laLoiTruyVan(loi) ? loi.message : 'Không chuyển được giai đoạn.')` (`DealDetailPage.tsx:53`). `toast.warning` khi đã làm xong nhưng
  có điều cần biết (`CreateContactDialog.tsx:95`). `import { toast } from 'sonner'`; `<Toaster>` gắn một lần ở `app/providers.tsx`.
- **Lỗi tải trang**: các mẫu chưa có prop lỗi tải — xem mục 16 trước khi dựa vào chúng.

## 11. Dữ liệu
- **RTK Query là cơ chế duy nhất cho state máy chủ** (ADR-0012): một `createApi` ở `api/apiSlice.ts`, mỗi nhóm một file `injectEndpoints`,
  mutation `invalidatesTags` để tự nạp lại. State client chỉ có `authSlice`, `realtimeSlice`. Dùng `useAppSelector`/`useAppDispatch`
  (`app/store/hooks.ts`), không bản trần. TanStack chỉ dùng **`@tanstack/react-table`**; không zustand, không TanStack Query, không `createAsyncThunk`.
- Mọi request qua `axiosClient` (JWT, `X-Trace-Id`, bóc `ApiResponse`, xếp hàng làm mới token khi 401) nhờ `axiosBaseQuery`. `axios` bị import 0 lần ngoài `api/`.
- **`src/types/api-schema.d.ts` là file SINH TỰ ĐỘNG** (6.136 dòng, dòng đầu ghi "Do not make direct changes"). Sửa tay là mất ở lần `gen:api`
  kế tiếp. Đổi hình dạng dữ liệu = sửa `docs/openapi/dashboard-api.yaml` rồi sinh lại; không khai lại interface trong `features/`.
- **`data` vs `currentData`**: danh sách dùng `data` (không nháy trắng); nội dung **một bản ghi** dùng `currentData` + `isFetching`
  (`InboxPage.tsx:72`) — `data` hiện tin nhắn khách A dưới tên khách B lúc chuyển.
- **MSW chặn ở tầng mạng** (Service Worker), nên `axiosClient` viết y hệt như gọi backend thật — không có `if (mock)` nào. Bật/tắt bằng
  `VITE_USE_MOCK` (`main.tsx:21` bật worker trước khi render). Handler trả `ok(data)` từ `mocks/tienIch.ts`; WebSocket giả ở `mocks/ws.ts`.

## 12. Tiếp cận được
- Tương phản: chữ thường ≥ 4,5:1, chữ lớn/thành phần đồ hoạ ≥ 3:1. Đã đo từ `index.css`: chữ trắng trên `primary` 6,02:1;
  `muted-foreground` trên nền trắng 4,73:1. Chữ không bao giờ tô bằng `chart-*` — dấu màu đứng cạnh mới mang danh tính.
- Vòng focus: `Button`, `Input`, `Checkbox` có sẵn `focus-visible:ring-3 focus-visible:ring-ring/50`. `features/` không có class focus riêng nào —
  dùng component `ui/`; viết `<button>` trần (đang có 19 chỗ) thì nó **không** có vòng này.
- Số liệu (tiền, điểm, số đếm, phân trang) luôn `tabular-nums` (98 chỗ) và định dạng `toLocaleString('vi-VN')`.
- Không truyền đạt chỉ bằng màu: chip có biểu tượng + chữ; % thay đổi KPI có `TrendingUp`/`TrendingDown`; `ChiBaoThoiGianThuc` hiện chữ khi
  bất thường, `role="status" aria-live="polite"`. Nút chỉ có biểu tượng phải có `aria-label` tiếng Việt (nút chế độ tối ở `AppShell.tsx:108`).

## 13. KHÔNG ĐƯỢC
- Gỡ `max-h-[calc(100dvh-2rem)]` + `overflow-y-auto` khỏi `DialogContent` (`ui/dialog.tsx:67`), hay truyền `className` ghi đè chúng (`cn` dùng
  `tailwind-merge` nên class sau thắng lặng lẽ) → hộp thoại căn giữa bằng `top-1/2 -translate-y-1/2` tràn **cả hai đầu** khung nhìn, hàng nút
  ở chân không cuộn tới, không bấm được. Đo ở SCR040: hộp thoại 1050px trong khung 813px, nút đồng ý ở y = 883. **`tsc` không bắt được.**
- Bỏ `noValidate` khỏi `<form>` → bong bóng kiểm tra của trình duyệt chặn submit trước react-hook-form, thông báo zod tiếng Việt không bao giờ hiện.
- Sửa tay `api-schema.d.ts` → mất ở lần `gen:api`; mock và giao ước lệch mà `tsc` không còn báo.
- Dùng `data` cho nội dung một bản ghi → hiện dữ liệu bản ghi trước dưới tiêu đề bản ghi sau.
- `axios.get`/`fetch`/`fetchBaseQuery` trong component → mất JWT, `X-Trace-Id`, luồng làm mới token.
- Import `@/app/store` từ `axiosClient` → vòng phụ thuộc `store → apiSlice → baseQuery → axiosClient → store` (dùng `truyCapStore.ts`).
- Đăng ký `columnFilteringFeature`/`rowPaginationFeature` cho `DataTable` → lọc trên 25 dòng của trang hiện tại mà tưởng đã lọc cả tập.
  Chép ví dụ v8 (`useReactTable`, `getVisibleCells`) → phương thức không tồn tại.
- Tự trì hoãn tìm kiếm hay tự thêm cột hộp kiểm trong màn dùng `ListPage` → làm hai lần; bỏ trì hoãn thì gõ "báo giá" sinh 7 mục cache.
- Gọi `useKetNoiThoiGianThuc()` ngoài `AppShell` → mở thêm socket (`window.mockThoiGianThuc.soClient()` phải luôn là 1).
  Đặt token lên URL WebSocket → token vào access log gateway (ADR-0013).
- Hex/màu Tailwind gốc trong JSX → không đổi theo `.dark`. Dùng `chart-*` làm màu trạng thái hoặc `success/warning/...` làm màu chuỗi → phá cơ chế
  an toàn cho người mù màu. Xoay vòng slot, hay đổi màu một chuỗi khi bộ lọc bớt chuỗi khác → người xem ghép nhầm thực thể.
- Xếp handler MSW có tham số trước đường dẫn cụ thể → `/erasure-requests/preview` bị hiểu thành `:id` (`mocks/handlers/index.ts:13`).
- Handler trả JSON trần thay vì `ok(...)` → phần bóc vỏ của `axiosClient` không được chạy thử trước khi nối backend thật.
- Có ô `tenantId` trên biểu mẫu → `tenant_id` chỉ đến từ ngữ cảnh đã xác thực; `schema.ts` cố ý không có trường này.
- Reset biểu mẫu khi đóng hộp thoại → người lỡ bấm ra ngoài mất hết thứ đã gõ. Reset sau khi gửi thành công.

## 14. Preset `radix-nova` (shadcn 4.x)
- Số đo **đặc hơn** shadcn cổ điển — lấy từ `src/components/ui/*.tsx`, đừng ước lượng: `Button` mặc định `h-8` (32px), `size="sm"` `h-7` (mẫu dùng `sm`
  cho thanh thao tác); `Input` `h-8 rounded-lg`; `Badge` `rounded-4xl`; `Card` dùng `ring-1 ring-foreground/10` thay đổ bóng;
  `destructive` là nền pha loãng `bg-destructive/10 text-destructive`, không phải nền đỏ đặc. Primitive nhập từ gói gộp `radix-ui`.
- shadcn 4.x **đã bỏ `Form`**: biểu mẫu = `useForm({ resolver: zodResolver(luocDo) })` + `Field` / `FieldLabel` / `FieldDescription` /
  `FieldError errors={[form.formState.errors.phone]}`. `Select`/`Checkbox` điều khiển bằng `form.watch` + `form.setValue` (`CreateContactDialog.tsx:155,173`). zod v4: `z.email(...)`.
- Hàm `cn` ở **`@/utils/cn`**, không phải `@/lib/utils` (`components.json` → `aliases.utils`). Toast là `Sonner`, không phải `Toast` cũ.

## 15. Checklist trước khi commit
- [ ] `npm run typecheck` sạch · [ ] `npm run build` sạch
- [ ] Không thêm hex/rgb/màu Tailwind gốc: `grep -rnE "#[0-9a-fA-F]{3,8}\b|rgba?\(|-(red|green|blue|gray)-[0-9]" src/features src/components/layout`
- [ ] Màn mới dùng một trong M1–M6 (hoặc có lý do là màn chữ ký); không import từ feature khác
- [ ] Có đủ trạng thái: rỗng-chưa-có-dữ-liệu, rỗng-vì-lọc, đang tải (Skeleton), lỗi (biểu mẫu qua `loi`, thao tác qua toast)
- [ ] Route mới có nhãn trong `NHAN_DUONG_DAN`; enum mới có `Record` đầy đủ trong `nhan.ts`; đổi dữ liệu thì đã sửa YAML + `gen:api`
- [ ] Biểu đồ mới: slot cố định, có nhãn trực tiếp hoặc bảng/thẻ số; số liệu `tabular-nums`

## 16. Điểm lệch đã ghi nhận (chỉ ghi, chưa sửa)
**Tài liệu ↔ code**
- Luật "không import chéo feature" (README, `.claude/rules/frontend.md`) đang bị vi phạm **8 chỗ**, đều tới `nhan.ts`: `conversations/nhan` ×4,
  `leads/nhan` ×3, `ai-agent/nhan` ×1. Chưa có chỗ chung được chốt cho bảng nhãn enum (`components/ui` không được biết nghiệp vụ).
- Số màn: README ghi **54/54**; `.claude/rules/frontend.md` ghi 58/58 và "37 trong 58"; comment trong code vẫn nói 58 (`AppSidebar.tsx:38`, `ListPage.tsx:63`).
- `docs/design/tokens.md` §5–6 lệch code: tiêu đề trang ghi `text-2xl` (code `text-xl`, 15 chỗ); số KPI `text-3xl` (code `text-2xl`); đệm trang `p-6`
  (5 mẫu dùng `p-4`); ô bảng `px-4 py-3` (`ui/table.tsx` `p-2`); "chỉ dùng bậc 2 3 4 6 8 12" (code `gap-1.5` ×54, `gap-1` ×39, `gap-0.5` ×34);
  không liệt kê `text-[13px]` (109 chỗ). §3 dẫn `node scripts/validate_palette.js` — file không tồn tại.
- README bảo màn chi tiết dùng `currentData`, nhưng `ContactDetailPage.tsx:47`, `LeadDetailPage.tsx:59`, `DealDetailPage.tsx:43` dùng `data`.
- Comment `hooks/useCheDo.ts:13` còn nhắc TanStack Query (đã gỡ theo ADR-0012).
- `npm run lint` hỏng: không có `eslint.config.*`; `ListPage.tsx:98` có `eslint-disable` cho plugin `react-hooks` chưa cài.
- `vite.config.ts` đọc `process.env.VITE_GATEWAY_URL`, nhưng Vite không nạp `.env` vào `process.env` khi đọc config → giá trị trong `.env`
  không đổi được đích proxy (cần `loadEnv` hoặc biến môi trường của shell).

**Hành vi dễ gây hiểu nhầm**
- Lỗi tải bị nuốt: `ListPage`/`DataTable` không có prop lỗi → truy vấn hỏng hiện `EmptyState` "chưa có dữ liệu" kèm nút tạo mới. Chỉ `LoginPage`,
  `VerifyEmailPage` đọc `isError`. `TenantProfilePage.tsx:69` `dangTai={truyVan.isLoading || !nhap}` → lỗi tải thành xương vô hạn.
- `ui/sonner.tsx` dùng `useTheme` của `next-themes` nhưng không có `ThemeProvider` → toast theo hệ điều hành, không theo nút chế độ của app.
  `useCheDo` chỉ chạy trong `AppShell` và `index.html` không đặt lớp sớm → màn đăng nhập không theo lựa chọn tối; khung đầu vẽ ở chế độ sáng.
- Màu chuỗi dùng làm trạng thái: "Trực tuyến" = `bg-chart-2` (cam), "Đang nối" = `bg-chart-3` (`ChiBaoThoiGianThuc.tsx:11-13`);
  `RolesPage.tsx:30`, `LeadDetailPage.tsx:304`, `SubscriptionPage.tsx:247` dùng `chart-2` cho nghĩa "tốt/có".
- Cùng thực thể, khác màu: "Người xử lý" là `chart-2` ở `OverviewPage.tsx:234` nhưng `chart-1` ở `ConversationStatsPage.tsx:103,158`. Biểu đồ đường của
  `OverviewPage` dùng `chart-3` mà chỉ có `Legend`, không nhãn trực tiếp hay bảng.
- Tương phản `StatusChip` ở chế độ sáng (tính từ oklch trong `index.css`): `warning` 3,26:1, `destructive` 3,84:1, `success` 4,37:1 — dưới 4,5:1
  cho `text-xs`. `text-warning` trên nền trắng 3,75:1 (`AppSidebar.tsx:272`). Chữ trắng trên màu widget mặc định `#2a78d6` 4,42:1.
- Không co theo màn hẹp: `DetailPage` cột phụ `w-80`, hộp thư hai cột `w-80` (`ConversationList`, `ContextPanel`), ô tìm `w-[280px]` trên thanh trên.
- Số liệu viết cứng: huy hiệu hộp thư `'12'` và hạn mức `1.842/2.000` (`AppSidebar.tsx:43,269`); `thayDoi: 4.2 / 8.1 / -12.4` (`OverviewPage.tsx:90-119`),
  đổi khoảng thời gian không đổi tham số truy vấn (`useTongQuanQuery({})`). `LoginPage.tsx:15-16` điền sẵn email và mật khẩu mẫu.
- Dấu vết màn đã gỡ: `NHAN_DUONG_DAN` còn `phien`, `quy-tac-phan-cong`, `bao-cao`; chân `LoginPage` hứa "tự thu hồi được ở mục Bảo mật" (SCR011 đã gỡ).
- Nhãn đọc màn hình tiếng Anh `Close` ở `ui/dialog.tsx:82`, `ui/sheet.tsx:80`.

**Lặp code đáng gom sau này**
- `const so`/`const tien` (`Intl.NumberFormat('vi-VN')`) khai lại ở 10 file, cộng `tienVnd` (`ai-agent/nhan.ts`) và `tien` (`leads/nhan.ts`).
- Đầu trang `<h1 className="text-xl font-semibold tracking-tight">` viết lại ở 10 file feature ngoài 5 mẫu layout.
- Ô chữ cái đầu viết tay 9 chỗ trong khi `ui/avatar.tsx` không ai dùng; `command`, `dropdown-menu`, `popover`, `input-group`, `badge` cũng 0 import.
- `NHAN_MUC_NGHIEM_TRONG` khai ở cả `ai-agent/nhan.ts:102` và `audit/nhan.ts:11`. `ChuaChonHoiThoai` (`InboxPage.tsx:106`) chép markup `EmptyState`.
- `DataTable` bọc thêm `div overflow-x-auto` quanh `Table`, trong khi `ui/table.tsx` đã có `table-container` cuộn ngang.
