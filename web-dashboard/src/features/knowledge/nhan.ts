import {
  CircleCheck,
  CircleX,
  Clock,
  FileClock,
  Loader2,
  type LucideIcon,
} from 'lucide-react'

import type { SacThai } from '@/components/ui/status-chip'
import type {
  LoaiKhoangTrong,
  LoaiNguonTaiLieu,
  TrangThaiCongViecNap,
  TrangThaiTaiLieu,
} from '@/types/schema'

/**
 * Nhãn tiếng Việt của miền tri thức.
 *
 * `Record` đầy đủ, không có nhánh mặc định: thêm giá trị vào enum trong
 * `docs/openapi/dashboard-api.yaml` mà quên ánh xạ ở đây thì `tsc` báo lỗi ngay.
 */

export const NHAN_TRANG_THAI_TAI_LIEU: Record<
  TrangThaiTaiLieu,
  { nhan: string; sacThai: SacThai; BieuTuong: LucideIcon }
> = {
  PENDING: { nhan: 'Chờ nạp', sacThai: 'neutral', BieuTuong: Clock },
  PROCESSING: { nhan: 'Đang nạp', sacThai: 'info', BieuTuong: Loader2 },
  READY: { nhan: 'Sẵn sàng', sacThai: 'success', BieuTuong: CircleCheck },
  FAILED: { nhan: 'Nạp lỗi', sacThai: 'destructive', BieuTuong: CircleX },
  ARCHIVED: { nhan: 'Đã lưu trữ', sacThai: 'neutral', BieuTuong: FileClock },
}

export const NHAN_LOAI_NGUON: Record<LoaiNguonTaiLieu, string> = {
  PDF: 'PDF',
  DOCX: 'Word',
  TXT: 'Văn bản thuần',
  MD: 'Markdown',
  HTML: 'HTML',
  URL: 'Đường dẫn web',
}

/**
 * Sáu bước của đường ống nạp, theo đúng thứ tự chạy. `PAUSED` và `FAILED` nằm ngoài chuỗi.
 * Thứ tự này dùng để vẽ thanh tiến độ ở SCR033 — đổi ở đây là đổi cả thanh đó.
 */
export const CHUOI_NAP: TrangThaiCongViecNap[] = [
  'QUEUED',
  'EXTRACTING',
  'CHUNKING',
  'EMBEDDING',
  'INDEXING',
  'DONE',
]

export const NHAN_TRANG_THAI_NAP: Record<
  TrangThaiCongViecNap,
  { nhan: string; sacThai: SacThai }
> = {
  QUEUED: { nhan: 'Chờ trong hàng đợi', sacThai: 'neutral' },
  EXTRACTING: { nhan: 'Trích xuất văn bản', sacThai: 'info' },
  CHUNKING: { nhan: 'Chia đoạn', sacThai: 'info' },
  EMBEDDING: { nhan: 'Tạo vector nhúng', sacThai: 'info' },
  INDEXING: { nhan: 'Lập chỉ mục', sacThai: 'info' },
  DONE: { nhan: 'Hoàn tất', sacThai: 'success' },
  FAILED: { nhan: 'Thất bại', sacThai: 'destructive' },
  PAUSED: { nhan: 'Tạm dừng', sacThai: 'warning' },
}

/**
 * Ba loại khoảng trống **không cùng một cách xử lý** — nhãn phải nói ra điều đó, nếu không cả
 * danh sách trông như một đống việc giống nhau:
 * - `NOT_COVERED` thì viết tài liệu mới;
 * - `OUT_OF_SCOPE_DATA` thì nối công cụ, viết tài liệu không giải quyết được gì;
 * - `LOW_CONFIDENCE` thì tài liệu đã có nhưng diễn đạt chưa đủ rõ để truy hồi bắt trúng.
 */
export const NHAN_LOAI_KHOANG_TRONG: Record<
  LoaiKhoangTrong,
  { nhan: string; moTa: string; sacThai: SacThai }
> = {
  NOT_COVERED: {
    nhan: 'Chưa có tài liệu',
    moTa: 'Kho tri thức không có nội dung nào trả lời được — cần bổ sung tài liệu.',
    sacThai: 'destructive',
  },
  OUT_OF_SCOPE_DATA: {
    nhan: 'Cần dữ liệu thời gian thực',
    moTa: 'Câu hỏi cần tra hệ thống nghiệp vụ, không phải tra tài liệu — cần nối công cụ MCP.',
    sacThai: 'info',
  },
  LOW_CONFIDENCE: {
    nhan: 'Truy hồi không chắc chắn',
    moTa: 'Có tài liệu liên quan nhưng độ bám nguồn dưới ngưỡng — cần viết lại cho rõ hơn.',
    sacThai: 'warning',
  },
}

/** Cỡ tệp đọc được bằng mắt. Chia 1024 chứ không phải 1000 — khớp với cách hệ điều hành hiển thị. */
export function coTep(byte: number): string {
  if (byte < 1024) return `${byte} B`
  if (byte < 1024 * 1024) return `${(byte / 1024).toFixed(0)} KB`
  return `${(byte / 1024 / 1024).toFixed(1)} MB`
}
