# Token thiết kế — web-dashboard

Nguồn sự thật cho giao diện dashboard. **Dán nguyên file này vào mọi prompt `/design`** —
đây là cơ chế khiến việc chuyển canvas sang React thành ánh xạ 1-1 thay vì dịch tay.

| | |
|---|---|
| Nền tảng | Tailwind **v4** (CSS-first, không có `tailwind.config.js`) + shadcn/ui CLI 4.x |
| Preset | `radix-nova` — cơ sở Radix UI, biểu tượng Lucide, chữ Geist |
| File thật | `web-dashboard/src/styles/index.css` — **file đó là nguồn, file này là bản chép để tra cứu** |
| Cấu hình CLI | `web-dashboard/components.json` |

Token khai trong `@theme inline` rồi gán giá trị ở `:root` (sáng) và `.dark` (tối).
Đổi màu thì sửa `index.css`, **không sửa từng component**.

---

## 1. Màu giao diện

| Token | Sáng (oklch) | Sáng (hex) | Tối (oklch) | Tối (hex) |
|---|---|---|---|---|
| `--background` | `oklch(1 0 0)` | `#ffffff` | `oklch(0.145 0 0)` | `#0a0a0a` |
| `--foreground` | `oklch(0.145 0 0)` | `#0a0a0a` | `oklch(0.985 0 0)` | `#fafafa` |
| `--card` | `oklch(1 0 0)` | `#ffffff` | `oklch(0.205 0 0)` | `#171717` |
| `--card-foreground` | `oklch(0.145 0 0)` | `#0a0a0a` | `oklch(0.985 0 0)` | `#fafafa` |
| `--primary` | `oklch(0.51 0.19 266)` | `#3259d1` | `oklch(0.72 0.14 266)` | `#7ba1fc` |
| `--primary-foreground` | `oklch(0.985 0 0)` | `#fafafa` | `oklch(0.2 0.05 266)` | `#0b152d` |
| `--secondary` | `oklch(0.97 0 0)` | `#f5f5f5` | `oklch(0.269 0 0)` | `#262626` |
| `--secondary-foreground` | `oklch(0.205 0 0)` | `#171717` | `oklch(0.985 0 0)` | `#fafafa` |
| `--muted` | `oklch(0.97 0 0)` | `#f5f5f5` | `oklch(0.269 0 0)` | `#262626` |
| `--muted-foreground` | `oklch(0.556 0 0)` | `#737373` | `oklch(0.708 0 0)` | `#a1a1a1` |
| `--accent` | `oklch(0.97 0 0)` | `#f5f5f5` | `oklch(0.269 0 0)` | `#262626` |
| `--accent-foreground` | `oklch(0.205 0 0)` | `#171717` | `oklch(0.985 0 0)` | `#fafafa` |
| `--border` | `oklch(0.922 0 0)` | `#e5e5e5` | `oklch(1 0 0 / 10%)` | — |
| `--input` | `oklch(0.922 0 0)` | `#e5e5e5` | `oklch(1 0 0 / 15%)` | — |
| `--ring` | `oklch(0.62 0.15 266)` | `#5b81e0` | `oklch(0.62 0.15 266)` | `#5b81e0` |
| `--sidebar` | `oklch(0.985 0 0)` | `#fafafa` | `oklch(0.205 0 0)` | `#171717` |

**Màu thương hiệu là chàm (indigo).** Preset `nova` gốc cho `--primary` xám gần đen; đã đổi
sang chàm để dashboard có bản sắc riêng. Chữ trắng đè lên nền chàm sáng đạt **6,03:1**
(WCAG AA cần 4,5:1). Chế độ tối theo quy ước đảo của `nova`: nền chàm nhạt + chữ tối, đạt
**7,20:1** cho chữ và **7,87:1** so với nền.

## 2. Màu trạng thái — dành riêng

**Không bao giờ dùng lại làm màu chuỗi dữ liệu**, và **luôn đi kèm biểu tượng + nhãn chữ**,
không bao giờ chỉ dựa vào màu.

