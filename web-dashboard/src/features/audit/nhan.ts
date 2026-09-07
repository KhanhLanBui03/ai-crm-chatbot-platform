import type { SacThai } from '@/components/ui/status-chip'
import type {
  LoaiChuThe,
  MucNghiemTrongKiemToan,
  ThaoTacXoa,
  TrangThaiYeuCauXoa,
} from '@/types/schema'

/** Nhãn tiếng Việt của nhóm kiểm toán và quyền xoá dữ liệu cá nhân. */

export const NHAN_MUC_NGHIEM_TRONG: Record<
  MucNghiemTrongKiemToan,
  { nhan: string; sacThai: SacThai }
> = {
  INFO: { nhan: 'Thông tin', sacThai: 'neutral' },
  WARNING: { nhan: 'Cần chú ý', sacThai: 'warning' },
  CRITICAL: { nhan: 'Nghiêm trọng', sacThai: 'destructive' },
}

export const NHAN_CHU_THE: Record<LoaiChuThe, string> = {
  USER: 'Người dùng',
  AI_AGENT: 'Tác tử AI',
  SYSTEM: 'Hệ thống',
  PLATFORM_ADMIN: 'Quản trị nền tảng',
}

/**
 * Hành động ghi vào nhật ký. `Record` **không** đầy đủ được vì `action` là chuỗi tự do ở giao ước
 * — máy chủ thêm hành động mới mà không cần đổi lược đồ. Chỗ nào tra không thấy thì hiện nguyên
 * mã, đọc vẫn ra nghĩa, hơn là hiện một dòng trống.
 */
export const NHAN_HANH_DONG: Record<string, string> = {
  LOGIN_SUCCESS: 'Đăng nhập thành công',
  LOGIN_FAILED: 'Đăng nhập thất bại',
  ROLE_CHANGED: 'Đổi vai trò người dùng',
  CONTACT_MERGED: 'Hợp nhất hồ sơ khách hàng',
  CONSENT_WITHDRAWN: 'Khách rút đồng ý xử lý dữ liệu',
  ERASURE_EXECUTED: 'Thực thi xoá dữ liệu cá nhân',
  EXPORT_REQUESTED: 'Yêu cầu xuất báo cáo',
  RETENTION_PURGE: 'Dọn dữ liệu quá hạn lưu trữ',
  PLAN_CHANGED: 'Đổi gói dịch vụ',
  MCP_SERVER_ADDED: 'Thêm máy chủ MCP',
  TOOL_CALL_BLOCKED: 'Chặn lời gọi công cụ',
  DOCUMENT_DELETED: 'Xoá tài liệu tri thức',
  AUDIT_LOG_REVEALED: 'Xem đầy đủ bản ghi kiểm toán',
}

export const NHAN_TRANG_THAI_XOA: Record<
  TrangThaiYeuCauXoa,
  { nhan: string; sacThai: SacThai }
> = {
  PENDING: { nhan: 'Chờ thực thi', sacThai: 'warning' },
  IN_PROGRESS: { nhan: 'Đang xoá', sacThai: 'info' },
  COMPLETED: { nhan: 'Đã hoàn tất', sacThai: 'success' },
  PARTIALLY_FAILED: { nhan: 'Hỏng giữa chừng', sacThai: 'destructive' },
}

/**
 * Ba thao tác xoá **không thay thế được cho nhau**, nên nhãn phải nói ra hệ quả:
 * xoá sạch cả `KEEP_AGGREGATE` là phá luôn báo cáo doanh thu của những kỳ đã chốt sổ.
 */
export const NHAN_THAO_TAC_XOA: Record<
  ThaoTacXoa,
  { nhan: string; moTa: string; sacThai: SacThai }
> = {
  DELETE: {
    nhan: 'Xoá hẳn',
    moTa: 'Dòng dữ liệu bị xoá khỏi bảng, không khôi phục được.',
    sacThai: 'destructive',
  },
  ANONYMIZE: {
    nhan: 'Ẩn danh hoá',
    moTa: 'Giữ dòng nhưng bỏ mọi trường quy về được cá nhân — quan hệ nghiệp vụ vẫn nguyên vẹn.',
    sacThai: 'warning',
  },
  KEEP_AGGREGATE: {
    nhan: 'Giữ số tổng hợp',
    moTa: 'Không đụng tới: đây là số liệu đã tổng hợp, không còn quy về một cá nhân nào.',
    sacThai: 'neutral',
  },
}

export const NHAN_TRANG_THAI_MUC: Record<string, { nhan: string; sacThai: SacThai }> = {
  PENDING: { nhan: 'Chưa chạy', sacThai: 'neutral' },
  DONE: { nhan: 'Xong', sacThai: 'success' },
  FAILED: { nhan: 'Hỏng', sacThai: 'destructive' },
}
