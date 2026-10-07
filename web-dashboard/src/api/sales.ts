import { apiSlice } from '@/api/apiSlice'
import type { Page } from '@/types/api'
import type {
  ChuyenDoiLeadResult,
  Deal,
  DealChiTiet,
  DiemLead,
  HoatDong,
  Lead,
  LeadChiTiet,
  LoaiHoatDong,
  LyDoLoaiLead,
  LyDoThuaDeal,
  MucDo,
  NguonLead,
  Pheu,
  TrangThaiDeal,
  TrangThaiLead,
  TrangThaiNhacViec,
} from '@/types/schema'

/** Bán hàng — SCR041–SCR047. */

export interface BoLocLead {
  tuKhoa?: string
  trangThai?: TrangThaiLead
  nguon?: NguonLead
  chuSoHuu?: string
  diemToiThieu?: number
  trang?: number
  sapXep?: string
}

export interface TaoLead {
  contactId: string
  /** Nút "Tạo lead" trong Hộp thư gửi kèm hội thoại đang mở. */
  sourceConversationId?: string | null
  interestedProduct?: string | null
  budgetMin?: number | null
  budgetMax?: number | null
  urgency?: MucDo | null
  ownerUserId?: string | null
}

/** PATCH — trường không gửi thì giữ nguyên, gửi `null` là xoá giá trị. */
export interface CapNhatLead {
  status?: TrangThaiLead
  interestedProduct?: string | null
  budgetMin?: number | null
  budgetMax?: number | null
  urgency?: MucDo | null
  ownerUserId?: string | null
  disqualifyReason?: LyDoLoaiLead | null
}

export interface CapNhatDeal {
  title?: string
  amount?: number | null
  expectedCloseDate?: string | null
  ownerUserId?: string | null
}

export interface LuuDeal {
  contactId: string
  leadId?: string | null
  pipelineId: string
  stageId: string
  title: string
  amount?: number | null
  currency?: string
  expectedCloseDate?: string | null
  ownerUserId?: string | null
}

const CA_LEAD = { type: 'Lead' as const, id: 'DANH-SACH' }
const CA_DEAL = { type: 'Deal' as const, id: 'DANH-SACH' }

