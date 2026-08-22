# ADR-0012 — Redux Toolkit và RTK Query quản lý toàn bộ state của web-dashboard

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-08-21
- **Làn sở hữu:** Track A

## Bối cảnh

Bản dựng đầu của `web-dashboard` dùng **hai** thư viện quản lý state, theo đúng khuyến nghị mặc
định của hệ sinh thái React: TanStack Query cho dữ liệu lấy từ máy chủ, zustand cho phiên đăng
nhập và trạng thái giao diện. Cách này chạy được và đã qua kiểm thử end-to-end.

Hai điều buộc phải xem lại:

1. **Yêu cầu của nhóm:** state phải quản lý bằng Redux. Đây là ràng buộc của đồ án, không phải
   một sở thích kỹ thuật có thể thương lượng.
2. **Tỉ trọng thật của hai loại state.** Đếm trên 58 màn hình: 19 màn là danh sách có lọc và phân
   trang, 4 màn chi tiết, 7 biểu mẫu, 6 màn thống kê — gần như toàn bộ state của dashboard là dữ
   liệu lấy từ máy chủ. Client state thật sự chỉ có `accessToken`, hồ sơ người dùng, và chế độ
   sáng/tối.

Thời điểm quyết định cũng quan trọng: lúc này zustand mới xuất hiện ở **đúng một file**
(`app/store/authStore.ts`) và TanStack Query ở ba file. Chuyển sau khi dựng xong 6 mẫu lặp và 21
màn chữ ký thì đắt gấp nhiều lần.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| **A.** Redux Toolkit cho client state, giữ TanStack Query cho server state | Sửa ít nhất — một file | Redux chỉ còn giữ mỗi token; câu "quản lý state bằng Redux" thành nửa đúng, và dự án mang hai thư viện state cạnh nhau mà không giải thích được vì sao |
| **B.** Redux Toolkit + **RTK Query** cho tất cả | Một kiến trúc state duy nhất; cache nằm trong store nên Redux DevTools thấy toàn bộ; `createApi` sinh sẵn hook cho từng endpoint | Phải viết `baseQuery` riêng để giữ `axiosClient`; RTK Query ít tài liệu bên thứ ba hơn TanStack Query |
| **C.** Redux Toolkit + `createAsyncThunk`, không dùng RTK Query | Dạng Redux cổ điển, dễ nhận ra nhất | Phải tự viết `pending`/`fulfilled`/`rejected`, chống trùng request, và vô hiệu hóa cache cho **19 màn danh sách** — lặp lại đúng thứ RTK Query đã làm sẵn |
| **D.** Giữ nguyên TanStack Query + zustand | Không phải sửa gì | Không đáp ứng ràng buộc của nhóm |

## Quyết định

Chọn **B**: Redux Toolkit là cơ chế state duy nhất của `web-dashboard`. Dữ liệu máy chủ đi qua
**RTK Query** (`src/api/apiSlice.ts`, mỗi nhóm endpoint một file gọi `injectEndpoints`); phiên
đăng nhập nằm ở một slice thường (`src/app/store/authSlice.ts`). Gỡ `zustand` và
`@tanstack/react-query` khỏi `package.json`.

`axiosClient` **giữ nguyên**. RTK Query gọi nó qua một `baseQuery` tự viết
(`src/api/baseQuery.ts`) thay cho `fetchBaseQuery` mặc định.

## Lập luận

Phương án A không sai về kỹ thuật nhưng sai về tỉ trọng: khi ~90% state là dữ liệu máy chủ, để
Redux giữ mỗi `accessToken` rồi nói dự án "quản lý state bằng Redux" là mô tả không trung thực về
kiến trúc. Hội đồng mở Redux DevTools ra sẽ thấy một store gần như rỗng.

Phương án C là cái bẫy dễ rơi vào nhất vì trông "Redux thuần" hơn. Nhưng 19 màn danh sách cùng
kiểu M1 nghĩa là 19 lần viết lại ba nhánh trạng thái, 19 lần tự chống trùng request khi người
dùng gõ nhanh vào ô tìm kiếm. RTK Query là một phần **chính thức** của Redux Toolkit, không phải
thư viện ngoài — chọn nó không làm dự án bớt "Redux" đi chút nào.

Việc giữ `axiosClient` thay vì dùng `fetchBaseQuery` là để không viết lại lần hai ba thứ đã có và
đã kiểm: gắn `Authorization`, gắn `X-Trace-Id`, và luồng xếp hàng khi làm mới token sau lỗi 401.
Cái giá là một file 50 dòng.

## Đánh đổi

- **`data` giữ kết quả của tham số cũ khi tham số đổi.** Với danh sách thì đây là ưu điểm (không
  nháy trắng); với **nội dung một hội thoại thì là sai lệch** — nó hiển thị tin nhắn của khách A
  dưới tên khách B trong khoảnh khắc chuyển. Chỗ nào hiển thị nội dung của một bản ghi cụ thể
  phải dùng `currentData`, không phải `data`. Đây là bẫy thường trực, không phải việc sửa một lần.
- **Lỗi phải là object thuần.** `ApiError` là một `Error`, không serialize được, nên `baseQuery`
  phải chuyển nó thành `{ status, message, traceId }`. Màn hình đọc lỗi phải qua `laLoiTruyVan()`
  để thu hẹp kiểu — dài dòng hơn `error instanceof ApiError`.
- **Ít tài liệu bên thứ ba hơn.** Phần lớn ví dụ React trên mạng dùng TanStack Query; gặp vấn đề
  lạ sẽ mất thời gian tra hơn.
- **Không có `redux-persist`.** Lưu phiên xuống `localStorage` viết bằng một listener của RTK
  (~10 dòng). Đổi lại: nếu về sau cần lưu thêm nhiều nhánh state thì phải tự mở rộng listener đó
  thay vì có sẵn cơ chế.
- **Một `createApi` duy nhất** nghĩa là mọi nhóm endpoint chia sẻ một `tagTypes` và một
  `keepUnusedDataFor`. Nếu một nhóm cần chính sách cache khác hẳn thì phải đặt riêng ở từng
  endpoint chứ không tách được ở cấp API.
- Phải viết lại 8 file đang chạy tốt. Công này bỏ ra vào lúc mới có 2 màn hình là rẻ nhất, nhưng
  vẫn là công bỏ ra.

## Hệ quả

- **Schema:** không ảnh hưởng.
- **Giao ước hai làn:** không ảnh hưởng. Đây là quyết định nội bộ của `web-dashboard`.
- **Vận hành:** `package.json` bớt `zustand` và `@tanstack/react-query`, thêm `@reduxjs/toolkit`
  và `react-redux`. Tầng mock MSW không đổi một dòng nào — nó chặn ở tầng mạng, dưới cả axios lẫn
  RTK Query.
- **Tài liệu phải sửa theo:** `.claude/rules/frontend.md` và `web-dashboard/README.md` đang ghi
  "TanStack Query cho server state · zustand cho client state" — sửa trong cùng thay đổi này, vì
  rule lệch với thực tế còn tệ hơn không có rule.
- **Báo cáo:** chương 3 lấy ADR này. Điểm đáng viết là **lý do chọn RTK Query thay vì
  `createAsyncThunk`** — nó cho thấy quyết định dựa trên số màn hình thật của hệ thống chứ không
  theo thói quen.
