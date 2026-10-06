import { AlertTriangle, Ban, Check, CircleDot, Clock, Siren, Sparkles, type LucideIcon } from 'lucide-react'

import type { SacThai } from '@/components/ui/status-chip'
import type { LoaiKenh, TrangThaiHoiThoai } from '@/types/schema'

/**
 * Ánh xạ giá trị enum của ERD sang nhãn tiếng Việt.
 *
 * `Record` đầy đủ (không có nhánh mặc định) là cố ý: thêm một giá trị vào `TrangThaiHoiThoai`
 * mà quên ánh xạ ở đây thì `tsc` báo lỗi ngay, thay vì màn hình hiện chuỗi thô lúc chạy.
 * Vì enum sinh từ `docs/openapi/dashboard-api.yaml`, giao ước đổi là lỗi nổ ra ngay tại đây.
 */
export const NHAN_TRANG_THAI: Record<
  TrangThaiHoiThoai,
  { nhan: string; sacThai: SacThai; BieuTuong: LucideIcon }
> = {
  BOT_HANDLING: { nhan: 'Bot đang xử lý', sacThai: 'info', BieuTuong: Sparkles },
  PENDING_AGENT: { nhan: 'Chờ nhân viên', sacThai: 'warning', BieuTuong: Clock },
  AGENT_HANDLING: { nhan: 'Đang xử lý', sacThai: 'success', BieuTuong: CircleDot },
  RESOLVED: { nhan: 'Đã giải quyết', sacThai: 'success', BieuTuong: Check },
  CLOSED: { nhan: 'Đã đóng', sacThai: 'neutral', BieuTuong: Ban },
}

/**
 * Mức ưu tiên do job quá hạn nâng (UC014 7.1): chờ > 5 phút → 2, > 15 phút → 3. Mức thường (0–1)
 * không hiện chip — chỉ những hội thoại cần chú ý mới nổi lên.
 */
export const NHAN_UU_TIEN: Record<number, { nhan: string; sacThai: SacThai; BieuTuong: LucideIcon }> = {
  2: { nhan: 'Gấp', sacThai: 'warning', BieuTuong: AlertTriangle },
  3: { nhan: 'Khẩn', sacThai: 'destructive', BieuTuong: Siren },
}

export const NHAN_KENH: Record<LoaiKenh, string> = {
  WEB_WIDGET: 'Web Widget',
  ZALO: 'Zalo OA',
  FACEBOOK: 'Messenger',
}