export const salesApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    // ── SCR041 · SCR042 · SCR043 — cơ hội tiềm năng ───────────────────────────
    danhSachLead: build.query<Page<Lead>, BoLocLead>({
      query: (bo) => ({
        url: '/api/v1/leads',
        params: {
          q: bo.tuKhoa || undefined,
          status: bo.trangThai,
          source: bo.nguon,
          ownerUserId: bo.chuSoHuu,
          minScore: bo.diemToiThieu,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: (kq) =>
        kq ? [...kq.items.map(({ id }) => ({ type: 'Lead' as const, id })), CA_LEAD] : [CA_LEAD],
    }),

    chiTietLead: build.query<LeadChiTiet, string>({
      query: (id) => ({ url: `/api/v1/leads/${id}` }),
      providesTags: (_kq, _loi, id) => [{ type: 'Lead', id }],
    }),

    taoLead: build.mutation<Lead, TaoLead>({
      query: (than) => ({ url: '/api/v1/leads', method: 'POST', body: than }),
      invalidatesTags: [CA_LEAD],
    }),

    capNhatLead: build.mutation<LeadChiTiet, { id: string; than: CapNhatLead }>({
      query: ({ id, than }) => ({ url: `/api/v1/leads/${id}`, method: 'PATCH', body: than }),
      invalidatesTags: (_kq, _loi, { id }) => [{ type: 'Lead', id }, CA_LEAD],
    }),

    /** UC032 bước 6 — lịch sử điểm, mới nhất trước. */
    lichSuDiemLead: build.query<DiemLead[], string>({
      query: (id) => ({ url: `/api/v1/leads/${id}/scores` }),
      providesTags: (_kq, _loi, id) => [{ type: 'Lead', id }],
    }),

    /**
     * UC033 — chuyển lead thành deal. Bỏ trống phễu/giai đoạn thì máy chủ đặt vào giai đoạn mở đầu
     * tiên của phễu mặc định.
     */
    chuyenLeadThanhDeal: build.mutation<
      ChuyenDoiLeadResult,
      { id: string; title?: string | null; amount?: number | null; expectedCloseDate?: string | null }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/leads/${id}/convert`,
        method: 'POST',
        body: than,
      }),
      invalidatesTags: (_kq, _loi, { id }) => [{ type: 'Lead', id }, CA_LEAD, CA_DEAL, 'GiaiDoanDeal'],
    }),

    // ── SCR044 · SCR045 · SCR046 — cơ hội bán hàng ────────────────────────────
    danhSachPheu: build.query<Pheu[], void>({
      query: () => ({ url: '/api/v1/pipelines' }),
      providesTags: ['GiaiDoanDeal'],
    }),

    /**
     * Kanban lấy **toàn bộ** deal đang mở của một phễu trong một lời gọi, không phân trang theo
     * cột: bảng Kanban phải hiện đủ để kéo thả có nghĩa, và một SME hiếm khi có quá vài trăm
     * cơ hội đang mở. `size` lớn là chủ ý, không phải quên.
     */
    danhSachDeal: build.query<
      Page<Deal>,
      { pheuId?: string; giaiDoanId?: string; trangThai?: TrangThaiDeal; chuSoHuu?: string }
    >({
      query: (bo) => ({
        url: '/api/v1/deals',
        params: {
          pipelineId: bo.pheuId,
          stageId: bo.giaiDoanId,
          // Không mặc định OPEN: bảng phễu cần cả cột Thắng/Thua
          status: bo.trangThai,
          ownerUserId: bo.chuSoHuu,
          size: 200,
        },
      }),
      providesTags: (kq) =>
        kq ? [...kq.items.map(({ id }) => ({ type: 'Deal' as const, id })), CA_DEAL] : [CA_DEAL],
    }),

    chiTietDeal: build.query<DealChiTiet, string>({
      query: (id) => ({ url: `/api/v1/deals/${id}` }),
      providesTags: (_kq, _loi, id) => [{ type: 'Deal', id }],
    }),

    taoDeal: build.mutation<Deal, LuuDeal>({
      query: (than) => ({ url: '/api/v1/deals', method: 'POST', body: than }),
      invalidatesTags: [CA_DEAL, 'GiaiDoanDeal'],
    }),

    /** PATCH — trường không gửi thì giữ nguyên, gửi `null` là xoá. */
    capNhatDeal: build.mutation<DealChiTiet, { id: string; than: CapNhatDeal }>({
      query: ({ id, than }) => ({ url: `/api/v1/deals/${id}`, method: 'PATCH', body: than }),
      invalidatesTags: (_kq, _loi, { id }) => [{ type: 'Deal', id }, CA_DEAL, 'GiaiDoanDeal'],
    }),

    keoDealSangGiaiDoan: build.mutation<
      DealChiTiet,
      { id: string; stageId: string; closeReason?: LyDoThuaDeal | null }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/deals/${id}/stage`,
        method: 'POST',
        body: than,
      }),
      // Kéo một thẻ làm đổi cả tổng giá trị của hai cột — nhãn giai đoạn phải nạp lại theo
      invalidatesTags: (_kq, _loi, { id }) => [{ type: 'Deal', id }, CA_DEAL, 'GiaiDoanDeal'],
    }),

    // ── SCR047 — hoạt động chăm sóc ───────────────────────────────────────────
    danhSachHoatDong: build.query<
      Page<HoatDong>,
      {
        khachHangId?: string
        leadId?: string
        dealId?: string
        loai?: LoaiHoatDong
        nhacViec?: TrangThaiNhacViec
        trang?: number
        sapXep?: string
      }
    >({
      query: (bo) => ({
        url: '/api/v1/activities',
        params: {
          contactId: bo.khachHangId,
          leadId: bo.leadId,
          dealId: bo.dealId,
          type: bo.loai,
          remindStatus: bo.nhacViec,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: (kq) =>
        kq
          ? [
              ...kq.items.map(({ id }) => ({ type: 'HoatDong' as const, id })),
              { type: 'HoatDong' as const, id: 'DANH-SACH' },
            ]
          : [{ type: 'HoatDong' as const, id: 'DANH-SACH' }],
    }),

    ghiNhanHoatDong: build.mutation<
      HoatDong,
      {
        contactId: string
        leadId?: string | null
        dealId?: string | null
        type: LoaiHoatDong
        subject?: string | null
        content?: string | null
      }
    >({
      query: (than) => ({ url: '/api/v1/activities', method: 'POST', body: than }),
      invalidatesTags: ['HoatDong', 'Lead', 'Deal'],
    }),
  }),
})

export const {
  useDanhSachLeadQuery,
  useChiTietLeadQuery,
  useTaoLeadMutation,
  useCapNhatLeadMutation,
  useLichSuDiemLeadQuery,
  useChuyenLeadThanhDealMutation,
  useDanhSachPheuQuery,
  useDanhSachDealQuery,
  useChiTietDealQuery,
  useTaoDealMutation,
  useCapNhatDealMutation,
  useKeoDealSangGiaiDoanMutation,
  useDanhSachHoatDongQuery,
  useGhiNhanHoatDongMutation,
} = salesApi
