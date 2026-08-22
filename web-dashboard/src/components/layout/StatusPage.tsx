import { CircleCheck, CircleX, Loader2, MailCheck, type LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/utils/cn'
import type { ThaoTac } from '@/components/layout/ListPage'

export type TrangThaiTrang = 'dang-xu-ly' | 'thanh-cong' | 'that-bai' | 'cho-thao-tac'

const KIEU: Record<
  TrangThaiTrang,
  { BieuTuong: LucideIcon; mauChu: string; mauNen: string; quay?: boolean }
> = {
  'dang-xu-ly': {
    BieuTuong: Loader2,
    mauChu: 'text-primary',
    mauNen: 'bg-primary/10',
    quay: true,
  },
  'thanh-cong': { BieuTuong: CircleCheck, mauChu: 'text-success', mauNen: 'bg-success/12' },
  'that-bai': { BieuTuong: CircleX, mauChu: 'text-destructive', mauNen: 'bg-destructive/12' },
  'cho-thao-tac': { BieuTuong: MailCheck, mauChu: 'text-warning', mauNen: 'bg-warning/12' },
}

export interface StatusPageProps {
  trangThai: TrangThaiTrang
  tieuDe: string
  moTa?: string
  /** Khối nội dung phụ: mã theo dõi, hộp xem trước, hướng dẫn tiếp theo. */
  chiTiet?: React.ReactNode
  thaoTacChinh?: ThaoTac
  thaoTacPhu?: ThaoTac
  /** Bọc toàn màn hình — dùng cho các trang ngoài phạm vi đăng nhập (xác thực thư, đặt lại mật khẩu). */
  toanManHinh?: boolean
}

/**
 * Mẫu M6 — trang trạng thái đơn. Phủ 3 màn hình (ADR-0011).
 *
 * Bốn trạng thái, không phải hai. `cho-thao-tac` tách khỏi `thanh-cong` là có chủ đích: "đã gửi
 * thư, mời bạn mở hộp thư" không phải là kết thúc, và hiển thị nó bằng dấu tích xanh sẽ khiến
 * người dùng đóng tab rồi không bao giờ xác thực.
 */
export function StatusPage({
  trangThai,
  tieuDe,
  moTa,
  chiTiet,
  thaoTacChinh,
  thaoTacPhu,
  toanManHinh = false,
}: StatusPageProps) {
  const kieu = KIEU[trangThai]

  return (
    <div
      className={cn(
        'flex flex-1 items-center justify-center p-6',
        toanManHinh && 'bg-background text-foreground min-h-screen',
      )}
    >
      <div className="flex w-full max-w-md flex-col items-center gap-4 text-center">
        <div
          className={cn(
            'flex size-12 items-center justify-center rounded-full',
            kieu.mauNen,
            kieu.mauChu,
          )}
        >
          <kieu.BieuTuong className={cn('size-6', kieu.quay && 'animate-spin')} />
        </div>

        <div className="flex flex-col gap-1.5">
          <h1 className="text-xl font-semibold tracking-tight text-pretty">{tieuDe}</h1>
          {moTa && (
            <p className="text-muted-foreground text-sm leading-relaxed text-pretty">{moTa}</p>
          )}
        </div>

        {chiTiet && <div className="w-full">{chiTiet}</div>}

        {(thaoTacChinh || thaoTacPhu) && (
          <div className="flex items-center gap-2">
            {thaoTacPhu && (
              <Button variant={thaoTacPhu.bienThe ?? 'outline'} onClick={thaoTacPhu.onClick}>
                {thaoTacPhu.BieuTuong && <thaoTacPhu.BieuTuong />}
                {thaoTacPhu.nhan}
              </Button>
            )}
            {thaoTacChinh && (
              <Button variant={thaoTacChinh.bienThe ?? 'default'} onClick={thaoTacChinh.onClick}>
                {thaoTacChinh.BieuTuong && <thaoTacChinh.BieuTuong />}
                {thaoTacChinh.nhan}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
