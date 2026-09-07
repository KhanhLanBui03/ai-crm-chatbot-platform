import { apiSlice } from '@/api/apiSlice'
import type { Page } from '@/types/api'
import type {
  BanGhiKiemToan,
  MucNghiemTrongKiemToan,
  MucXoa,
  TrangThaiYeuCauXoa,
  YeuCauXoa,
  YeuCauXoaChiTiet,
} from '@/types/schema'

/** Kiểm toán và quyền xoá dữ liệu cá nhân — SCR054–SCR058. Nghị định 13/2023/NĐ-CP. */

export interface BoLocKiemToan {
  tuKhoa?: string
  hanhDong?: string
  chuTheId?: string
  mucNghiemTrong?: MucNghiemTrongKiemToan
  loaiThucThe?: string
  tuNgay?: string
  denNgay?: string
  trang?: number
}

const CA_YEU_CAU_XOA = { type: 'NhatKyKiemToan' as const, id: 'YEU-CAU-XOA' }

export const auditApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    // ── SCR054 — nhật ký kiểm toán ────────────────────────────────────────────
    danhSachKiemToan: build.query<Page<BanGhiKiemToan>, BoLocKiemToan>({
      query: (bo) => ({
        url: '/api/v1/audit-logs',
        params: {
          q: bo.tuKhoa || undefined,
          action: bo.hanhDong,
          actorId: bo.chuTheId,
          severity: bo.mucNghiemTrong,
          entityType: bo.loaiThucThe,
          from: bo.tuNgay,
          to: bo.denNgay,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: ['NhatKyKiemToan'],
    }),

    /**
     * Bỏ che một bản ghi có dữ liệu cá nhân.
     *
     * **Không** `invalidatesTags`, và đây là chủ ý: chính lần xem này sinh thêm một dòng nhật ký
     * mới, nên làm mới ngay sẽ chèn một dòng vào đầu danh sách và đẩy bản ghi người dùng đang đọc
     * trôi xuống — giữa lúc họ đang đọc nó. Nội dung đã bỏ che nằm sẵn trong phản hồi nên hộp
     * thoại không cần danh sách để hiển thị.
     *
     * Đổi lại, màn hình **phải** tự gọi `refetch` khi đóng hộp thoại. Bỏ bước đó thì danh sách
     * thiếu mất chính dòng `AUDIT_LOG_REVEALED` vừa sinh ra, và người vào kiểm tra "lần xem của
     * tôi có được ghi không" sẽ kết luận là không.
     */
    xemDayDuBanGhi: build.mutation<BanGhiKiemToan, { id: number; reason: string }>({
      query: ({ id, reason }) => ({
        url: `/api/v1/audit-logs/${id}/reveal`,
        method: 'POST',
        body: { reason },
      }),
    }),

    // ── SCR056 — yêu cầu xoá dữ liệu cá nhân ──────────────────────────────────
    danhSachYeuCauXoa: build.query<
      Page<YeuCauXoa>,
      { trangThai?: TrangThaiYeuCauXoa; trang?: number }
    >({
      query: (bo) => ({
        url: '/api/v1/erasure-requests',
        params: { status: bo.trangThai, page: bo.trang ?? 0, size: 10 },
      }),
      providesTags: [CA_YEU_CAU_XOA],
    }),

    /**
     * SCR055 — xem trước phạm vi ảnh hưởng.
     *
     * Đường dẫn cố định `/preview`, **không** phải một id. Handler mock phải đăng ký nó **trước**
     * `/erasure-requests/:id`, nếu không `preview` bị khớp thành một id.
     */
    xemTruocPhamViXoa: build.query<MucXoa[], string>({
      query: (khachHangId) => ({
        url: '/api/v1/erasure-requests/preview',
        params: { contactId: khachHangId },
      }),
    }),

    // ── SCR057 — tiến độ xoá theo từng bảng ───────────────────────────────────
    chiTietYeuCauXoa: build.query<YeuCauXoaChiTiet, string>({
      query: (id) => ({ url: `/api/v1/erasure-requests/${id}` }),
      providesTags: (_kq, _loi, id) => [{ type: 'NhatKyKiemToan', id }],
    }),

    // ── SCR058 — thực thi yêu cầu xoá ─────────────────────────────────────────
    /** Thao tác **không đảo ngược được**. Làm mới cả nhật ký kiểm toán vì nó sinh ra `ERASURE_EXECUTED`. */
    thucThiYeuCauXoa: build.mutation<YeuCauXoaChiTiet, string>({
      query: (id) => ({ url: `/api/v1/erasure-requests/${id}/execute`, method: 'POST' }),
      invalidatesTags: (_kq, _loi, id) => [
        { type: 'NhatKyKiemToan', id },
        CA_YEU_CAU_XOA,
        'NhatKyKiemToan',
        'KhachHang',
      ],
    }),
  }),
})

export const {
  useDanhSachKiemToanQuery,
  useXemDayDuBanGhiMutation,
  useDanhSachYeuCauXoaQuery,
  useXemTruocPhamViXoaQuery,
  useChiTietYeuCauXoaQuery,
  useThucThiYeuCauXoaMutation,
} = auditApi
