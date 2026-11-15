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
 * Hành động ghi vào nhật ký — đúng các mã java-core THẬT SỰ ghi (rà mọi lời gọi `AuditLogWriter`,
 * 07/11/2026). Danh sách này cũng là các lựa chọn của bộ lọc "Hành động": để mã không ai ghi ở đây
 * thì người dùng chọn xong chỉ thấy bảng rỗng và tưởng hệ thống không ghi.
 *
 * `Record` **không** đầy đủ được vì `action` là chuỗi tự do ở giao ước — máy chủ thêm hành động mới
 * mà không cần đổi lược đồ. Chỗ nào tra không thấy thì hiện nguyên mã, đọc vẫn ra nghĩa.
 * Thêm hành động mới ở java-core thì thêm nhãn ở đây.
 */
export const NHAN_HANH_DONG: Record<string, string> = {
  CONTACT_CREATED: 'Tạo hồ sơ khách hàng',
  CONTACT_CONSENT_GRANTED: 'Khách đồng ý lưu dữ liệu',
  CONTACT_TAGGED: 'Gắn thẻ khách hàng',
  CONTACT_UNTAGGED: 'Gỡ thẻ khách hàng',
  TAG_CREATED: 'Tạo thẻ mới',
  NOTE_UPDATED: 'Sửa ghi chú',
  NOTE_DELETED: 'Xoá ghi chú',
  CONVERSATION_HANDOFF: 'Chuyển hội thoại cho nhân viên',
  CONVERSATION_ASSIGNED: 'Giao hội thoại',
  CONVERSATION_RELEASED: 'Trả hội thoại về hàng chờ',
  CONVERSATION_AUTO_RELEASED: 'Tự trả về hàng chờ (nhân viên ngoại tuyến)',
  CONVERSATION_ESCALATED: 'Nâng mức ưu tiên hội thoại chờ lâu',
  CONVERSATION_STATUS_CHANGED: 'Đổi trạng thái hội thoại',
  LEAD_CREATED: 'Tạo cơ hội tiềm năng',
  LEAD_UPDATED: 'Sửa cơ hội tiềm năng',
  LEAD_STATUS_CHANGED: 'Đổi trạng thái lead',
  LEAD_ASSIGNED: 'Giao lead',
  LEAD_CONVERTED: 'Chuyển lead thành deal',
  DEAL_CREATED: 'Tạo deal',
  DEAL_UPDATED: 'Sửa deal',
  DEAL_STAGE_CHANGED: 'Chuyển giai đoạn deal',
  DEAL_ASSIGNED: 'Giao deal',
  WIDGET_CREATED: 'Tạo khung chat website',
  WIDGET_CONFIG_UPDATED: 'Đổi cấu hình khung chat',
  WIDGET_ORIGIN_REJECTED: 'Chặn khung chat nhúng trên tên miền lạ',
  AUDIT_LOG_REVEALED: 'Xem đầy đủ bản ghi kiểm toán',
  // UC020 (Dev A, GD1) — KnowledgeDocumentServiceImpl
  DOCUMENT_UPDATED: 'Sửa thông tin tài liệu tri thức',
  DOCUMENT_REINDEXED: 'Nạp lại tài liệu tri thức',
  DOCUMENT_ARCHIVED: 'Gỡ tài liệu khỏi kho tri thức',
  // Sắp ghi qua AuditLogWriter.recordWithPersonalData
  CONTACT_MERGED: 'Hợp nhất hồ sơ khách hàng',
  // UC041 (Dev A, GD3) — platform/erasure/ErasureService
  ERASURE_REQUESTED: 'Tạo yêu cầu xoá dữ liệu cá nhân',
  ERASURE_IDENTITY_VERIFIED: 'Xác minh danh tính chủ thể dữ liệu',
  ERASURE_EXECUTED: 'Thực thi xoá dữ liệu cá nhân',
}

/** UC041 — hai nguồn yêu cầu (V109 `requested_by`). */
export const NHAN_NGUON_YEU_CAU: Record<'CONTACT' | 'STAFF', string> = {
  CONTACT: 'Khách hàng tự gửi yêu cầu',
  STAFF: 'Nhân viên tạo thay mặt khách',
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
