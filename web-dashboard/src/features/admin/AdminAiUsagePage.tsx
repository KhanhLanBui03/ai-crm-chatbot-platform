import {
  Activity,
  DollarSign,
  Gauge,
  Sparkles,
  TrendingUp,
} from 'lucide-react'

import { useTaiNguyenAiAdminQuery } from '@/api/admin'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

function dinhDangSo(so: number): string {
  return new Intl.NumberFormat('vi-VN').format(so)
}

function dinhDangUSD(so: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(so)
}

/** Trang giám sát FinOps — tài nguyên AI và chi phí toàn sàn. */
export function AdminAiUsagePage() {
  const { data: dsAi, isLoading } = useTaiNguyenAiAdminQuery()

  if (isLoading || !dsAi) {
    return (
      <div className="p-6 space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    )
  }

  const tongToken = dsAi.reduce((s, d) => s + d.tokensUsed, 0)
  const tongChiPhi = dsAi.reduce((s, d) => s + d.costUsd, 0)
  const tongTuongTac = dsAi.reduce((s, d) => s + d.interactionCount, 0)
  const tbLatency = Math.round(dsAi.reduce((s, d) => s + d.avgLatencyMs, 0) / dsAi.length)

  // Sắp theo token giảm dần
  const dsSap = [...dsAi].sort((a, b) => b.tokensUsed - a.tokensUsed)

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Tài nguyên & Chi phí AI</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Giám sát FinOps — tổng quan chi phí API LLM và mức tiêu thụ theo từng doanh nghiệp
        </p>
      </div>

      {/* KPI tổng */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-400">
              <Sparkles className="size-5" />
            </div>
            <div>
              <CardDescription className="text-xs">Tổng token tiêu thụ</CardDescription>
              <CardTitle className="text-xl tabular-nums">{dinhDangSo(tongToken)}</CardTitle>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-400">
              <DollarSign className="size-5" />
            </div>
            <div>
              <CardDescription className="text-xs">Chi phí ước tính</CardDescription>
              <CardTitle className="text-xl tabular-nums">{dinhDangUSD(tongChiPhi)}</CardTitle>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400">
              <Activity className="size-5" />
            </div>
            <div>
              <CardDescription className="text-xs">Tổng tương tác</CardDescription>
              <CardTitle className="text-xl tabular-nums">{dinhDangSo(tongTuongTac)}</CardTitle>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center gap-3 pb-2">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-orange-100 text-orange-600 dark:bg-orange-900/40 dark:text-orange-400">
              <Gauge className="size-5" />
            </div>
            <div>
              <CardDescription className="text-xs">Độ trễ trung bình</CardDescription>
              <CardTitle className="text-xl tabular-nums">{tbLatency} ms</CardTitle>
            </div>
          </CardHeader>
        </Card>
      </div>

      {/* Bảng chi tiết theo doanh nghiệp */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="size-4" />
            Mức tiêu thụ theo doanh nghiệp
          </CardTitle>
          <CardDescription>Sắp xếp theo số token AI giảm dần</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8">#</TableHead>
                <TableHead>Doanh nghiệp</TableHead>
                <TableHead className="text-right">Token dùng</TableHead>
                <TableHead className="text-right">Hạn mức</TableHead>
                <TableHead className="w-[160px]">Mức sử dụng</TableHead>
                <TableHead className="text-right">Chi phí (USD)</TableHead>
                <TableHead className="text-right">Độ trễ TB</TableHead>
                <TableHead className="text-right">Tương tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {dsSap.map((ai, i) => {
                const phanTram = ai.tokensLimit > 0
                  ? Math.min(100, Math.round((ai.tokensUsed / ai.tokensLimit) * 100))
                  : 0
                return (
                  <TableRow key={ai.tenantId}>
                    <TableCell className="text-muted-foreground text-sm">{i + 1}</TableCell>
                    <TableCell className="font-medium text-sm">{ai.companyName}</TableCell>
                    <TableCell className="text-right tabular-nums text-sm">
                      {dinhDangSo(ai.tokensUsed)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm text-muted-foreground">
                      {dinhDangSo(ai.tokensLimit)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={phanTram} className="h-1.5 flex-1" />
                        <span className="text-xs tabular-nums text-muted-foreground w-8 text-right">
                          {phanTram}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm">
                      <Badge
                        variant={ai.costUsd > 10 ? 'destructive' : 'secondary'}
                        className="tabular-nums"
                      >
                        {dinhDangUSD(ai.costUsd)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm">
                      <span className={ai.avgLatencyMs > 300 ? 'text-orange-600' : 'text-emerald-600'}>
                        {ai.avgLatencyMs} ms
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm">
                      {dinhDangSo(ai.interactionCount)}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
