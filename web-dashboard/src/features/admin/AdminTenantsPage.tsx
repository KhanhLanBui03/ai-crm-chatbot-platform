import { useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Lock,
  Search,
  Unlock,
  XCircle,
} from 'lucide-react'
import { toast } from 'sonner'

import {
  useDanhSachDoanhNghiepAdminQuery,
  useKhoaDoanhNghiepMutation,
  useKichHoatDoanhNghiepMutation,
} from '@/api/admin'
import type { DoanhNghiepAdmin } from '@/mocks/du-lieu-admin'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import { Textarea } from '@/components/ui/textarea'

const TRANG_THAI_BADGE: Record<
  string,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: typeof CheckCircle2 }
> = {
  ACTIVE: { label: 'Hoạt động', variant: 'default', icon: CheckCircle2 },
  TRIAL: { label: 'Dùng thử', variant: 'secondary', icon: Clock },
  SUSPENDED: { label: 'Bị tạm dừng', variant: 'destructive', icon: XCircle },
  EXPIRED: { label: 'Hết hạn', variant: 'outline', icon: AlertTriangle },
}

function dinhDangSo(so: number): string {
  return new Intl.NumberFormat('vi-VN').format(so)
}

function dinhDangNgay(iso: string): string {
  return new Date(iso).toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/** Trang quản lý danh sách doanh nghiệp — tìm kiếm, lọc, khóa/mở khóa. */
export function AdminTenantsPage() {
  const [tuKhoa, datTuKhoa] = useState('')
  const [trangThai, datTrangThai] = useState<string>('')
  const [goiLoc, datGoiLoc] = useState<string>('')
  const [dnKhoa, datDnKhoa] = useState<DoanhNghiepAdmin | null>(null)
  const [lyDoKhoa, datLyDoKhoa] = useState('')

  const { data: trang, isLoading } = useDanhSachDoanhNghiepAdminQuery({
    q: tuKhoa || undefined,
    status: trangThai || undefined,
    planCode: goiLoc || undefined,
  })

  const [khoaDN, { isLoading: dangKhoa }] = useKhoaDoanhNghiepMutation()
  const [moKhoaDN] = useKichHoatDoanhNghiepMutation()

  async function xuLyKhoa() {
    if (!dnKhoa || !lyDoKhoa.trim()) return
    try {
      await khoaDN({ id: dnKhoa.id, reason: lyDoKhoa.trim() }).unwrap()
      toast.success(`Đã tạm dừng ${dnKhoa.companyName}`)
      datDnKhoa(null)
      datLyDoKhoa('')
    } catch {
      toast.error('Không thể khóa doanh nghiệp')
    }
  }

  async function xuLyMoKhoa(dn: DoanhNghiepAdmin) {
    try {
      await moKhoaDN({ id: dn.id }).unwrap()
      toast.success(`Đã kích hoạt lại ${dn.companyName}`)
    } catch {
      toast.error('Không thể mở khóa doanh nghiệp')
    }
  }

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Quản lý doanh nghiệp</h1>
          <p className="text-muted-foreground text-xs sm:text-sm mt-0.5">
            Danh sách toàn bộ doanh nghiệp đang sử dụng nền tảng
          </p>
        </div>
        <div className="flex items-center">
          <Badge variant="secondary" className="text-xs sm:text-sm tabular-nums">
            {trang?.totalItems ?? 0} doanh nghiệp
          </Badge>
        </div>
      </div>

      {/* Bộ lọc */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="relative sm:col-span-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                placeholder="Tìm theo tên công ty, email, slug..."
                className="pl-9 w-full"
                value={tuKhoa}
                onChange={(e) => datTuKhoa(e.target.value)}
              />
            </div>
            <div>
              <Select value={trangThai} onValueChange={datTrangThai}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value=" ">Tất cả trạng thái</SelectItem>
                  <SelectItem value="ACTIVE">Hoạt động</SelectItem>
                  <SelectItem value="TRIAL">Dùng thử</SelectItem>
                  <SelectItem value="SUSPENDED">Bị tạm dừng</SelectItem>
                  <SelectItem value="EXPIRED">Hết hạn</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Select value={goiLoc} onValueChange={datGoiLoc}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Gói dịch vụ" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value=" ">Tất cả gói</SelectItem>
                  <SelectItem value="TRIAL">Dùng thử</SelectItem>
                  <SelectItem value="STARTER">Starter</SelectItem>
                  <SelectItem value="GROWTH">Growth</SelectItem>
                  <SelectItem value="PRO">Pro</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bảng doanh nghiệp */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 rounded-md" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[200px]">Doanh nghiệp</TableHead>
                    <TableHead className="min-w-[90px]">Gói</TableHead>
                    <TableHead className="min-w-[130px]">Trạng thái</TableHead>
                    <TableHead className="text-right whitespace-nowrap">Người dùng</TableHead>
                    <TableHead className="text-right whitespace-nowrap">Hội thoại</TableHead>
                    <TableHead className="text-right whitespace-nowrap">Token AI</TableHead>
                    <TableHead className="whitespace-nowrap">Ngày tham gia</TableHead>
                    <TableHead className="text-right whitespace-nowrap">Thao tác</TableHead>
                  </TableRow>
                </TableHeader>
              <TableBody>
                {trang?.items.map((dn) => {
                  const tt = TRANG_THAI_BADGE[dn.status] ?? TRANG_THAI_BADGE.ACTIVE
                  const TtIcon = tt.icon
                  return (
                    <TableRow key={dn.id}>
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="font-medium text-sm">{dn.companyName}</span>
                          <span className="text-xs text-muted-foreground">{dn.contactEmail}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {dn.planName}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={tt.variant} className="gap-1">
                          <TtIcon className="size-3" />
                          {tt.label}
                        </Badge>
                        {dn.suspendedReason && (
                          <p className="text-xs text-destructive mt-1 max-w-[200px] truncate" title={dn.suspendedReason}>
                            {dn.suspendedReason}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{dn.userCount}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {dinhDangSo(dn.conversationCount)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {dinhDangSo(dn.tokenUsed)}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {dinhDangNgay(dn.createdAt)}
                      </TableCell>
                      <TableCell className="text-right">
                        {dn.status === 'SUSPENDED' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1.5 text-emerald-600 border-emerald-200 hover:bg-emerald-50 dark:border-emerald-800 dark:hover:bg-emerald-900/30"
                            onClick={() => xuLyMoKhoa(dn)}
                          >
                            <Unlock className="size-3.5" />
                            Mở khóa
                          </Button>
                        ) : dn.status === 'ACTIVE' || dn.status === 'TRIAL' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1.5 text-destructive border-destructive/30 hover:bg-destructive/5"
                            onClick={() => datDnKhoa(dn)}
                          >
                            <Lock className="size-3.5" />
                            Đình chỉ
                          </Button>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
      </Card>

      {/* Dialog xác nhận khóa */}
      <Dialog open={!!dnKhoa} onOpenChange={(mo) => !mo && datDnKhoa(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Lock className="size-5 text-destructive" />
              Đình chỉ doanh nghiệp
            </DialogTitle>
            <DialogDescription>
              Bạn sắp tạm dừng <strong>{dnKhoa?.companyName}</strong>. Doanh nghiệp sẽ không thể
              truy cập hệ thống cho đến khi được mở khóa.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="lyDoKhoa">Lý do đình chỉ *</Label>
            <Textarea
              id="lyDoKhoa"
              placeholder="Nhập lý do đình chỉ (bắt buộc)..."
              value={lyDoKhoa}
              onChange={(e) => datLyDoKhoa(e.target.value)}
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => datDnKhoa(null)}>
              Huỷ
            </Button>
            <Button
              variant="destructive"
              onClick={xuLyKhoa}
              disabled={!lyDoKhoa.trim() || dangKhoa}
            >
              {dangKhoa ? 'Đang xử lý...' : 'Xác nhận đình chỉ'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
