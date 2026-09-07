import type { LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'

/**
 * Trạng thái rỗng.
 *
 * Phân biệt hai loại **khác hẳn nhau** — dùng nhầm là chỉ sai đường cho người dùng:
 * - *chưa có dữ liệu*: lối thoát là tạo bản ghi đầu tiên;
 * - *rỗng vì bộ lọc*: lối thoát là gỡ bộ lọc, và nút "tạo mới" ở đây chỉ gây lạc hướng.
 */
export function EmptyState({
  BieuTuong,
  tieuDe,
  moTa,
  thaoTac,
}: {
  BieuTuong: LucideIcon
  tieuDe: string
  moTa?: string
  thaoTac?: { nhan: string; onClick: () => void; bienThe?: 'default' | 'outline' }
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
      <div className="bg-muted text-muted-foreground flex size-11 items-center justify-center rounded-full">
        <BieuTuong className="size-5" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-base font-medium">{tieuDe}</span>
        {moTa && <span className="text-muted-foreground max-w-sm text-[13px]">{moTa}</span>}
      </div>
      {thaoTac && (
        <Button variant={thaoTac.bienThe ?? 'outline'} size="sm" onClick={thaoTac.onClick}>
          {thaoTac.nhan}
        </Button>
      )}
    </div>
  )
}
