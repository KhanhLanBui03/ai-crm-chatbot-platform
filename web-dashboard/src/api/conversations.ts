import { apiSlice } from '@/api/apiSlice'
import { ketNoiThoiGianThuc } from '@/api/realtime/ketNoi'
import type { Page } from '@/types/api'
import type {
  HoiThoaiChiTiet,
  HoiThoaiTomTat,
  LoaiKenh,
  LyDoChuyenGiao,
  MauCauTraLoi,
  NguCanhHoiThoai,
  QuyTacPhanCong,
  SuKienChuyenGiao,
  TrangThaiHoiThoai,
} from '@/types/schema'

export interface BoLocHoiThoai {
  /** `mine` = của tôi · `unassigned` = chờ tôi nhận · để trống là tất cả. */
  phamVi?: 'all' | 'mine' | 'unassigned'
  trangThai?: TrangThaiHoiThoai[]
  tuKhoa?: string
  trang?: number
}

/** Nhãn đại diện cho "cả danh sách", để một tin nhắn mới làm mọi bộ lọc nạp lại. */
const CA_DANH_SACH = { type: 'HoiThoai' as const, id: 'DANH-SACH' }

/**
 * Một khung `CONVERSATION_UPDATED` đến sẽ chạy qua **mọi** mục cache của `danhSachHoiThoai` —
 * hộp thư mở ba tab là ba mục. Khi hội thoại đó không nằm trong mục nào (nó vừa đổi trạng thái
 * nên bây giờ mới khớp bộ lọc), cách duy nhất đúng là hỏi lại máy chủ: chỉ máy chủ biết bộ lọc
 * có khớp không.
 *
 * Tập này giữ những `eventId` đã kích hoạt việc hỏi lại, để ba mục cache không sinh ra ba lần
 * nạp lại cho cùng một sự kiện.
 */
const daNapLaiVi = new Set<string>()

function danhDauDaNapLai(eventId: string): boolean {
  if (daNapLaiVi.has(eventId)) return false
  daNapLaiVi.add(eventId)
  if (daNapLaiVi.size > 200) {
    for (const cu of [...daNapLaiVi].slice(0, 100)) daNapLaiVi.delete(cu)
  }
  return true
}

/** Khoá sắp xếp mặc định của hộp thư — giống hệt `ORDER BY last_message_at DESC` của máy chủ. */
function sapTheoTinMoiNhat(ds: HoiThoaiTomTat[]) {
  ds.sort((a, b) => b.lastMessageAt.localeCompare(a.lastMessageAt))
}

