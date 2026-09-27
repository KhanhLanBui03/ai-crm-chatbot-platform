import { useState } from 'react'
import {
  CreditCard,
  Edit3,
  FileText,
  Globe,
  MessageSquare,
  Sparkles,
  Users,
} from 'lucide-react'
import { toast } from 'sonner'

import { useCapNhatGoiAdminMutation, useDanhSachGoiAdminQuery } from '@/api/admin'
import type { GoiDichVuAdmin } from '@/mocks/du-lieu-admin'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
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
import { Skeleton } from '@/components/ui/skeleton'

function dinhDangTien(so: number): string {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(so)
}

function dinhDangSo(so: number): string {
  return new Intl.NumberFormat('vi-VN').format(so)
}

const MAU_GOI: Record<string, string> = {
  TRIAL: 'from-slate-500 to-slate-600',
  STARTER: 'from-blue-500 to-blue-600',
  GROWTH: 'from-emerald-500 to-emerald-600',
  PRO: 'from-violet-500 to-violet-600',
}

/** Trang quản lý gói dịch vụ — xem và chỉnh sửa giá/hạn mức. */
export function AdminPlansPage() {
  const { data: dsGoi, isLoading } = useDanhSachGoiAdminQuery()
  const [capNhat, { isLoading: dangCapNhat }] = useCapNhatGoiAdminMutation()
  const [goiSua, datGoiSua] = useState<GoiDichVuAdmin | null>(null)
  const [form, datForm] = useState({
    monthlyPriceVnd: 0,
    maxUsers: 0,
    maxConversationsPerMonth: 0,
    maxTokensPerMonth: 0,
    maxDocuments: 0,
    maxChannels: 0,
  })

  function moSua(goi: GoiDichVuAdmin) {
    datGoiSua(goi)
    datForm({
      monthlyPriceVnd: goi.monthlyPriceVnd,
      maxUsers: goi.maxUsers,
      maxConversationsPerMonth: goi.maxConversationsPerMonth,
      maxTokensPerMonth: goi.maxTokensPerMonth,
      maxDocuments: goi.maxDocuments,
      maxChannels: goi.maxChannels,
    })
  }

  async function xuLyCapNhat() {
    if (!goiSua) return
    try {
      await capNhat({ code: goiSua.code, data: form }).unwrap()
      toast.success(`Đã cập nhật gói ${goiSua.name}`)
      datGoiSua(null)
    } catch {
      toast.error('Không thể cập nhật gói dịch vụ')
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-96 rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Quản lý gói dịch vụ</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Cấu hình giá và hạn mức cho từng gói thuê bao
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {dsGoi?.map((goi) => (
          <Card key={goi.code} className="relative overflow-hidden flex flex-col">
            {/* Header gradient */}
            <div className={`h-2 bg-gradient-to-r ${MAU_GOI[goi.code] ?? 'from-gray-500 to-gray-600'}`} />
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{goi.name}</CardTitle>
                <Badge variant="secondary" className="tabular-nums">
                  {goi.tenantCount} DN
                </Badge>
              </div>
              <CardDescription className="text-xs">{goi.description}</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 space-y-3">
              <div className="text-center pb-3 border-b">
                <span className="text-2xl font-bold tabular-nums">
                  {goi.monthlyPriceVnd === 0 ? 'Miễn phí' : dinhDangTien(goi.monthlyPriceVnd)}
                </span>
                {goi.monthlyPriceVnd > 0 && (
                  <span className="text-muted-foreground text-sm"> / tháng</span>
                )}
              </div>
              <div className="space-y-2.5 text-sm">
                <div className="flex items-center gap-2.5">
                  <Users className="size-4 text-muted-foreground shrink-0" />
                  <span>{dinhDangSo(goi.maxUsers)} người dùng</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <MessageSquare className="size-4 text-muted-foreground shrink-0" />
                  <span>{dinhDangSo(goi.maxConversationsPerMonth)} hội thoại/tháng</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <Sparkles className="size-4 text-muted-foreground shrink-0" />
                  <span>{dinhDangSo(goi.maxTokensPerMonth)} token AI/tháng</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <FileText className="size-4 text-muted-foreground shrink-0" />
                  <span>{dinhDangSo(goi.maxDocuments)} tài liệu</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <Globe className="size-4 text-muted-foreground shrink-0" />
                  <span>{goi.maxChannels} kênh</span>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button
                variant="outline"
                className="w-full gap-1.5"
                onClick={() => moSua(goi)}
              >
                <Edit3 className="size-3.5" />
                Chỉnh sửa
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {/* Dialog chỉnh sửa gói */}
      <Dialog open={!!goiSua} onOpenChange={(mo) => !mo && datGoiSua(null)}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CreditCard className="size-5" />
              Chỉnh sửa gói {goiSua?.name}
            </DialogTitle>
            <DialogDescription>Cập nhật giá và hạn mức cho gói dịch vụ</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid gap-1.5">
              <Label>Giá mỗi tháng (VNĐ)</Label>
              <Input
                type="number"
                value={form.monthlyPriceVnd}
                onChange={(e) => datForm({ ...form, monthlyPriceVnd: Number(e.target.value) })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1.5">
                <Label>Người dùng tối đa</Label>
                <Input
                  type="number"
                  value={form.maxUsers}
                  onChange={(e) => datForm({ ...form, maxUsers: Number(e.target.value) })}
                />
              </div>
              <div className="grid gap-1.5">
                <Label>Hội thoại/tháng</Label>
                <Input
                  type="number"
                  value={form.maxConversationsPerMonth}
                  onChange={(e) =>
                    datForm({ ...form, maxConversationsPerMonth: Number(e.target.value) })
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1.5">
                <Label>Token AI/tháng</Label>
                <Input
                  type="number"
                  value={form.maxTokensPerMonth}
                  onChange={(e) =>
                    datForm({ ...form, maxTokensPerMonth: Number(e.target.value) })
                  }
                />
              </div>
              <div className="grid gap-1.5">
                <Label>Tài liệu tối đa</Label>
                <Input
                  type="number"
                  value={form.maxDocuments}
                  onChange={(e) => datForm({ ...form, maxDocuments: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="grid gap-1.5">
              <Label>Số kênh tối đa</Label>
              <Input
                type="number"
                value={form.maxChannels}
                onChange={(e) => datForm({ ...form, maxChannels: Number(e.target.value) })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => datGoiSua(null)}>
              Huỷ
            </Button>
            <Button onClick={xuLyCapNhat} disabled={dangCapNhat}>
              {dangCapNhat ? 'Đang lưu...' : 'Lưu thay đổi'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
