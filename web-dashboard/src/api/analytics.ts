import { apiSlice } from '@/api/apiSlice'
import type { Page } from '@/types/api'
import type {
  BacPheu,
  DiemHoiThoaiNgay,
  LoaiBaoCao,
  TepBaoCao,
  ThongKeChuDe,
  TongQuan,
} from '@/types/schema'

/** Phân tích và báo cáo — SCR006, SCR048–SCR053. */

export interface KhoangNgay {
  tuNgay?: string
  denNgay?: string
}

export const analyticsApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    // SCR006 và SCR048 dùng chung endpoint: cùng một bộ số, khác nhau ở người đọc
    tongQuan: build.query<TongQuan, KhoangNgay>({
      query: (bo) => ({
        url: '/api/v1/analytics/overview',
        params: { from: bo.tuNgay, to: bo.denNgay },
      }),
      providesTags: ['BaoCao'],
    }),

    hoiThoaiTheoNgay: build.query<
      DiemHoiThoaiNgay[],
      KhoangNgay & { nhomTheo?: 'channel' | 'assignee' }
    >({
      query: (bo) => ({
        url: '/api/v1/analytics/conversations',
        params: { from: bo.tuNgay, to: bo.denNgay, groupBy: bo.nhomTheo },
      }),
      providesTags: ['BaoCao'],
    }),

    pheuChuyenDoi: build.query<BacPheu[], KhoangNgay & { nguonLead?: string }>({
      query: (bo) => ({
        url: '/api/v1/analytics/funnel',
        params: { from: bo.tuNgay, to: bo.denNgay, leadSource: bo.nguonLead },
      }),
      providesTags: ['BaoCao'],
    }),

    thongKeChuDe: build.query<ThongKeChuDe[], KhoangNgay>({
      query: (bo) => ({
        url: '/api/v1/analytics/topics',
        params: { from: bo.tuNgay, to: bo.denNgay },
      }),
      providesTags: ['BaoCao'],
    }),

    // ── SCR053 — tệp báo cáo đã xuất ──────────────────────────────────────────
    danhSachTepBaoCao: build.query<Page<TepBaoCao>, { trang?: number; sapXep?: string }>({
      query: (bo) => ({
        url: '/api/v1/reports/exports',
        params: { sort: bo.sapXep, page: bo.trang ?? 0, size: 10 },
      }),
      providesTags: ['BaoCao'],
    }),

    yeuCauXuatBaoCao: build.mutation<
      TepBaoCao,
      { reportType: LoaiBaoCao; format: 'CSV' | 'XLSX' | 'PDF'; params?: Record<string, unknown> }
    >({
      query: (than) => ({ url: '/api/v1/reports/exports', method: 'POST', body: than }),
      invalidatesTags: ['BaoCao'],
    }),
  }),
})

export const {
  useTongQuanQuery,
  useHoiThoaiTheoNgayQuery,
  usePheuChuyenDoiQuery,
  useThongKeChuDeQuery,
  useDanhSachTepBaoCaoQuery,
  useYeuCauXuatBaoCaoMutation,
} = analyticsApi
