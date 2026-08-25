import { createApi } from '@reduxjs/toolkit/query/react'

import { axiosBaseQuery } from '@/api/baseQuery'

/**
 * Một `createApi` duy nhất cho toàn bộ dashboard. Mỗi nhóm endpoint là một file trong `src/api/`
 * gọi `apiSlice.injectEndpoints(...)` — chia nhỏ như vậy để không có file nào phình lên theo 58
 * màn hình, mà cache vẫn nằm chung một chỗ trong store (`state.api`).
 *
 * Vì sao RTK Query chứ không phải slice + `createAsyncThunk`: 19 trong 58 màn là danh sách có
 * lọc/phân trang. Viết tay `pending / fulfilled / rejected` cộng chống trùng request cho từng màn
 * là lặp lại đúng thứ RTK Query đã làm sẵn.
 */
export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: axiosBaseQuery,
  /**
   * Nhãn cache theo nhóm bảng của ERD. Ghi (mutation) `invalidatesTags` nhãn nào thì mọi truy vấn
   * `providesTags` nhãn đó tự nạp lại — không phải gọi refetch bằng tay ở từng màn.
   */
  tagTypes: [
    // Nền tảng, tài khoản, gói dịch vụ
    'Tenant',
    'NguoiDung',
    'VaiTro',
    'GoiDichVu',
    'HanMuc',
    'NhatKyKiemToan',
    // Kênh và hộp thư
    'Kenh',
    'HoiThoai',
    'TinNhan',
    // Khách hàng
    'KhachHang',
    // Tri thức
    'TaiLieu',
    'ChunkTriThuc',
    // Tác tử AI và giám sát
    'TacTuAI',
    'MauNhacViec',
    'ToolCall',
    'TuongTacAI',
    // Bán hàng
    'Lead',
    'Deal',
    'GiaiDoanDeal',
    'HoatDong',
    // Phân tích
    'BaoCao',
  ],
  /**
   * Bao lâu thì bỏ cache của một truy vấn không còn component nào dùng (giây).
   * Mặc định của RTK Query là 60; giữ nguyên vì dữ liệu CRM đổi liên tục.
   */
  keepUnusedDataFor: 60,
  /**
   * Mất mạng rồi có lại thì nạp lại — hộp thư mà hiện dữ liệu của mười phút trước là sai lệch
   * nguy hiểm hơn là để trống. Ngược lại `refetchOnFocus` để nguyên mặc định (tắt): chuyển qua lại
   * giữa các tab là thao tác thường xuyên, nạp lại mỗi lần chỉ tốn hạn mức.
   */
  refetchOnReconnect: true,
  endpoints: () => ({}),
})
