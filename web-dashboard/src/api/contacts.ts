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

    // ── SCR028 — sửa / ghim / xoá ghi chú (UC017, thêm 06/10) ─────────────────
    suaGhiChu: build.mutation<
      GhiChu,
      { contactId: string; noteId: string; content?: string; isPinned?: boolean }
    >({
      query: ({ contactId, noteId, ...than }) => ({
        url: `/api/v1/contacts/${contactId}/notes/${noteId}`,
        method: 'PATCH',
        body: than,
      }),
      invalidatesTags: (_kq, _loi, { contactId }) => [
        { type: 'KhachHang', id: `ghi-chu-${contactId}` },
      ],
    }),

    xoaGhiChu: build.mutation<null, { contactId: string; noteId: string }>({
      query: ({ contactId, noteId }) => ({
        url: `/api/v1/contacts/${contactId}/notes/${noteId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_kq, _loi, { contactId }) => [
        { type: 'KhachHang', id: `ghi-chu-${contactId}` },
      ],
    }),

    danhSachThe: build.query<The[], void>({
      query: () => ({ url: '/api/v1/tags' }),
      providesTags: [{ type: 'KhachHang', id: 'DANH-SACH-THE' }],
    }),

    // Trùng tên (khác hoa thường / khác dấu) máy chủ trả THẺ CŨ — giao diện gắn luôn thẻ đó.
    taoThe: build.mutation<The, { name: string }>({
      query: (than) => ({ url: '/api/v1/tags', method: 'POST', body: than }),
      invalidatesTags: [{ type: 'KhachHang', id: 'DANH-SACH-THE' }],
    }),

    ganThe: build.mutation<null, { contactId: string; tagId: string }>({
      query: ({ contactId, tagId }) => ({
        url: `/api/v1/contacts/${contactId}/tags/${tagId}`,
        method: 'PUT',
      }),
      // Hồ sơ (thẻ đang gắn), danh sách khách (cột Thẻ), số lượt dùng của thẻ
      invalidatesTags: (_kq, _loi, { contactId }) => [
        { type: 'KhachHang', id: contactId },
        CA_DANH_SACH,
        { type: 'KhachHang', id: 'DANH-SACH-THE' },
      ],
    }),

    goThe: build.mutation<null, { contactId: string; tagId: string }>({
      query: ({ contactId, tagId }) => ({
        url: `/api/v1/contacts/${contactId}/tags/${tagId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_kq, _loi, { contactId }) => [
        { type: 'KhachHang', id: contactId },
        CA_DANH_SACH,
        { type: 'KhachHang', id: 'DANH-SACH-THE' },
      ],
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
  useSuaGhiChuMutation,
  useXoaGhiChuMutation,
  useDanhSachTheQuery,
  useTaoTheMutation,
  useGanTheMutation,
  useGoTheMutation,
} = contactsApi
