import { format, formatDistanceToNowStrict, isPast } from 'date-fns'
import { vi } from 'date-fns/locale'
import { Clock, Globe, Laptop, LogOut, ShieldAlert } from 'lucide-react'
import { toast } from 'sonner'

import { useDanhSachPhienQuery, useThuHoiPhienMutation } from '@/api/platform'
import { laLoiTruyVan } from '@/api/baseQuery'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import type { PhienDangNhap } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * SCR011 — các phiên đăng nhập đang mở. Màn chữ ký.
 *
 * Bố cục riêng chứ không phải bảng: mỗi phiên là một thẻ đủ rộng cho ba mẩu thông tin mà người
 * dùng cần đọc **cùng lúc** để nhận ra phiên lạ — thiết bị, địa chỉ mạng, thời điểm. Một bảng
 * bảy cột buộc mắt quét ngang, và đây là màn hình mà quét sót nghĩa là bỏ qua một phiên bị chiếm.
 */
export function SessionsPage() {
  const { data: phien, isLoading } = useDanhSachPhienQuery()
  const [thuHoi, ketQua] = useThuHoiPhienMutation()

  const khac = phien?.filter((p) => !p.isCurrent) ?? []

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="flex max-w-2xl flex-col gap-5 p-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-semibold tracking-tight">Phiên đăng nhập</h1>
          <p className="text-muted-foreground text-[13px]">
            Mọi thiết bị đang đăng nhập bằng tài khoản của bạn. Thu hồi một phiên là buộc thiết bị
            đó đăng nhập lại.
          </p>
        </div>

        {laLoiTruyVan(ketQua.error) && (
          <Alert variant="destructive">
            <AlertDescription>{ketQua.error.message}</AlertDescription>
          </Alert>
        )}

        {isLoading || !phien ? (
          <div className="flex flex-col gap-2.5">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-2.5">
              {phien.map((p) => (
                <ThePhien
                  key={p.id}
                  phien={p}
                  dangThuHoi={ketQua.isLoading}
                  onThuHoi={async () => {
                    await thuHoi(p.id).unwrap()
                    toast.success('Đã thu hồi phiên.')
                  }}
                />
              ))}
            </div>

            {khac.length > 0 && (
              <div className="flex items-center gap-3 rounded-lg border border-dashed p-3">
                <ShieldAlert className="text-muted-foreground size-4 shrink-0" />
                <span className="text-muted-foreground flex-1 text-[13px] leading-relaxed">
                  Thấy thiết bị lạ? Thu hồi hết rồi đổi mật khẩu ngay — thu hồi mà không đổi mật
                  khẩu thì người kia đăng nhập lại được.
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={ketQua.isLoading}
                  onClick={async () => {
                    for (const p of khac) await thuHoi(p.id).unwrap()
                    toast.success(`Đã thu hồi ${khac.length} phiên khác.`)
                  }}
                >
                  Thu hồi tất cả
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function ThePhien({
  phien,
  dangThuHoi,
  onThuHoi,
}: {
  phien: PhienDangNhap
  dangThuHoi: boolean
  onThuHoi: () => void
}) {
  const hetHan = isPast(new Date(phien.expiresAt))

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border p-3',
        phien.isCurrent && 'ring-primary/40 ring-1',
      )}
    >
      <div className="bg-muted text-muted-foreground flex size-9 shrink-0 items-center justify-center rounded-lg">
        <Laptop className="size-4" />
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{phien.userAgent ?? 'Thiết bị không rõ'}</span>
          {phien.isCurrent && <StatusChip sacThai="success">Thiết bị này</StatusChip>}
          {hetHan && <StatusChip sacThai="neutral">Đã hết hạn</StatusChip>}
        </div>

        <div className="text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          <span className="flex items-center gap-1">
            <Globe className="size-3" />
            {phien.ipAddress ?? 'Không rõ địa chỉ'}
          </span>
          <span className="flex items-center gap-1 tabular-nums">
            <Clock className="size-3" />
            Đăng nhập{' '}
            {formatDistanceToNowStrict(new Date(phien.issuedAt), { locale: vi, addSuffix: true })}
          </span>
          <span className="tabular-nums">
            Hết hạn {format(new Date(phien.expiresAt), 'dd/MM/yyyy HH:mm', { locale: vi })}
          </span>
        </div>
      </div>

      {/* Không cho thu hồi phiên đang dùng: đó là "đăng xuất", và nó có nút riêng ở menu tài
          khoản với xác nhận đàng hoàng. Ẩn nút ở đây tránh một cú bấm nhầm tự đá mình ra ngoài. */}
      {!phien.isCurrent && (
        <Button variant="ghost" size="sm" onClick={onThuHoi} disabled={dangThuHoi}>
          <LogOut />
          Thu hồi
        </Button>
      )}
    </div>
  )
}
