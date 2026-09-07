import { apiSlice } from '@/api/apiSlice'
import type { DangKyResult, KetQuaDangNhap, NguoiDungHienTai } from '@/types/schema'

export interface ThanDangNhap {
  email: string
  password: string
}

export interface ThanDangKy {
  companyName: string
  industry?: string | null
  fullName: string
  email: string
  password: string
  timezone?: string
  acceptedTerms: boolean
}

/**
 * Xác thực và vòng đời tài khoản — SCR001–SCR005.
 *
 * Không endpoint nào ở đây `providesTags` hay `invalidatesTags`: chúng chạy **trước** khi có
 * phiên đăng nhập, nên không có cache nào của người dùng để làm mới. Gắn nhãn vào chỉ khiến các
 * truy vấn của phiên trước đó (nếu tab còn mở) nạp lại bằng token đã hết hiệu lực.
 */
export const authApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    dangNhap: build.mutation<KetQuaDangNhap, ThanDangNhap>({
      query: (than) => ({ url: '/api/v1/auth/login', method: 'POST', body: than }),
    }),

    // ── SCR001 — đăng ký doanh nghiệp ─────────────────────────────────────────
    /** Không gửi `slug`: máy chủ sinh từ `companyName` rồi tự bảo đảm duy nhất. */
    dangKy: build.mutation<DangKyResult, ThanDangKy>({
      query: (than) => ({ url: '/api/v1/auth/register', method: 'POST', body: than }),
    }),

    // ── SCR002 — xác thực địa chỉ thư ─────────────────────────────────────────
    xacThucThu: build.mutation<null, { token: string }>({
      query: (than) => ({ url: '/api/v1/auth/verify-email', method: 'POST', body: than }),
    }),

    guiLaiThuXacThuc: build.mutation<null, { email: string }>({
      query: (than) => ({
        url: '/api/v1/auth/resend-verification',
        method: 'POST',
        body: than,
      }),
    }),

    // ── SCR004 · SCR005 — quên và đặt lại mật khẩu ────────────────────────────
    quenMatKhau: build.mutation<null, { email: string }>({
      query: (than) => ({ url: '/api/v1/auth/forgot-password', method: 'POST', body: than }),
    }),

    datLaiMatKhau: build.mutation<null, { token: string; newPassword: string }>({
      query: (than) => ({ url: '/api/v1/auth/reset-password', method: 'POST', body: than }),
    }),

    /** Hồ sơ của chính người đang đăng nhập. Máy chủ đọc tenant từ JWT, không nhận tham số nào. */
    hoSoCuaToi: build.query<NguoiDungHienTai, void>({
      query: () => ({ url: '/api/v1/me' }),
      providesTags: [{ type: 'NguoiDung', id: 'TOI' }],
    }),
  }),
})

export const {
  useDangNhapMutation,
  useDangKyMutation,
  useXacThucThuMutation,
  useGuiLaiThuXacThucMutation,
  useQuenMatKhauMutation,
  useDatLaiMatKhauMutation,
  useHoSoCuaToiQuery,
} = authApi
