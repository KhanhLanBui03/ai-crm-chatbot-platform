import type { SacThai } from '@/components/ui/status-chip'
import type {
  KetQuaHoatDong,
  LoaiHoatDong,
  MucDo,
  TrangThaiDeal,
  TrangThaiLead,
} from '@/types/schema'

/** Nhãn tiếng Việt dùng chung cho cả miền bán hàng — tránh mỗi màn tự đặt một kiểu. */

export const NHAN_TRANG_THAI_LEAD: Record<TrangThaiLead, { nhan: string; sacThai: SacThai }> = {
  NEW: { nhan: 'Mới', sacThai: 'info' },
  CONTACTED: { nhan: 'Đã liên hệ', sacThai: 'neutral' },
  QUALIFIED: { nhan: 'Đủ điều kiện', sacThai: 'success' },
  CONVERTED: { nhan: 'Đã chuyển đổi', sacThai: 'success' },
  DISQUALIFIED: { nhan: 'Không phù hợp', sacThai: 'neutral' },
}

export const NHAN_TRANG_THAI_DEAL: Record<TrangThaiDeal, { nhan: string; sacThai: SacThai }> = {
  OPEN: { nhan: 'Đang mở', sacThai: 'info' },
  WON: { nhan: 'Thắng', sacThai: 'success' },
  LOST: { nhan: 'Thua', sacThai: 'neutral' },
}

export const NHAN_MUC_DO: Record<MucDo, string> = {
  LOW: 'Thấp',
  MEDIUM: 'Trung bình',
  HIGH: 'Cao',
}

export const NHAN_LOAI_HOAT_DONG: Record<LoaiHoatDong, string> = {
  CALL: 'Gọi điện',
  MEETING: 'Gặp mặt',
  QUOTE: 'Báo giá',
  EMAIL: 'Gửi thư',
  NOTE: 'Ghi chú',
}

export const NHAN_KET_QUA: Record<KetQuaHoatDong, { nhan: string; sacThai: SacThai }> = {
  DONE: { nhan: 'Xong', sacThai: 'success' },
  NO_ANSWER: { nhan: 'Không nghe máy', sacThai: 'warning' },
  REFUSED: { nhan: 'Từ chối', sacThai: 'destructive' },
  NOT_INTERESTED: { nhan: 'Không quan tâm', sacThai: 'neutral' },
  RESCHEDULED: { nhan: 'Hẹn lại', sacThai: 'warning' },
}

export const tien = (v: number | null | undefined) =>
  v == null ? '—' : new Intl.NumberFormat('vi-VN').format(v) + ' ₫'

/** Rút gọn tiền cho thẻ Kanban: 104.000.000 ₫ chiếm cả thẻ, "104 tr" thì không. */
export function tienGon(v: number | null | undefined): string {
  if (v == null) return '—'
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1).replace('.0', '')} tỉ`
  if (v >= 1_000_000) return `${Math.round(v / 1_000_000)} tr`
  return new Intl.NumberFormat('vi-VN').format(v)
}

/**
 * Dải màu của điểm tiềm năng.
 *
 * Ba bậc chứ không phải một dải liên tục: người dùng cần quyết định "gọi hay không", và một dải
 * gradient buộc họ tự đặt ngưỡng trong đầu mỗi lần nhìn.
 */
export function sacThaiDiem(diem: number | null | undefined): SacThai {
  if (diem == null) return 'neutral'
  if (diem >= 80) return 'success'
  if (diem >= 60) return 'warning'
  return 'neutral'
}
