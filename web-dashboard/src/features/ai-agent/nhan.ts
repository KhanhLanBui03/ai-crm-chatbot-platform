import type { SacThai } from '@/components/ui/status-chip'
import type {
  KetQuaGoiCongCu,
  KetQuaKiemDuyet,
  LoaiSuKienAnToan,
  LyDoChan,
  LyDoChuyenGiao,
  LyDoDanhGia,
  LyDoTuChoi,
  MucNghiemTrong,
  MucRuiRo,
  NhanhXuLyAi,
  TrangThaiPheDuyet,
} from '@/types/schema'

/** Nhãn tiếng Việt của miền tác tử AI, MCP và giám sát an toàn. */

/**
 * Ba mức rủi ro quyết định công cụ có được gọi tự động hay không, nên nhãn phải nói ra **hệ quả**
 * chứ không chỉ dịch tên: người cấu hình đọc bảng này để quyết định bật cái gì.
 */
export const NHAN_MUC_RUI_RO: Record<
  MucRuiRo,
  { nhan: string; moTa: string; sacThai: SacThai }
> = {
  READ: {
    nhan: 'Chỉ đọc',
    moTa: 'Không đổi dữ liệu — gọi được tự động, không cần người duyệt.',
    sacThai: 'neutral',
  },
  WRITE: {
    nhan: 'Ghi dữ liệu',
    moTa: 'Tạo hoặc sửa bản ghi — luôn phải có người duyệt trước khi chạy.',
    sacThai: 'warning',
  },
  DESTRUCTIVE: {
    nhan: 'Phá huỷ',
    moTa: 'Xoá, huỷ hoặc chuyển tiền — luôn phải có người duyệt, và nên tắt khi chưa cần.',
    sacThai: 'destructive',
  },
}

export const NHAN_KET_QUA_KIEM_DUYET: Record<
  KetQuaKiemDuyet,
  { nhan: string; sacThai: SacThai }
> = {
  ALLOWED: { nhan: 'Cho phép', sacThai: 'success' },
  BLOCKED: { nhan: 'Bị chặn', sacThai: 'destructive' },
  NEEDS_APPROVAL: { nhan: 'Chờ duyệt', sacThai: 'warning' },
}

export const NHAN_LY_DO_CHAN: Record<LyDoChan, string> = {
  NOT_ALLOWLISTED: 'Công cụ không nằm trong danh sách cho phép',
  TOOL_DISABLED: 'Công cụ đang tắt',
  SCHEMA_HASH_MISMATCH: 'Lược đồ công cụ đã đổi, chưa được duyệt lại',
  INVALID_ARGUMENTS: 'Tham số không khớp lược đồ',
  CROSS_TENANT_IDENTIFIER: 'Định danh không thuộc doanh nghiệp này',
  RATE_LIMIT_EXCEEDED: 'Vượt số lời gọi cho phép trong một hội thoại',
}

export const NHAN_TRANG_THAI_DUYET: Record<
  TrangThaiPheDuyet,
  { nhan: string; sacThai: SacThai }
> = {
  PENDING: { nhan: 'Chờ người duyệt', sacThai: 'warning' },
  APPROVED: { nhan: 'Đã duyệt', sacThai: 'success' },
  REJECTED: { nhan: 'Đã từ chối', sacThai: 'destructive' },
  EXPIRED: { nhan: 'Hết hạn chờ', sacThai: 'neutral' },
}

export const NHAN_KET_QUA_GOI: Record<KetQuaGoiCongCu, { nhan: string; sacThai: SacThai }> = {
  SUCCESS: { nhan: 'Thành công', sacThai: 'success' },
  BUSINESS_ERROR: { nhan: 'Lỗi nghiệp vụ', sacThai: 'warning' },
  TIMEOUT: { nhan: 'Quá hạn chờ', sacThai: 'destructive' },
  TRANSPORT_ERROR: { nhan: 'Lỗi truyền tải', sacThai: 'destructive' },
}

export const NHAN_NHANH_XU_LY: Record<NhanhXuLyAi, { nhan: string; sacThai: SacThai }> = {
  SMALL_TALK: { nhan: 'Chào hỏi', sacThai: 'neutral' },
  RAG: { nhan: 'Truy hồi tri thức', sacThai: 'info' },
  TOOL_CALL: { nhan: 'Gọi công cụ', sacThai: 'warning' },
  CLARIFY: { nhan: 'Hỏi lại cho rõ', sacThai: 'neutral' },
  HANDOFF: { nhan: 'Chuyển nhân viên', sacThai: 'warning' },
  SUMMARY: { nhan: 'Tóm tắt', sacThai: 'neutral' },
  EXTRACTION: { nhan: 'Trích xuất thông tin', sacThai: 'neutral' },
}

