import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '@/components/ui/button'

/**
 * Thanh phân trang, đếm trang từ 0 giống máy chủ nhưng **hiển thị từ 1** cho người dùng.
 * Quy đổi đúng một chỗ ở đây; mọi màn khác cứ truyền số trang của máy chủ vào.
 */
export function Pagination({
  trang,
  tongSoTrang,
  tongSoMuc,
  coTrang,
  onDoiTrang,
}: {
  trang: number
  tongSoTrang: number
  tongSoMuc: number
  coTrang: number
  onDoiTrang: (trangMoi: number) => void
}) {
  if (tongSoMuc === 0) return null

  const dau = trang * coTrang + 1
  const cuoi = Math.min((trang + 1) * coTrang, tongSoMuc)

  return (
    <div className="flex shrink-0 items-center justify-between gap-3 border-t px-4 py-2.5">
      <span className="text-muted-foreground text-[13px] tabular-nums">
        {dau.toLocaleString('vi-VN')}–{cuoi.toLocaleString('vi-VN')} trong{' '}
        {tongSoMuc.toLocaleString('vi-VN')}
      </span>

      <div className="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="sm"
          disabled={trang <= 0}
          onClick={() => onDoiTrang(trang - 1)}
        >
          <ChevronLeft />
          Trước
        </Button>
        <span className="text-muted-foreground px-1 text-[13px] tabular-nums">
          {trang + 1} / {Math.max(tongSoTrang, 1)}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={trang >= tongSoTrang - 1}
          onClick={() => onDoiTrang(trang + 1)}
        >
          Sau
          <ChevronRight />
        </Button>
      </div>
    </div>
  )
}
