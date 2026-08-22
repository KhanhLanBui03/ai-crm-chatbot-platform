import { Download, TrendingDown, TrendingUp } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/utils/cn'

export interface TheKpi {
  nhan: string
  giaTri: string
  phuChu?: string
  /** Phần trăm thay đổi so với kỳ trước. Dương là tăng. */
  thayDoi?: number
  /**
   * Với chỉ số mà **giảm mới là tốt** (thời gian phản hồi, tỉ lệ chuyển giao) thì đặt `false`.
   * Không có cờ này thì mũi tên xanh/đỏ sẽ nói ngược ý nghĩa.
   */
  tangLaTot?: boolean
}

export interface KpiDashboardProps {
  tieuDe: string
  moTa?: string
  kpi: TheKpi[]
  /** Số liệu tổng hợp có độ trễ — hiện mốc cập nhật thay vì để người xem tưởng là thời gian thực. */
  capNhatLuc?: string
  khoangThoiGian: { giaTri: string; onDoi: (v: string) => void }
  onXuatBaoCao?: () => void
  /** Lưới biểu đồ do phía gọi dựng. */
  children: React.ReactNode
  dangTai?: boolean
}

const KHOANG = [
  { giaTri: '7d', nhan: '7 ngày qua' },
  { giaTri: '30d', nhan: '30 ngày qua' },
  { giaTri: '90d', nhan: '90 ngày qua' },
  { giaTri: 'ky-nay', nhan: 'Chu kỳ hiện tại' },
]

/**
 * Mẫu M5 — bảng điều khiển chỉ số. Phủ 1 màn hình, nhưng là màn hội đồng nhìn đầu tiên.
 *
 * Ràng buộc màu biểu đồ ở `docs/design/tokens.md`: ba màu chuỗi dữ liệu dưới 3:1 trên nền trắng,
 * nên **mọi biểu đồ dùng chúng bắt buộc có nhãn trực tiếp hoặc bảng dữ liệu kèm theo**. Đây là
 * nghĩa vụ thường trực của từng biểu đồ truyền vào `children`, không phải việc component này lo.
 */
export function KpiDashboard({
  tieuDe,
  moTa,
  kpi,
  capNhatLuc,
  khoangThoiGian,
  onXuatBaoCao,
  children,
  dangTai = false,
}: KpiDashboardProps) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight">{tieuDe}</h1>
            {moTa && <p className="text-muted-foreground text-[13px]">{moTa}</p>}
            {capNhatLuc && (
              <p className="text-muted-foreground text-xs">Số liệu cập nhật lúc {capNhatLuc}</p>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            <Select value={khoangThoiGian.giaTri} onValueChange={khoangThoiGian.onDoi}>
              <SelectTrigger size="sm" className="w-auto min-w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {KHOANG.map((k) => (
                  <SelectItem key={k.giaTri} value={k.giaTri}>
                    {k.nhan}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {onXuatBaoCao && (
              <Button variant="outline" size="sm" onClick={onXuatBaoCao}>
                <Download />
                Xuất báo cáo
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {dangTai
            ? Array.from({ length: kpi.length || 4 }).map((_, i) => (
                <Skeleton key={i} className="h-[88px] w-full rounded-lg" />
              ))
            : kpi.map((k) => <TheChiSo key={k.nhan} {...k} />)}
        </div>

        {children}
      </div>
    </div>
  )
}

function TheChiSo({ nhan, giaTri, phuChu, thayDoi, tangLaTot = true }: TheKpi) {
  const coThayDoi = thayDoi !== undefined && thayDoi !== 0
  const tang = (thayDoi ?? 0) > 0
  const tot = tang === tangLaTot

  return (
    <Card>
      <CardContent className="flex flex-col gap-1.5">
        <span className="text-muted-foreground text-[13px]">{nhan}</span>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold tracking-tight tabular-nums">{giaTri}</span>
          {coThayDoi && (
            <span
              className={cn(
                'flex items-center gap-0.5 text-xs font-medium tabular-nums',
                tot ? 'text-success' : 'text-destructive',
              )}
            >
              {tang ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
              {Math.abs(thayDoi).toLocaleString('vi-VN', { maximumFractionDigits: 1 })}%
            </span>
          )}
        </div>
        {phuChu && <span className="text-muted-foreground text-xs">{phuChu}</span>}
      </CardContent>
    </Card>
  )
}
