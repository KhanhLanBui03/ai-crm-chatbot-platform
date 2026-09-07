import { apiSlice } from '@/api/apiSlice'
import type { Page } from '@/types/api'
import type {
  GhiChu,
  KenhChinh,
  KhachHang,
  KhachHangChiTiet,
  The,
  TrangThaiKhachHang,
} from '@/types/schema'

export interface BoLocKhachHang {
  tuKhoa?: string
  trangThai?: TrangThaiKhachHang
  /** Đồng ý xử lý dữ liệu cá nhân (Nghị định 13). */
  daDongY?: boolean
  trang?: number
  sapXep?: string
}

export interface LuuKhachHang {
  fullName?: string | null
  phone?: string | null
  email?: string | null
  primaryChannel?: KenhChinh
  consentGranted?: boolean
  consentSource?: 'WIDGET' | 'ZALO' | 'FACEBOOK' | 'AGENT_MANUAL'
}

export interface KetQuaTaoKhachHang {
  contact: KhachHangChiTiet
  /** Trùng số điện thoại hoặc thư — chỉ **cảnh báo**, không chặn. */
  duplicateCandidates: KhachHang[]
}

const CA_DANH_SACH = { type: 'KhachHang' as const, id: 'DANH-SACH' }

export const contactsApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    danhSachKhachHang: build.query<Page<KhachHang>, BoLocKhachHang>({
      query: (bo) => ({
        url: '/api/v1/contacts',
        params: {
          q: bo.tuKhoa || undefined,
          status: bo.trangThai,
          hasConsent: bo.daDongY,
          sort: bo.sapXep,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: (kq) =>
        kq
          ? [...kq.items.map(({ id }) => ({ type: 'KhachHang' as const, id })), CA_DANH_SACH]
          : [CA_DANH_SACH],
    }),

    // ── SCR024 — hồ sơ khách hàng ─────────────────────────────────────────────
    chiTietKhachHang: build.query<KhachHangChiTiet, string>({
      query: (id) => ({ url: `/api/v1/contacts/${id}` }),
      providesTags: (_kq, _loi, id) => [{ type: 'KhachHang', id }],
    }),

    suaKhachHang: build.mutation<KhachHangChiTiet, { id: string; than: LuuKhachHang }>({
      query: ({ id, than }) => ({ url: `/api/v1/contacts/${id}`, method: 'PATCH', body: than }),
      invalidatesTags: (_kq, _loi, { id }) => [{ type: 'KhachHang', id }, CA_DANH_SACH],
    }),

    // ── SCR027 — tạo khách hàng thủ công ──────────────────────────────────────
    taoKhachHang: build.mutation<KetQuaTaoKhachHang, LuuKhachHang>({
      query: (than) => ({ url: '/api/v1/contacts', method: 'POST', body: than }),
      invalidatesTags: [CA_DANH_SACH],
    }),

    // ── SCR025 — hợp nhất hai hồ sơ ───────────────────────────────────────────
    hopNhatKhachHang: build.mutation<
      KhachHangChiTiet,
      { id: string; mergedContactId: string; fieldChoices?: Record<string, string> }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/contacts/${id}/merge`,
        method: 'POST',
        body: than,
      }),
      // Hợp nhất đụng cả hai bản ghi lẫn mọi hội thoại trỏ về chúng
      invalidatesTags: ['KhachHang', 'HoiThoai'],
    }),

    // ── SCR028 — ghi chú nội bộ ───────────────────────────────────────────────
    ghiChuKhachHang: build.query<GhiChu[], string>({
      query: (id) => ({ url: `/api/v1/contacts/${id}/notes` }),
      providesTags: (_kq, _loi, id) => [{ type: 'KhachHang', id: `ghi-chu-${id}` }],
    }),

    themGhiChu: build.mutation<
      GhiChu,
      { contactId: string; content: string; conversationId?: string | null }
    >({
      query: ({ contactId, ...than }) => ({
        url: `/api/v1/contacts/${contactId}/notes`,
        method: 'POST',
        body: than,
      }),
      invalidatesTags: (_kq, _loi, { contactId }) => [
        { type: 'KhachHang', id: `ghi-chu-${contactId}` },
      ],
    }),

    danhSachThe: build.query<The[], void>({
      query: () => ({ url: '/api/v1/tags' }),
      providesTags: ['KhachHang'],
    }),
  }),
})

export const {
  useDanhSachKhachHangQuery,
  useChiTietKhachHangQuery,
  useSuaKhachHangMutation,
  useTaoKhachHangMutation,
  useHopNhatKhachHangMutation,
  useGhiChuKhachHangQuery,
  useThemGhiChuMutation,
  useDanhSachTheQuery,
} = contactsApi