export const NHAN_LY_DO_TU_CHOI: Record<LyDoTuChoi, string> = {
  NOT_COVERED: 'Kho tri thức không có nội dung phù hợp',
  OUT_OF_SCOPE_DATA: 'Cần dữ liệu nghiệp vụ mà tác tử không truy cập được',
  LOW_CONFIDENCE: 'Độ bám nguồn dưới ngưỡng',
  SAFETY_PROBE: 'Phát hiện dò tìm nhằm vượt rào an toàn',
}

export const NHAN_LY_DO_DANH_GIA: Record<LyDoDanhGia, string> = {
  WRONG_INFO: 'Thông tin sai',
  IRRELEVANT: 'Trả lời lạc đề',
  INCOMPLETE: 'Trả lời thiếu',
  BAD_TONE: 'Giọng điệu không phù hợp',
}

export const NHAN_MUC_NGHIEM_TRONG: Record<
  MucNghiemTrong,
  { nhan: string; sacThai: SacThai }
> = {
  LOW: { nhan: 'Thấp', sacThai: 'neutral' },
  MEDIUM: { nhan: 'Trung bình', sacThai: 'warning' },
  HIGH: { nhan: 'Cao', sacThai: 'destructive' },
  CRITICAL: { nhan: 'Nghiêm trọng', sacThai: 'destructive' },
}

export const NHAN_LOAI_SU_KIEN_AN_TOAN: Record<LoaiSuKienAnToan, string> = {
  PROMPT_INJECTION_INPUT: 'Tiêm chỉ thị qua tin nhắn khách',
  PROMPT_INJECTION_TOOL_RESULT: 'Tiêm chỉ thị qua kết quả công cụ',
  PROMPT_INJECTION_DOCUMENT: 'Tiêm chỉ thị qua tài liệu tri thức',
  CROSS_TENANT_PROBE: 'Dò dữ liệu doanh nghiệp khác',
  INTERNAL_DATA_PROBE: 'Dò thông tin nội bộ hệ thống',
  TOOL_CALL_BLOCKED: 'Lời gọi công cụ bị chặn',
}

/**
 * Lý do chuyển giao có cột `countsAgainstAiQuality` ở giao ước.
 *
 * Khách chủ động xin gặp người, hoặc công cụ ghi cần người duyệt, **không phải là tác tử làm dở**.
 * Gộp hết vào một tỉ lệ "chuyển giao" là tự bôi xấu số liệu của chính mình trong báo cáo.
 */
export const NHAN_LY_DO_CHUYEN_GIAO: Record<LyDoChuyenGiao, string> = {
  CUSTOMER_REQUEST: 'Khách yêu cầu gặp người',
  LOW_CONFIDENCE: 'Độ tin cậy thấp',
  NO_GROUNDING: 'Không tìm được căn cứ',
  NEGATIVE_SENTIMENT: 'Khách có dấu hiệu bức xúc',
  REPEATED_FAILURE: 'Trả lời hỏng nhiều lần liên tiếp',
  WRITE_TOOL_APPROVAL: 'Cần người duyệt công cụ ghi',
  QUOTA_EXCEEDED: 'Chạm hạn mức hội thoại',
  LLM_ERROR: 'Lỗi mô hình ngôn ngữ',
}

export const NHAN_TRANG_THAI_MCP: Record<string, { nhan: string; sacThai: SacThai }> = {
  PENDING: { nhan: 'Chưa bắt tay', sacThai: 'neutral' },
  ACTIVE: { nhan: 'Đang hoạt động', sacThai: 'success' },
  ERROR: { nhan: 'Lỗi kết nối', sacThai: 'destructive' },
  DISCONNECTED: { nhan: 'Đã ngắt', sacThai: 'neutral' },
}

export const NHAN_NGAT_MACH: Record<string, { nhan: string; sacThai: SacThai }> = {
  CLOSED: { nhan: 'Mạch đóng', sacThai: 'success' },
  OPEN: { nhan: 'Mạch ngắt', sacThai: 'destructive' },
  HALF_OPEN: { nhan: 'Đang thử lại', sacThai: 'warning' },
}

export const NHAN_TU_TAT: Record<string, string> = {
  SCHEMA_HASH_CHANGED: 'Tự tắt vì lược đồ công cụ đã thay đổi',
  SERVER_DISCONNECTED: 'Tự tắt vì máy chủ MCP đã ngắt',
  ADMIN_DISABLED: 'Quản trị viên tắt thủ công',
}

export const tienVnd = (v: number | null | undefined) =>
  v == null ? '—' : `${new Intl.NumberFormat('vi-VN').format(Math.round(v))} ₫`

export const phanTram = (v: number | null | undefined, soLe = 1) =>
  v == null ? '—' : `${(v * 100).toFixed(soLe)}%`

/** Độ trễ đọc được: dưới một giây thì mili-giây, trên thì giây có một chữ số thập phân. */
export const doTre = (ms: number | null | undefined) =>
  ms == null ? '—' : ms < 1_000 ? `${ms} ms` : `${(ms / 1_000).toFixed(1)} s`