| Token | Sáng | Tối | Dùng cho |
|---|---|---|---|
| `--success` | `#007e46` | `#3bb974` | `ACTIVE` · `READY` · `ALLOWED` · `WON` · `RESOLVED` |
| `--warning` | `#be7200` | `#efa831` | `PENDING_AGENT` · `NEEDS_APPROVAL` · `PAST_DUE` · hạn mức 80% |
| `--destructive` | `#e7000b` | `#ff6467` | `FAILED` · `BLOCKED` · `LOST` · `SUSPENDED` · hạn mức 100% |
| `--info` | `#3259d1` | `#7ba1fc` | `BOT_HANDLING` · `PROCESSING` · `QUEUED` · `TRIALING` |

Mỗi màu có token chữ đi kèm (`--success-foreground` …). Chú ý `--warning` chế độ sáng dùng
**chữ tối** (5,28:1), không phải chữ trắng.

## 3. Màu biểu đồ — đã qua kiểm định, không tự đổi

Giữ nguyên **mã hex**, cố ý không quy đổi sang oklch để tránh sai số làm lệch kết quả kiểm định.

| Slot | Sắc | Sáng | Tối |
|---|---|---|---|
| `--chart-1` | xanh dương | `#2a78d6` | `#3987e5` |
| `--chart-2` | cam | `#eb6834` | `#d95926` |
| `--chart-3` | xanh ngọc | `#1baf7a` | `#199e70` |
| `--chart-4` | vàng | `#eda100` | `#c98500` |
| `--chart-5` | hồng sen | `#e87ba4` | `#d55181` |

Kết quả kiểm định (nền card `#ffffff` / `#171717`):

| Kiểm tra | Sáng | Tối |
|---|---|---|
| Dải độ sáng | đạt | đạt |
| Sàn độ bão hòa | đạt | đạt |
| Phân tách mù màu (ΔE ≥ 8) | **9,1** | **8,4** |
| Sàn thị lực thường (ΔE ≥ 15) | **19,6** | **19,3** |
| Tương phản với nền (≥ 3:1) | *cần cứu trợ* | đạt |

### Ràng buộc bắt buộc khi vẽ biểu đồ

1. **Chế độ sáng: xanh ngọc, vàng và hồng sen đều dưới 3:1 trên nền trắng** → mọi biểu đồ
   dùng các slot đó **phải** có nhãn trực tiếp nhìn thấy được hoặc kèm bảng dữ liệu. Đây là
   nghĩa vụ, không phải khuyến nghị bỏ qua được.
2. **Gán màu theo thứ tự slot cố định, không bao giờ xoay vòng.** Thứ tự slot chính là cơ
   chế an toàn cho người mù màu. Chuỗi thứ 6 trở đi thì gộp vào "Khác" hoặc tách thành
   nhiều biểu đồ nhỏ, **không sinh thêm màu mới**.
3. **Màu đi theo thực thể, không theo thứ hạng.** Bộ lọc làm đổi số chuỗi thì các chuỗi còn
   lại phải giữ nguyên màu.
4. **Không bao giờ dùng hai trục y.** Hai đại lượng khác thang thì tách hai biểu đồ, hoặc
   qui về cùng một mốc chỉ số.
5. **Không dùng ba slot đầu trở lên cho biểu đồ phân tán / bong bóng / bản đồ nhiệt.**
   Ở các dạng đó mọi cặp đều có thể đứng cạnh nhau, và slot 4 (vàng) đặt cạnh slot 2 (cam)
   không đạt sàn — **giới hạn 3 chuỗi**, quá thì gộp "Khác" hoặc tách nhỏ.
6. **Từ 2 chuỗi trở lên luôn có chú giải**; 1 chuỗi thì tiêu đề đã nói rõ, không cần hộp
   chú giải. Không ghi số lên mọi điểm.
7. **Chữ mặc token chữ** (`--foreground` / `--muted-foreground`), không bao giờ tô theo màu
   chuỗi. Dấu màu đứng cạnh mới là thứ mang danh tính.
8. Nét mảnh: đường 2px, điểm đánh dấu ≥ 8px, đầu cột bo 4px neo vào đường cơ sở, khe hở 2px
   màu nền giữa các mảng kề nhau. Lưới và trục phải lùi về sau.

Kiểm lại bất cứ lúc nào đổi màu:

```bash
node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4" --mode light --surface "#ffffff"
node scripts/validate_palette.js "#3987e5,#d95926,#199e70,#c98500,#d55181" --mode dark  --surface "#171717"
```

## 4. Bo góc

`--radius: 0.625rem` (10px). Các bậc dẫn xuất — dùng tên bậc, đừng ghi số px:

