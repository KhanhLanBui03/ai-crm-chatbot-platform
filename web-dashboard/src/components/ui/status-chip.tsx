import type { LucideIcon } from 'lucide-react'

import { cn } from '@/utils/cn'

export type SacThai = 'success' | 'warning' | 'destructive' | 'info' | 'neutral'

/**
 * Nhãn trạng thái — nền pha loãng + chữ đậm màu, theo đúng ngôn ngữ của preset `radix-nova`.
 *
 * LUÔN kèm nhãn chữ, và kèm biểu tượng khi có: màu trạng thái không bao giờ được là tín hiệu
 * duy nhất. Component này không biết nghiệp vụ — phần ánh xạ enum sang nhãn nằm ở từng feature.
 */
const NEN: Record<SacThai, string> = {
  success: 'bg-success/12 text-success',
  warning: 'bg-warning/12 text-warning',
  destructive: 'bg-destructive/12 text-destructive',
  info: 'bg-info/12 text-info',
  neutral: 'bg-secondary text-secondary-foreground',
}

export function StatusChip({
  sacThai = 'neutral',
  BieuTuong,
  children,
  className,
}: {
  sacThai?: SacThai
  BieuTuong?: LucideIcon
  children: React.ReactNode
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex h-5 w-fit shrink-0 items-center gap-1 rounded-full px-2 text-xs font-medium whitespace-nowrap',
        NEN[sacThai],
        className,
      )}
    >
      {BieuTuong && <BieuTuong className="size-3" />}
      {children}
    </span>
  )
}
