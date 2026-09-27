import { useState } from 'react'
import {
  ArrowUpRight,
  Bot,
  Building2,
  Calendar,
  Cpu,
  DollarSign,
  Download,
  Layers,
  MessageSquare,
  Percent,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { toast } from 'sonner'

import { usePhanTichNenTangQuery } from '@/api/admin'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

function dinhDangTien(so: number): string {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(so)
}

function dinhDangSo(so: number): string {
  return new Intl.NumberFormat('vi-VN').format(so)
}

function dinhDangUSD(so: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(so)
}

export function AdminAnalyticsPage() {
  const [khoang, datKhoang] = useState('30d')
  const { data: pt, isLoading, refetch, isFetching } = usePhanTichNenTangQuery({ khoang })

  if (isLoading || !pt) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-88 rounded-xl lg:col-span-2" />
          <Skeleton className="h-88 rounded-xl" />
        </div>
      </div>
    )
  }

  const { kpis } = pt

  const theKpis = [
    {
      nhan: 'Doanh thu định kỳ (MRR)',
      giaTri: dinhDangTien(kpis.mrrVnd),
      tangTruong: `+${kpis.mrrTangTruongPhanTram}% so với tháng trước`,
      laTang: true,
      icon: DollarSign,
      mau: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-950/60 dark:text-emerald-400',
    },
    {
      nhan: 'Doanh nghiệp hoạt động',
      giaTri: `${kpis.tongDoanhNghiep} công ty`,
      tangTruong: `Tỷ lệ chuyển đổi dùng thử ${kpis.tiLeChuyenDoiDungThu}%`,
      laTang: true,
      icon: Building2,
      mau: 'text-blue-600 bg-blue-100 dark:bg-blue-950/60 dark:text-blue-400',
    },
    {
      nhan: 'Tổng Token AI tiêu thụ',
      giaTri: dinhDangSo(kpis.tongTokensAi),
      tangTruong: `Chi phí: ${dinhDangUSD(kpis.chiPhiAiUsd)} · Biên lãi ${kpis.bienLoiNhuanGop}%`,
      laTang: true,
      icon: Sparkles,
      mau: 'text-violet-600 bg-violet-100 dark:bg-violet-950/60 dark:text-violet-400',
    },
    {
      nhan: 'Tỷ lệ AI tự động giải quyết',
      giaTri: `${kpis.tiLeAiTuXuLy}%`,
      tangTruong: `${dinhDangSo(kpis.tongHoiThoai)} hội thoại · Độ trễ ${kpis.doTreTrungBinhMs}ms`,
      laTang: true,
      icon: Bot,
      mau: 'text-amber-600 bg-amber-100 dark:bg-amber-950/60 dark:text-amber-400',
    },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Phân tích & Báo cáo Nền tảng</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Báo cáo toàn diện về tăng trưởng thuê bao, mức độ tiêu thụ AI và biên lợi nhuận SaaS.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Select value={khoang} onValueChange={datKhoang}>
            <SelectTrigger className="w-[140px] h-9 text-xs">
              <Calendar className="mr-1.5 size-3.5 text-muted-foreground" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">7 ngày qua</SelectItem>
              <SelectItem value="30d">30 ngày qua</SelectItem>
              <SelectItem value="90d">90 ngày qua</SelectItem>
              <SelectItem value="12m">12 tháng qua</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="h-9 px-3"
          >
            <RefreshCw className={`size-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>

          <Button
            size="sm"
            className="h-9 gap-1.5 bg-violet-600 hover:bg-violet-700 text-white"
            onClick={() => toast.success('Đã xuất file báo cáo phân tích tổng quan (.CSV)')}
          >
            <Download className="size-3.5" />
            <span className="hidden sm:inline">Xuất báo cáo</span>
          </Button>
        </div>
      </div>

      {/* 4 Thẻ KPI chính */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {theKpis.map((kpi) => (
          <Card key={kpi.nhan} className="relative overflow-hidden border-sidebar-border/60">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <span className="text-xs font-medium text-muted-foreground">{kpi.nhan}</span>
              <div className={`flex size-8 shrink-0 items-center justify-center rounded-lg ${kpi.mau}`}>
                <kpi.icon className="size-4" />
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="text-2xl font-bold tracking-tight tabular-nums">{kpi.giaTri}</div>
              <div className="mt-1.5 flex items-center text-xs text-muted-foreground">
                <ArrowUpRight className="mr-1 size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span className="truncate">{kpi.tangTruong}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Row 1: Doanh thu & Tỷ lệ AI */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Biểu đồ Doanh thu MRR & Số lượng Tenant */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="size-4 text-emerald-600" />
                  Tăng trưởng Doanh thu Định kỳ (MRR) & Doanh nghiệp
                </CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  Doanh thu hàng tháng so sánh với chi phí hạ tầng AI
                </CardDescription>
              </div>
              <Badge variant="outline" className="text-xs font-normal">
                6 tháng gần nhất
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={pt.tangTruongDoanhThuVaTenant}
                  margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorMrr" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted/40" />
                  <XAxis dataKey="thang" tickLine={false} axisLine={false} className="text-xs" />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${Math.round(v / 1_000_000)}M`}
                    className="text-xs"
                  />
                  <Tooltip
                    cursor={{
                      stroke: 'rgba(150, 150, 150, 0.25)',
                      strokeWidth: 1,
                      strokeDasharray: '4 4',
                    }}
                    formatter={((val: any, name: any) => [
                      typeof val === 'number' ? dinhDangTien(val) : (val ?? '0 ₫'),
                      name === 'mrr' ? 'Doanh thu MRR' : 'Chi phí AI',
                    ]) as any}
                    labelFormatter={(l) => `Tháng: ${l}`}
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                    }}
                    labelStyle={{ color: '#f8fafc', fontWeight: 600, marginBottom: '4px' }}
                    itemStyle={{ color: '#f8fafc', padding: '2px 0' }}
                  />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    formatter={(val) => (val === 'mrr' ? 'Doanh thu MRR' : 'Chi phí Token AI')}
                  />
                  <Area
                    type="monotone"
                    dataKey="mrr"
                    stroke="#8b5cf6"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#colorMrr)"
                  />
                  <Area
                    type="monotone"
                    dataKey="chiPhiAiCost"
                    stroke="#ef4444"
                    strokeWidth={1.5}
                    fillOpacity={1}
                    fill="url(#colorCost)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Biểu đồ Donut: Tỷ lệ AI Tự giải quyết vs Con người */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Bot className="size-4 text-emerald-600" />
              Hiệu quả Tự động hóa AI
            </CardTitle>
            <CardDescription className="text-xs">
              Tỷ lệ xử lý hội thoại toàn sàn
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center">
            <div className="h-56 w-full relative flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pt.tiLeXuLyAi}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {pt.tiLeXuLyAi.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={((val: any) => [`${val}%`, 'Tỷ lệ']) as any}
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                    }}
                    labelStyle={{ color: '#f8fafc', fontWeight: 600, marginBottom: '4px' }}
                    itemStyle={{ color: '#f8fafc', padding: '2px 0' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-bold tracking-tight tabular-nums text-foreground">
                  {kpis.tiLeAiTuXuLy}%
                </span>
                <span className="text-[11px] text-muted-foreground font-medium">AI giải quyết</span>
              </div>
            </div>

            <div className="w-full space-y-2 mt-2 pt-2 border-t text-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="size-2.5 rounded-full bg-emerald-500" />
                  <span>AI tự xử lý 100%</span>
                </div>
                <span className="font-semibold tabular-nums">78.4%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="size-2.5 rounded-full bg-amber-500" />
                  <span>Chuyển tư vấn viên</span>
                </div>
                <span className="font-semibold tabular-nums">21.6%</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Tiêu thụ Token AI & Kênh giao tiếp */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Biểu đồ Cột chồng: Token Prompt vs Completion */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Cpu className="size-4 text-violet-600" />
                  Lượng Token AI Tiêu thụ Hàng ngày
                </CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  Phân tách giữa Input Prompt và Output Completion
                </CardDescription>
              </div>
              <Badge variant="secondary" className="text-xs">
                7 ngày qua
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-68 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={pt.tieuThuTokenTheoNgay}
                  margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted/40" />
                  <XAxis dataKey="ngay" tickLine={false} axisLine={false} className="text-xs" />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${Math.round(v / 1000)}k`}
                    className="text-xs"
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(255, 255, 255, 0.06)' }}
                    formatter={((val: any, name: any) => [
                      typeof val === 'number' ? dinhDangSo(val) : (val ?? '0'),
                      name === 'promptTokens'
                        ? 'Prompt (Input)'
                        : name === 'completionTokens'
                        ? 'Completion (Output)'
                        : 'Chi phí ($)',
                    ]) as any}
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                    }}
                    labelStyle={{ color: '#f8fafc', fontWeight: 600, marginBottom: '4px' }}
                    itemStyle={{ color: '#f8fafc', padding: '2px 0' }}
                  />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    formatter={(v) => (v === 'promptTokens' ? 'Prompt Token' : 'Completion Token')}
                  />
                  <Bar dataKey="promptTokens" stackId="a" fill="#6366f1" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="completionTokens" stackId="a" fill="#a855f7" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Biểu đồ Kênh giao tiếp */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="size-4 text-blue-600" />
                  Lưu lượng Hội thoại theo Kênh
                </CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  Phân bổ nguồn tin nhắn của khách hàng trên toàn bộ các kênh
                </CardDescription>
              </div>
              <Badge variant="outline" className="text-xs">
                Tổng 22.464 lượt
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-68 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={pt.phanBoKenh}
                  layout="vertical"
                  margin={{ top: 10, right: 25, left: 10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} className="stroke-muted/40" />
                  <XAxis type="number" tickLine={false} axisLine={false} className="text-xs" />
                  <YAxis
                    dataKey="kenh"
                    type="category"
                    tickLine={false}
                    axisLine={false}
                    className="text-xs font-medium"
                    width={130}
                    interval={0}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(255, 255, 255, 0.06)' }}
                    formatter={((val: any) => [
                      typeof val === 'number' ? dinhDangSo(val) : (val ?? '0'),
                      'Lượt hội thoại',
                    ]) as any}
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                    }}
                    labelStyle={{ color: '#f8fafc', fontWeight: 600, marginBottom: '4px' }}
                    itemStyle={{ color: '#f8fafc', padding: '2px 0' }}
                  />
                  <Bar dataKey="soLuong" radius={[0, 4, 4, 0]} barSize={20}>
                    {pt.phanBoKenh.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Phân bổ mô hình LLM */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="size-4 text-indigo-600" />
            Cơ cấu Sử dụng Mô hình AI (LLM Model Breakdown)
          </CardTitle>
          <CardDescription className="text-xs">
            Tỷ trọng lượt gọi, lượng token tiêu thụ và chi phí API tương ứng theo từng Model
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {pt.phanBoMoHinhAi.map((model) => (
              <div
                key={model.moHinh}
                className="p-3.5 rounded-xl border bg-muted/20 flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm">{model.moHinh}</span>
                    <Badge variant="outline" className="text-[10px] uppercase font-mono">
                      {model.nhaCungCap}
                    </Badge>
                  </div>
                  <div className="mt-2 flex items-baseline justify-between text-xs text-muted-foreground">
                    <span>{dinhDangSo(model.soLuotGoi)} lượt gọi</span>
                    <span className="font-medium text-foreground">{model.phanTram}%</span>
                  </div>
                  <Progress value={model.phanTram} className="h-1.5 mt-1.5" />
                </div>

                <div className="pt-2 border-t flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Token: {dinhDangSo(model.tokens)}</span>
                  <span className="font-semibold text-violet-600 dark:text-violet-400">
                    {dinhDangUSD(model.chiPhiUsd)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Row 4: Bảng Top Doanh nghiệp & Biên lợi nhuận (Unit Economics) */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Percent className="size-4 text-emerald-600" />
                Top Doanh nghiệp & Biên Lợi nhuận SaaS (Unit Economics)
              </CardTitle>
              <CardDescription className="text-xs mt-0.5">
                Theo dõi mức độ sinh lời thực tế trên mỗi doanh nghiệp sau khi trừ chi phí token AI
              </CardDescription>
            </div>
            <Badge variant="secondary" className="text-xs">
              Top 5 Tiêu thụ cao nhất
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Doanh nghiệp</TableHead>
                <TableHead>Gói cước</TableHead>
                <TableHead className="text-right">Doanh thu gói / tháng</TableHead>
                <TableHead className="text-right">Tokens tiêu thụ</TableHead>
                <TableHead className="text-right">Chi phí AI ước tính</TableHead>
                <TableHead className="text-right">Biên lãi gộp (%)</TableHead>
                <TableHead className="text-right">Tỷ lệ AI xử lý</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pt.topTenantSuDung.map((tenant, idx) => (
                <TableRow key={tenant.tenantId}>
                  <TableCell className="text-muted-foreground text-sm font-mono">{idx + 1}</TableCell>
                  <TableCell className="font-medium text-sm">{tenant.companyName}</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        tenant.planCode === 'PRO'
                          ? 'default'
                          : tenant.planCode === 'GROWTH'
                          ? 'secondary'
                          : 'outline'
                      }
                      className="text-xs font-medium"
                    >
                      {tenant.planName}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm font-semibold">
                    {dinhDangTien(tenant.doanhThuThangVnd)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm">
                    <span className="font-medium">{dinhDangSo(tenant.tokensUsed)}</span>
                    <span className="text-muted-foreground text-xs"> / {dinhDangSo(tenant.tokensLimit)}</span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm text-red-600 dark:text-red-400 font-medium">
                    {dinhDangTien(tenant.chiPhiAiVnd)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm">
                    <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800 font-semibold">
                      {tenant.bienLoiNhuanPhanTram}%
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm font-medium text-emerald-600 dark:text-emerald-400">
                    {tenant.tiLeAiXuLy}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
