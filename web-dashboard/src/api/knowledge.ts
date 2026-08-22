import { apiSlice } from '@/api/apiSlice'
import type { Page } from '@/types/api'
import type {
  CongViecNap,
  DoanTaiLieu,
  KetQuaTruyHoi,
  KhoangTrongTriThuc,
  LoaiKhoangTrong,
  LoaiNguonTaiLieu,
  TaiLieu,
  TaiLieuChiTiet,
  TrangThaiCongViecNap,
  TrangThaiTaiLieu,
} from '@/types/schema'

/** Kho tri thức — SCR029–SCR034. */

export interface BoLocTaiLieu {
  tuKhoa?: string
  trangThai?: TrangThaiTaiLieu
  loaiNguon?: LoaiNguonTaiLieu
  trang?: number
}

const CA_TAI_LIEU = { type: 'TaiLieu' as const, id: 'DANH-SACH' }

export const knowledgeApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    // ── SCR030 — danh sách tài liệu ───────────────────────────────────────────
    danhSachTaiLieu: build.query<Page<TaiLieu>, BoLocTaiLieu>({
      query: (bo) => ({
        url: '/api/v1/documents',
        params: {
          q: bo.tuKhoa || undefined,
          status: bo.trangThai,
          sourceType: bo.loaiNguon,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: (kq) =>
        kq
          ? [...kq.items.map(({ id }) => ({ type: 'TaiLieu' as const, id })), CA_TAI_LIEU]
          : [CA_TAI_LIEU],
    }),

    chiTietTaiLieu: build.query<TaiLieuChiTiet, string>({
      query: (id) => ({ url: `/api/v1/documents/${id}` }),
      providesTags: (_kq, _loi, id) => [{ type: 'TaiLieu', id }],
    }),

    /**
     * SCR029 — tải lên tài liệu.
     *
     * Thân là `FormData` chứ không phải JSON: giao ước khai `multipart/form-data`, và tệp PDF vài
     * MB mã hoá base64 nhét vào JSON thì phồng thêm một phần ba dung lượng cùng với việc phải giữ
     * trọn tệp trong bộ nhớ hai lần. axios tự đặt `Content-Type` kèm `boundary` khi thấy
     * `FormData` — **đừng** tự đặt header đó, đặt tay là mất `boundary` và máy chủ không tách được
     * các phần.
     */
    taiLenTaiLieu: build.mutation<
      TaiLieu,
      { tep: File; title: string; description?: string | null; language?: string }
    >({
      query: ({ tep, title, description, language }) => {
        const than = new FormData()
        than.append('file', tep)
        than.append('title', title)
        if (description) than.append('description', description)
        than.append('language', language ?? 'vi')
        return { url: '/api/v1/documents', method: 'POST', body: than }
      },
      invalidatesTags: [CA_TAI_LIEU, 'ChunkTriThuc'],
    }),

    xoaTaiLieu: build.mutation<null, string>({
      query: (id) => ({ url: `/api/v1/documents/${id}`, method: 'DELETE' }),
      invalidatesTags: [CA_TAI_LIEU],
    }),

    napLaiTaiLieu: build.mutation<CongViecNap, string>({
      query: (id) => ({ url: `/api/v1/documents/${id}/reindex`, method: 'POST' }),
      invalidatesTags: (_kq, _loi, id) => [{ type: 'TaiLieu', id }, CA_TAI_LIEU],
    }),

    // ── SCR032 — các đoạn của một tài liệu ────────────────────────────────────
    danhSachDoan: build.query<Page<DoanTaiLieu>, { taiLieuId: string; trang?: number }>({
      query: ({ taiLieuId, trang }) => ({
        url: `/api/v1/documents/${taiLieuId}/chunks`,
        params: { page: trang ?? 0, size: 10 },
      }),
      providesTags: (_kq, _loi, { taiLieuId }) => [{ type: 'ChunkTriThuc', id: taiLieuId }],
    }),

    /**
     * SCR031 — tìm thử trong kho tri thức.
     *
     * `providesTags` bỏ trống một cách cố ý: đây là một phép **thử**, không phải một khung nhìn
     * dữ liệu. Gắn nhãn `TaiLieu` vào thì mỗi lần tải lên tài liệu mới sẽ chạy lại truy hồi của
     * truy vấn cũ trong nền — tốn một lượt nhúng câu hỏi cho kết quả không ai đang nhìn.
     */
    timTriThuc: build.query<KetQuaTruyHoi[], { tuKhoa: string; topK?: number }>({
      query: ({ tuKhoa, topK }) => ({
        url: '/api/v1/knowledge/search',
        params: { q: tuKhoa, topK: topK ?? 5 },
      }),
    }),

    // ── SCR033 — tiến độ nạp tài liệu ─────────────────────────────────────────
    danhSachCongViecNap: build.query<
      Page<CongViecNap>,
      { trangThai?: TrangThaiCongViecNap; trang?: number; co?: number }
    >({
      query: (bo) => ({
        url: '/api/v1/ingestion-jobs',
        params: { state: bo.trangThai, page: bo.trang ?? 0, size: bo.co ?? 10 },
      }),
      providesTags: ['TaiLieu'],
    }),

    // ── SCR034 — khoảng trống tri thức ────────────────────────────────────────
    danhSachKhoangTrong: build.query<
      Page<KhoangTrongTriThuc>,
      { tuKhoa?: string; trangThai?: string; loai?: LoaiKhoangTrong; trang?: number }
    >({
      query: (bo) => ({
        url: '/api/v1/knowledge-gaps',
        params: {
          q: bo.tuKhoa || undefined,
          status: bo.trangThai,
          gapType: bo.loai,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: ['ChunkTriThuc'],
    }),

    danhDauKhoangTrong: build.mutation<
      KhoangTrongTriThuc,
      { id: string; status: 'RESOLVED' | 'IGNORED'; resolvedDocumentId?: string | null }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/knowledge-gaps/${id}`,
        method: 'PATCH',
        body: than,
      }),
      invalidatesTags: ['ChunkTriThuc'],
    }),
  }),
})

export const {
  useDanhSachTaiLieuQuery,
  useChiTietTaiLieuQuery,
  useTaiLenTaiLieuMutation,
  useXoaTaiLieuMutation,
  useNapLaiTaiLieuMutation,
  useDanhSachDoanQuery,
  useLazyTimTriThucQuery,
  useDanhSachCongViecNapQuery,
  useDanhSachKhoangTrongQuery,
  useDanhDauKhoangTrongMutation,
} = knowledgeApi
