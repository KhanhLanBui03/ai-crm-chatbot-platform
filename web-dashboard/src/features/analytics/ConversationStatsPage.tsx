import { format } from 'date-fns'
import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useHoiThoaiTheoNgayQuery } from '@/api/analytics'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { NHAN_KENH } from '@/features/conversations/nhan'
import type { LoaiKenh } from '@/types/schema'

const so = (v: number) => new Intl.NumberFormat('vi-VN').format(v)

/**
 * SCR049 — số liệu hội thoại theo ngày. Màn chữ ký.
 *
 * Cột **chồng** chứ không phải cột nhóm: tổng chiều cao là tổng hội thoại của ngày đó, và phần
 * màu cho biết ai xử lý. Cột nhóm cạnh nhau thì mắt phải tự cộng lại mới ra tổng.
 *
 * Có khoảng đệm 2px giữa các mảnh chồng — không có nó thì hai màu sát nhau trông như một dải
 * liền, và mảnh mỏng biến mất hoàn toàn.
 */
export function ConversationStatsPage() {
  const [kenh, datKenh] = useState<string>('tat-ca')
  const truyVan = useHoiThoaiTheoNgayQuery({})

  const duLieu = useMemo(() => {
    const theoNgay = new Map<string, { ngay: string; bot: number; nguoi: number; chuaXong: number }>()
    for (const d of truyVan.data ?? []) {
      if (kenh !== 'tat-ca' && d.channelType !== kenh) continue
      const cu = theoNgay.get(d.statDate) ?? { ngay: d.statDate, bot: 0, nguoi: 0, chuaXong: 0 }
      cu.bot += d.botResolved
      cu.nguoi += d.conversationsResolved - d.botResolved
      cu.chuaXong += Math.max(d.conversationsStarted - d.conversationsResolved, 0)
      theoNgay.set(d.statDate, cu)
    }
    return [...theoNgay.values()]
      .sort((a, b) => a.ngay.localeCompare(b.ngay))
      .map((d) => ({ ...d, nhan: format(new Date(d.ngay), 'dd/MM') }))
  }, [truyVan.data, kenh])

  const tong = duLieu.reduce(
    (t, d) => ({
      bot: t.bot + d.bot,
      nguoi: t.nguoi + d.nguoi,
      chuaXong: t.chuaXong + d.chuaXong,
    }),
    { bot: 0, nguoi: 0, chuaXong: 0 },
  )
  const tatCa = tong.bot + tong.nguoi + tong.chuaXong

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight">Hội thoại theo ngày</h1>
            <p className="text-muted-foreground text-[13px]">
              Tổng chiều cao mỗi cột là số hội thoại của ngày đó; màu cho biết ai đã xử lý.
            </p>
          </div>
          <Select value={kenh} onValueChange={datKenh}>
            <SelectTrigger size="sm" className="w-auto min-w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tat-ca">Mọi kênh</SelectItem>
              {(['WEB_WIDGET', 'ZALO', 'FACEBOOK'] as LoaiKenh[]).map((k) => (
                <SelectItem key={k} value={k}>
                  {NHAN_KENH[k]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <TheTong
            nhan="Tác tử tự đóng"
            giaTri={tong.bot}
            tyLe={tatCa > 0 ? tong.bot / tatCa : 0}
            mau="var(--chart-3)"
          />
          <TheTong
            nhan="Người xử lý"
            giaTri={tong.nguoi}
            tyLe={tatCa > 0 ? tong.nguoi / tatCa : 0}
            mau="var(--chart-1)"
          />
          <TheTong
            nhan="Chưa đóng"
            giaTri={tong.chuaXong}
            tyLe={tatCa > 0 ? tong.chuaXong / tatCa : 0}
            mau="var(--chart-2)"
          />
        </div>

        <Card>
          <CardContent>
            {truyVan.isLoading ? (
              <Skeleton className="h-72 w-full" />
            ) : (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={duLieu} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis
                      dataKey="nhan"
                      tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                      tickLine={false}
                      axisLine={false}
                      minTickGap={20}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      cursor={{ fill: 'var(--muted)' }}
                      contentStyle={{
                        background: 'var(--popover)',
                        border: '1px solid var(--border)',
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    {/* `stackId` giống nhau = chồng lên nhau. Viền cùng màu nền tạo khe 2px giữa
                        các mảnh, đủ để mảnh mỏng vẫn nhìn ra. */}
                    <Bar
                      dataKey="bot"
                      name="Tác tử tự đóng"
                      stackId="a"
                      fill="var(--chart-3)"
                      stroke="var(--background)"
                      strokeWidth={2}
                    />
                    <Bar
                      dataKey="nguoi"
                      name="Người xử lý"
                      stackId="a"
                      fill="var(--chart-1)"
                      stroke="var(--background)"
                      strokeWidth={2}
                    />
                    <Bar
                      dataKey="chuaXong"
                      name="Chưa đóng"
                      stackId="a"
                      fill="var(--chart-2)"
                      stroke="var(--background)"
                      strokeWidth={2}
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function TheTong({
  nhan,
  giaTri,
  tyLe,
  mau,
}: {
  nhan: string
  giaTri: number
  tyLe: number
  mau: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: mau }} />
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="text-muted-foreground text-xs">{nhan}</span>
        <span className="text-xl font-semibold tabular-nums">{so(giaTri)}</span>
      </div>
      <span className="text-muted-foreground shrink-0 text-[13px] tabular-nums">
        {(tyLe * 100).toFixed(1)}%
      </span>
    </div>
  )
}
