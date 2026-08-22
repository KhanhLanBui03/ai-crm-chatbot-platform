import { apiSlice } from '@/api/apiSlice'
import type { Page } from '@/types/api'
import type {
  DiemSuDungNgay,
  DoanhNghiep,
  GoiDichVu,
  HanMucSuDung,
  MaGoi,
  MaVaiTro,
  NguoiDung,
  PhienDangNhap,
  ThueBao,
  TrangThaiNguoiDung,
  VaiTro,
} from '@/types/schema'

/**
 * Nền tảng, tài khoản, gói dịch vụ — SCR007–SCR015.
 *
 * Nhóm chung một file vì cùng một nhãn cache: đổi gói làm hạn mức đổi theo, mời người dùng làm
 * cả danh sách lẫn số người dùng trong hạn mức đổi theo.
 */

export interface BoLocNguoiDung {
  tuKhoa?: string
  trangThai?: TrangThaiNguoiDung
  vaiTro?: MaVaiTro
  trang?: number
  sapXep?: string
}

const CA_NGUOI_DUNG = { type: 'NguoiDung' as const, id: 'DANH-SACH' }

export const platformApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    // ── SCR008 · SCR009 — người dùng ───────────────────────────────────────────
    danhSachNguoiDung: build.query<Page<NguoiDung>, BoLocNguoiDung>({
      query: (bo) => ({
        url: '/api/v1/users',
        params: {
          q: bo.tuKhoa || undefined,
          status: bo.trangThai,
          roleCode: bo.vaiTro,
          sort: bo.sapXep,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: (kq) =>
        kq
          ? [...kq.items.map(({ id }) => ({ type: 'NguoiDung' as const, id })), CA_NGUOI_DUNG]
          : [CA_NGUOI_DUNG],
    }),

    moiNguoiDung: build.mutation<
      NguoiDung,
      { email: string; fullName?: string | null; roleCode: MaVaiTro }
    >({
      query: (than) => ({ url: '/api/v1/users', method: 'POST', body: than }),
      // Mời thêm người làm đổi cả danh sách lẫn ô "người dùng" của hạn mức (SCR014)
      invalidatesTags: [CA_NGUOI_DUNG, { type: 'HanMuc', id: 'HIEN-TAI' }],
    }),

    voHieuHoaNguoiDung: build.mutation<NguoiDung, string>({
      query: (id) => ({ url: `/api/v1/users/${id}/disable`, method: 'POST' }),
      invalidatesTags: (_kq, _loi, id) => [{ type: 'NguoiDung', id }, CA_NGUOI_DUNG],
    }),

    guiLaiLoiMoi: build.mutation<void, string>({
      query: (id) => ({ url: `/api/v1/users/${id}/resend-invitation`, method: 'POST' }),
    }),

    // ── SCR010 — ma trận phân quyền ───────────────────────────────────────────
    danhSachVaiTro: build.query<VaiTro[], void>({
      query: () => ({ url: '/api/v1/roles' }),
      providesTags: ['VaiTro'],
    }),

    // ── SCR007 — hồ sơ doanh nghiệp ───────────────────────────────────────────
    hoSoDoanhNghiep: build.query<DoanhNghiep, void>({
      query: () => ({ url: '/api/v1/tenant' }),
      providesTags: ['Tenant'],
    }),

    capNhatDoanhNghiep: build.mutation<DoanhNghiep, Partial<DoanhNghiep>>({
      query: (than) => ({ url: '/api/v1/tenant', method: 'PATCH', body: than }),
      invalidatesTags: ['Tenant'],
    }),

    // ── SCR012 · SCR013 — thuê bao và gói dịch vụ ─────────────────────────────
    thueBaoHienTai: build.query<ThueBao, void>({
      query: () => ({ url: '/api/v1/subscription' }),
      providesTags: ['GoiDichVu'],
    }),

    danhSachGoi: build.query<GoiDichVu[], void>({
      query: () => ({ url: '/api/v1/plans' }),
      providesTags: ['GoiDichVu'],
    }),

    doiGoi: build.mutation<ThueBao, MaGoi>({
      query: (planCode) => ({
        url: '/api/v1/subscription/change',
        method: 'POST',
        body: { planCode },
      }),
      // Đổi gói là đổi luôn mẫu số của mọi hạn mức
      invalidatesTags: ['GoiDichVu', 'HanMuc'],
    }),

    // ── SCR014 · SCR015 — hạn mức ─────────────────────────────────────────────
    hanMucHienTai: build.query<HanMucSuDung, void>({
      query: () => ({ url: '/api/v1/usage' }),
      providesTags: [{ type: 'HanMuc', id: 'HIEN-TAI' }],
    }),

    mucSuDungTheoNgay: build.query<
      Page<DiemSuDungNgay>,
      { tuNgay?: string; denNgay?: string; nhomTheo?: 'channel' | 'route'; trang?: number; sapXep?: string }
    >({
      query: (bo) => ({
        url: '/api/v1/usage/daily',
        params: {
          from: bo.tuNgay,
          to: bo.denNgay,
          groupBy: bo.nhomTheo,
          sort: bo.sapXep,
          page: bo.trang ?? 0,
          size: 12,
        },
      }),
      providesTags: ['HanMuc'],
    }),

    // ── SCR011 — phiên đăng nhập ──────────────────────────────────────────────
    danhSachPhien: build.query<PhienDangNhap[], void>({
      query: () => ({ url: '/api/v1/me/sessions' }),
      providesTags: ['PhienDangNhap'],
    }),

    thuHoiPhien: build.mutation<void, string>({
      query: (id) => ({ url: `/api/v1/me/sessions/${id}`, method: 'DELETE' }),
      invalidatesTags: ['PhienDangNhap'],
    }),
  }),
})

export const {
  useDanhSachNguoiDungQuery,
  useMoiNguoiDungMutation,
  useVoHieuHoaNguoiDungMutation,
  useGuiLaiLoiMoiMutation,
  useDanhSachVaiTroQuery,
  useHoSoDoanhNghiepQuery,
  useCapNhatDoanhNghiepMutation,
  useThueBaoHienTaiQuery,
  useDanhSachGoiQuery,
  useDoiGoiMutation,
  useHanMucHienTaiQuery,
  useMucSuDungTheoNgayQuery,
  useDanhSachPhienQuery,
  useThuHoiPhienMutation,
} = platformApi
