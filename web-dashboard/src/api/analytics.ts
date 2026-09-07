import { apiSlice } from '@/api/apiSlice'
import type {
  BacPheu,
  DiemHoiThoaiNgay,
  LoaiBaoCao,
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

    // UC042 nhánh 4.2 — máy chủ sinh tệp đồng bộ và trả thẳng nội dung, không có
    // mã công việc để hỏi lại. Vì vậy đây là mutation trả Blob, không trả thực thể.
    yeuCauXuatBaoCao: build.mutation<
      Blob,
      {
        reportType: LoaiBaoCao
        format: 'CSV' | 'XLSX'
        params?: Record<string, unknown>
        confirmPersonalData?: boolean
      }
    >({
      query: (than) => ({
        url: '/api/v1/reports/exports',
        method: 'POST',
        body: than,
        responseHandler: (res: Response) => res.blob(),
      }),
    }),
  }),
})

export const {
  useTongQuanQuery,
  useHoiThoaiTheoNgayQuery,
  usePheuChuyenDoiQuery,
  useThongKeChuDeQuery,
  useYeuCauXuatBaoCaoMutation,
} = analyticsApi