| Lớp | Công thức | Giá trị |
|---|---|---|
| `rounded-sm` | `--radius × 0.6` | 6px |
| `rounded-md` | `--radius × 0.8` | 8px |
| `rounded-lg` | `--radius` | 10px |
| `rounded-xl` | `--radius × 1.4` | 14px |
| `rounded-2xl` | `--radius × 1.8` | 18px |

## 5. Chữ

Bộ chữ **Geist Variable** (`@fontsource-variable/geist`, có sẵn subset **vietnamese** — dấu
tiếng Việt hiển thị đúng, không phải chữ dự phòng). `--font-heading` trỏ về `--font-sans`.

| Vai trò | Lớp Tailwind | Cỡ |
|---|---|---|
| Tiêu đề trang | `text-2xl font-semibold tracking-tight` | 24px |
| Tiêu đề mục | `text-lg font-semibold` | 18px |
| Tiêu đề thẻ | `text-sm font-medium` | 14px |
| Nội dung | `text-sm` | 14px |
| Phụ chú | `text-xs text-muted-foreground` | 12px |
| Số liệu KPI | `text-3xl font-semibold tabular-nums` | 30px |

Số liệu (tiền, điểm, số đếm) **luôn `tabular-nums`** để cột số không nhảy khi giá trị đổi.

## 6. Thang khoảng cách

Chỉ dùng các bậc `2 3 4 6 8 12` (8px, 12px, 16px, 24px, 32px, 48px). Bậc lẻ ngoài danh sách
này là dấu hiệu đang căn bằng mắt.

| Chỗ | Bậc |
|---|---|
| Trong một thẻ | `p-6`, các phần cách nhau `gap-4` |
| Giữa các thẻ | `gap-4` |
| Đệm quanh nội dung trang | `p-6` |
| Ô của bảng | `px-4 py-3` |
| Nút / ô nhập, khoảng cách trong | `gap-2` |

## 7. Component đã cài — tên khối trên canvas

Trên artboard, đặt tên mỗi khối bằng đúng tên component tương ứng (trong comment HTML) để
bước chuyển sang React ánh xạ được 1-1.

| Component | Đường dẫn | Dùng ở màn |
|---|---|---|
| `Button` `Input` `Label` `Textarea` `Checkbox` `Select` | `@/components/ui/…` | khắp nơi |
| `Field` | `@/components/ui/field` | **thay cho `Form` cũ** — shadcn 4.x đã bỏ `Form` |
| `Card` `Separator` `Skeleton` `Progress` `Alert` | | KPI, hạn mức, trạng thái |
| `Table` | | 19 màn kiểu danh sách |
| `Tabs` `Badge` `Avatar` `Tooltip` | | chi tiết, danh bạ |
| `Dialog` `Sheet` `Popover` `DropdownMenu` `Command` | | thao tác, bộ lọc, tìm nhanh |
| `Sidebar` | `@/components/ui/sidebar` | khung ứng dụng AppShell |
| `Sonner` | `@/components/ui/sonner` | thông báo nổi (thay `Toast` cũ) |
| `InputGroup` | | ô tìm kiếm có biểu tượng |

Thêm component mới: `npx shadcn@latest add <tên>`. Hàm gộp class là `cn` ở
`@/utils/cn` (đã chỉnh `components.json` để khớp bố cục repo, **không phải** `@/lib/utils`
mặc định của shadcn).

## 8. Ràng buộc khi vẽ artboard

1. **Dùng đúng token ở trên**, không tự chọn màu, bo góc hay khoảng cách khác.
2. **Mọi chữ trên giao diện bằng tiếng Việt có dấu.**
3. **Vẽ cả trạng thái rỗng và trạng thái đang tải**, không chỉ trạng thái đầy dữ liệu — 58
   màn đều cần và đó là chỗ dễ quên nhất khi chuyển sang code.
4. **Giá trị enum phải lấy từ `docs/openapi/dashboard-api.yaml`** (mục `components/schemas`),
   không bịa. Đây là nguồn chân lý của enum; `docs/erd-ai-crm.md` và ràng buộc `CHECK` trong
   migration đều **theo** hợp đồng này chứ không ngược lại.
5. **Không vẽ trường `tenant_id` trên bất kỳ biểu mẫu nào** — nó luôn đến từ ngữ cảnh đã xác
   thực, không bao giờ từ người dùng nhập.
