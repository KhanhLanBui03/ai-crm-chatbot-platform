import {
  Activity,
  Building2,
  DollarSign,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react'

import { useThongKeNenTangQuery } from '@/api/admin'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'

function dinhDangTien(so: number): string {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(so)
}

function dinhDangSo(so: number): string {
  return new Intl.NumberFormat('vi-VN').format(so)
}

/** Trang tổng quan nền tảng — 4 KPI chính + biểu đồ phân bổ + tăng trưởng. */
export function AdminOverviewPage() {
  const { data: tk, isLoading } = useThongKeNenTangQuery()

  if (isLoading || !tk) {
    return (
      <div className="p-6 space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    )
  }

  const kpiCards = [
    {
      nhan: 'Tổng doanh nghiệp',
      giaTri: dinhDangSo(tk.tongDoanhNghiep),
      icon: Building2,
      moTa: `${tk.doanhNghiepHoatDong} hoạt động · ${tk.doanhNghiepDungThu} dùng thử`,
      mau: 'text-blue-600 bg-blue-100 dark:bg-blue-900/40 dark:text-blue-400',
    },
    {
      nhan: 'Doanh thu định kỳ (MRR)',
      giaTri: dinhDangTien(tk.mrrVnd),
      icon: DollarSign,
      moTa: 'Ước tính từ gói dịch vụ hiện tại',
      mau: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/40 dark:text-emerald-400',
    },
    {
      nhan: 'Hội thoại tháng này',
      giaTri: dinhDangSo(tk.tongHoiThoaiThang),
      icon: Activity,
      moTa: 'Tổng hội thoại trên toàn sàn',
      mau: 'text-orange-600 bg-orange-100 dark:bg-orange-900/40 dark:text-orange-400',
    },
    {
      nhan: 'Token AI tiêu thụ',
      giaTri: dinhDangSo(tk.tongTokenAiThang),
      icon: Sparkles,
      moTa: '≈ ' + dinhDangTien(Math.round(tk.tongTokenAiThang / 1000 * 0.003 * 25000)) + ' chi phí ước tính',
      mau: 'text-violet-600 bg-violet-100 dark:bg-violet-900/40 dark:text-violet-400',
    },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpiCards.map((kpi) => (
          <Card key={kpi.nhan} className="relative overflow-hidden">
            <CardHeader className="flex flex-row items-center gap-3 pb-2">
              <div className={`flex size-10 shrink-0 items-center justify-center rounded-lg ${kpi.mau}`}>
                <kpi.icon className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <CardDescription className="text-xs">{kpi.nhan}</CardDescription>
                <CardTitle className="text-xl tabular-nums">{kpi.giaTri}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">{kpi.moTa}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Phân bổ theo gói */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Phân bổ doanh nghiệp theo gói</CardTitle>
            <CardDescription>Số doanh nghiệp đang sử dụng mỗi gói dịch vụ</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {tk.phanBoTheoGoi.map((pb) => {
              const phanTram = Math.round((pb.soLuong / tk.tongDoanhNghiep) * 100)
              return (
                <div key={pb.goi} className="space-y-1.5">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{pb.goi}</span>
                    <span className="text-muted-foreground tabular-nums">
                      {pb.soLuong} DN ({phanTram}%)
                    </span>
                  </div>
                  <Progress value={phanTram} className="h-2" />
                </div>
              )
            })}
          </CardContent>
        </Card>

        {/* Tăng trưởng theo tháng */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tăng trưởng theo tháng</CardTitle>
            <CardDescription>Số doanh nghiệp và doanh thu MRR 6 tháng gần nhất</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {tk.tangTruongThang.map((t) => (
                <div key={t.thang} className="flex items-center gap-4 text-sm">
                  <span className="w-16 shrink-0 text-muted-foreground font-mono text-xs">
                    {t.thang}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Users className="size-3.5 text-muted-foreground" />
                      <span className="tabular-nums">{t.soDoanhNghiep} DN</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                    <TrendingUp className="size-3.5" />
                    <span className="tabular-nums text-xs font-medium">
                      {dinhDangTien(t.mrr)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cảnh báo hệ thống */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cảnh báo hệ thống</CardTitle>
          <CardDescription>Các vấn đề cần chú ý</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {tk.doanhNghiepBiKhoa > 0 && (
              <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                <Building2 className="size-4 shrink-0" />
                <span>{tk.doanhNghiepBiKhoa} doanh nghiệp đang bị tạm dừng</span>
              </div>
            )}
            {tk.doanhNghiepHetHan > 0 && (
              <div className="flex items-center gap-3 rounded-lg bg-orange-100 dark:bg-orange-900/30 p-3 text-sm text-orange-700 dark:text-orange-400">
                <Activity className="size-4 shrink-0" />
                <span>{tk.doanhNghiepHetHan} doanh nghiệp hết hạn chưa gia hạn</span>
              </div>
            )}
            {tk.doanhNghiepDungThu > 0 && (
              <div className="flex items-center gap-3 rounded-lg bg-blue-100 dark:bg-blue-900/30 p-3 text-sm text-blue-700 dark:text-blue-400">
                <Users className="size-4 shrink-0" />
                <span>{tk.doanhNghiepDungThu} doanh nghiệp đang dùng thử</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