export const conversationsApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    danhSachHoiThoai: build.query<Page<HoiThoaiTomTat>, BoLocHoiThoai>({
      query: (bo) => ({
        url: '/api/v1/conversations',
        params: {
          scope: bo.phamVi ?? 'all',
          status: bo.trangThai?.join(','),
          q: bo.tuKhoa || undefined,
          page: bo.trang ?? 0,
          size: 25,
        },
      }),
      providesTags: (ketQua) =>
        ketQua
          ? [...ketQua.items.map(({ id }) => ({ type: 'HoiThoai' as const, id })), CA_DANH_SACH]
          : [CA_DANH_SACH],

      /**
       * Cập nhật trực tiếp từ WebSocket. `updateCachedData` vá thẳng vào cache nên danh sách
       * nhích lên mà **không** tốn một request nào — khác hẳn với việc gọi `refetch()` mỗi khi
       * có tin nhắn, thứ sẽ biến một hộp thư bận thành một vòng lặp nạp lại.
       */
      async onCacheEntryAdded(_bo, { updateCachedData, cacheDataLoaded, cacheEntryRemoved, dispatch }) {
        const goBo: Array<() => void> = []
        try {
          // Chỉ vá được khi đã có dữ liệu để vá. Ném lỗi nếu truy vấn hỏng — nhánh `finally`
          // vẫn dọn, nên không có hàm nghe nào bị bỏ lại.
          await cacheDataLoaded

          const apDung = (hoiThoai: HoiThoaiTomTat, eventId: string) => {
            let coTrongMuc = false
            updateCachedData((trang) => {
              const i = trang.items.findIndex((c) => c.id === hoiThoai.id)
              if (i === -1) return
              coTrongMuc = true
              // Thay nguyên dòng chứ không trộn từng trường: `unreadCount` và
              // `lastMessagePreview` là cột máy chủ tính sẵn khi ghi, trình duyệt không suy
              // ra đúng được (nó không biết nhân viên nào đã đọc tới đâu).
              trang.items[i] = hoiThoai
              sapTheoTinMoiNhat(trang.items)
            })
            if (!coTrongMuc && danhDauDaNapLai(eventId)) {
              dispatch(apiSlice.util.invalidateTags([CA_DANH_SACH]))
            }
          }

          goBo.push(
            ketNoiThoiGianThuc.dangKy('CONVERSATION_UPDATED', (k) =>
              apDung(k.conversation, k.eventId),
            ),
            ketNoiThoiGianThuc.dangKy('HANDOFF_REQUESTED', (k) =>
              apDung(k.conversation, k.eventId),
            ),
          )
          await cacheEntryRemoved
        } catch {
          // `cacheDataLoaded` bị từ chối khi mục cache biến mất trước lúc có dữ liệu
        } finally {
          for (const go of goBo) go()
        }
      },
    }),

    chiTietHoiThoai: build.query<HoiThoaiChiTiet, string>({
      query: (id) => ({ url: `/api/v1/conversations/${id}` }),
      providesTags: (_kq, _loi, id) => [{ type: 'HoiThoai', id }],

      async onCacheEntryAdded(id, { updateCachedData, cacheDataLoaded, cacheEntryRemoved }) {
        const goBo: Array<() => void> = []
        try {
          await cacheDataLoaded
          // Xin nhận tin nhắn của riêng hội thoại này. Đẩy mọi tin nhắn của mọi hội thoại
          // xuống mọi nhân viên là gửi thừa gần như toàn bộ — xem `dashboard-realtime.md`.
          goBo.push(ketNoiThoiGianThuc.theoDoi(id))
          goBo.push(
            ketNoiThoiGianThuc.dangKy('MESSAGE_CREATED', (k) => {
              if (k.conversationId !== id) return
              updateCachedData((chiTiet) => {
                // Máy chủ có thể phát lại khung cuối sau khi nối lại; lớp kết nối đã lọc theo
                // `eventId`, ở đây lọc thêm theo `message.id` cho chắc — một tin nhắn hiện hai
                // lần là lỗi người dùng nhìn thấy ngay.
                if (chiTiet.messages.some((tn) => tn.id === k.message.id)) return
                chiTiet.messages.push(k.message)
                chiTiet.messageCount = (chiTiet.messageCount ?? 0) + 1
                chiTiet.lastMessageAt = k.message.createdAt
              })
            }),
          )
          await cacheEntryRemoved
        } catch {
          // như trên
        } finally {
          for (const go of goBo) go()
        }
      },
    }),

    nguCanhHoiThoai: build.query<NguCanhHoiThoai, string>({
      query: (id) => ({ url: `/api/v1/conversations/${id}/context` }),
      providesTags: (_kq, _loi, id) => [{ type: 'HoiThoai', id: `ngu-canh-${id}` }],
    }),

    // ── SCR021 — phân công và chuyển giao ─────────────────────────────────────

    /** Bỏ trống `assigneeUserId` là tự nhận về mình. */
    phanCongHoiThoai: build.mutation<
      HoiThoaiTomTat,
      { id: string; assigneeUserId?: string | null; reason?: string | null }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/conversations/${id}/assign`,
        method: 'POST',
        body: than,
      }),
      invalidatesTags: (_kq, _loi, { id }) => [{ type: 'HoiThoai', id }, CA_DANH_SACH],
    }),

    /**
     * Chuyển giao giữa tác tử AI và người.
     *
     * `reason` là bắt buộc và không phải thủ tục giấy tờ: `handoff_events.reason` là nguồn của
     * chỉ số "tỉ lệ AI phải nhường người", mà chỉ số đó là thước đo chính của chất lượng tác tử
     * (SCR051). Cho phép bỏ trống là tự làm mù phần đo lường quan trọng nhất của đề tài.
     */
    chuyenGiaoHoiThoai: build.mutation<
      SuKienChuyenGiao,
      { id: string; direction: 'BOT_TO_AGENT' | 'AGENT_TO_BOT'; reason: LyDoChuyenGiao }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/conversations/${id}/handoff`,
        method: 'POST',
        body: than,
      }),
      invalidatesTags: (_kq, _loi, { id }) => [{ type: 'HoiThoai', id }, CA_DANH_SACH],
    }),

    doiTrangThaiHoiThoai: build.mutation<
      HoiThoaiTomTat,
      { id: string; status: TrangThaiHoiThoai; closedReason?: string | null }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/conversations/${id}/status`,
        method: 'POST',
        body: than,
      }),
      invalidatesTags: (_kq, _loi, { id }) => [{ type: 'HoiThoai', id }, CA_DANH_SACH],
    }),

    // ── SCR022 · SCR023 — quy tắc phân công tự động ───────────────────────────

    danhSachQuyTac: build.query<QuyTacPhanCong[], { apDungCho?: 'CONVERSATION' | 'LEAD' }>({
      query: (bo) => ({ url: '/api/v1/assignment-rules', params: { appliesTo: bo.apDungCho } }),
      providesTags: ['HoiThoai'],
    }),

    taoQuyTac: build.mutation<QuyTacPhanCong, LuuQuyTac>({
      query: (than) => ({ url: '/api/v1/assignment-rules', method: 'POST', body: than }),
      invalidatesTags: ['HoiThoai'],
    }),

    suaQuyTac: build.mutation<QuyTacPhanCong, { id: string; than: Partial<LuuQuyTac> }>({
      query: ({ id, than }) => ({
        url: `/api/v1/assignment-rules/${id}`,
        method: 'PATCH',
        body: than,
      }),
      invalidatesTags: ['HoiThoai'],
    }),

    xoaQuyTac: build.mutation<void, string>({
      query: (id) => ({ url: `/api/v1/assignment-rules/${id}`, method: 'DELETE' }),
      invalidatesTags: ['HoiThoai'],
    }),

    danhSachMauCauTraLoi: build.query<MauCauTraLoi[], void>({
      query: () => ({ url: '/api/v1/canned-responses' }),
      providesTags: ['HoiThoai'],
    }),
  }),
})

export interface LuuQuyTac {
  name: string
  appliesTo: 'CONVERSATION' | 'LEAD'
  strategy: 'LEAST_BUSY' | 'ROUND_ROBIN' | 'FIXED_USER'
  channelType?: LoaiKenh | null
  tagId?: string | null
  targetUserId?: string | null
  maxConcurrent?: number | null
  priority?: number
  isActive?: boolean
}

export const {
  useDanhSachHoiThoaiQuery,
  useChiTietHoiThoaiQuery,
  useNguCanhHoiThoaiQuery,
  usePhanCongHoiThoaiMutation,
  useChuyenGiaoHoiThoaiMutation,
  useDoiTrangThaiHoiThoaiMutation,
  useDanhSachQuyTacQuery,
  useTaoQuyTacMutation,
  useSuaQuyTacMutation,
  useXoaQuyTacMutation,
  useDanhSachMauCauTraLoiQuery,
} = conversationsApi
