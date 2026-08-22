import { Ban, Check, CircleDot, Clock, Sparkles, type LucideIcon } from 'lucide-react'

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

export const NHAN_KENH: Record<LoaiKenh, string> = {
  WEB_WIDGET: 'Web Widget',
  ZALO: 'Zalo OA',
  FACEBOOK: 'Messenger',
}

