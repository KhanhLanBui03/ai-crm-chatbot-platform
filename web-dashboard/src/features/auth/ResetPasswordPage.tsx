import { zodResolver } from '@hookform/resolvers/zod'
import { AlertCircle, Check, ShieldCheck } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'

import { useDatLaiMatKhauMutation } from '@/api/auth'
import { laLoiTruyVan } from '@/api/baseQuery'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { AuthLayout } from '@/features/auth/AuthLayout'
import { cn } from '@/utils/cn'

const DIEU_KIEN = [
  { nhan: 'Ít nhất 8 ký tự', dat: (v: string) => v.length >= 8 },
  { nhan: 'Có chữ hoa', dat: (v: string) => /[A-Z]/.test(v) },
  { nhan: 'Có chữ số', dat: (v: string) => /\d/.test(v) },
  { nhan: 'Có ký tự đặc biệt', dat: (v: string) => /[^A-Za-z0-9]/.test(v) },
]

const luocDo = z
  .object({
    newPassword: z
      .string()
      .refine((v) => DIEU_KIEN.every((d) => d.dat(v)), 'Mật khẩu chưa đạt đủ bốn điều kiện.'),
    xacNhan: z.string(),
  })
  .refine((v) => v.newPassword === v.xacNhan, {
    message: 'Hai lần nhập mật khẩu không khớp.',
    path: ['xacNhan'],
  })

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR005 — đặt lại mật khẩu bằng mã. Mẫu M3 dựng thành trang, ngoài phạm vi đăng nhập.
 *
 * Mã đặt lại đọc từ `?token=` trên URL chứ không có ô nhập: người dùng tới đây bằng cách bấm
 * liên kết trong thư, và bắt họ chép tay một chuỗi ngẫu nhiên chỉ tạo thêm chỗ để gõ sai.
 * Không có token thì màn hình nói thẳng và chỉ đường về SCR004, thay vì hiện một biểu mẫu
 * chắc chắn sẽ hỏng lúc gửi.
 */
export function ResetPasswordPage() {
  const [thamSo] = useSearchParams()
  const dieuHuong = useNavigate()
  const token = thamSo.get('token')
  const [datLai, ketQua] = useDatLaiMatKhauMutation()

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { newPassword: '', xacNhan: '' },
  })

  const matKhau = form.watch('newPassword')
  const soDat = DIEU_KIEN.filter((d) => d.dat(matKhau)).length
  const thongDiepLoi = laLoiTruyVan(ketQua.error) ? ketQua.error.message : null

  if (!token) {
    return (
      <AuthLayout tieuDe="Thiếu mã đặt lại">
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>
            Địa chỉ này không kèm mã đặt lại. Mở lại liên kết trong thư, hoặc yêu cầu một liên kết
            mới nếu liên kết cũ đã quá 30 phút.
          </AlertDescription>
        </Alert>
        <Button size="lg" onClick={() => dieuHuong('/quen-mat-khau')}>
          Yêu cầu liên kết mới
        </Button>
      </AuthLayout>
    )
  }

  if (ketQua.isSuccess) {
    return (
      <AuthLayout tieuDe="Đã đổi mật khẩu">
        <Alert>
          <ShieldCheck />
          <AlertDescription>
            Mật khẩu mới đã có hiệu lực. Toàn bộ phiên đăng nhập cũ của tài khoản này đã bị thu
            hồi — nếu bạn đang mở hệ thống ở máy khác, hãy đăng nhập lại ở đó.
          </AlertDescription>
        </Alert>
        <Button size="lg" onClick={() => dieuHuong('/dang-nhap', { replace: true })}>
          Đăng nhập bằng mật khẩu mới
        </Button>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      tieuDe="Đặt mật khẩu mới"
      phuDe={
        <>
          Nhớ ra mật khẩu cũ?{' '}
          <Link to="/dang-nhap" className="text-primary hover:underline">
            Quay lại đăng nhập
          </Link>
        </>
      }
      chanTrang="Mã đặt lại chỉ dùng được một lần và hết hiệu lực sau 30 phút kể từ lúc gửi thư."
    >
      <form
        noValidate
        className="flex flex-col gap-4"
        onSubmit={form.handleSubmit(async (giaTri) => {
          try {
            await datLai({ token, newPassword: giaTri.newPassword }).unwrap()
          } catch {
            // Lỗi đã nằm trong `ketQua.error`; vùng cảnh báo bên dưới đọc từ đó
          }
        })}
      >
        {thongDiepLoi && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{thongDiepLoi}</AlertDescription>
          </Alert>
        )}

        <Field>
          <FieldLabel htmlFor="dl-mat-khau">Mật khẩu mới</FieldLabel>
          <Input
            id="dl-mat-khau"
            type="password"
            autoComplete="new-password"
            {...form.register('newPassword')}
          />
          <div className="flex flex-col gap-1.5 pt-0.5">
            <div className="bg-muted flex h-1 w-full overflow-hidden rounded-full">
              <span
                className={cn(
                  'h-full rounded-full transition-all',
                  soDat === 4 ? 'bg-success' : soDat >= 2 ? 'bg-warning' : 'bg-destructive',
                )}
                style={{ width: `${(soDat / DIEU_KIEN.length) * 100}%` }}
              />
            </div>
            <ul className="flex list-none flex-wrap gap-x-4 gap-y-1 p-0">
              {DIEU_KIEN.map((d) => {
                const dat = d.dat(matKhau)
                return (
                  <li
                    key={d.nhan}
                    className={cn(
                      'flex items-center gap-1 text-xs',
                      dat ? 'text-success' : 'text-muted-foreground',
                    )}
                  >
                    <Check className={cn('size-3', !dat && 'opacity-30')} />
                    {d.nhan}
                  </li>
                )
              })}
            </ul>
          </div>
          <FieldError errors={[form.formState.errors.newPassword]} />
        </Field>

        <Field>
          <FieldLabel htmlFor="dl-xac-nhan">Nhập lại mật khẩu mới</FieldLabel>
          <Input
            id="dl-xac-nhan"
            type="password"
            autoComplete="new-password"
            {...form.register('xacNhan')}
          />
          <FieldDescription>
            Đặt lại mật khẩu sẽ thu hồi mọi phiên đăng nhập đang mở của tài khoản.
          </FieldDescription>
          <FieldError errors={[form.formState.errors.xacNhan]} />
        </Field>

        <Button type="submit" size="lg" className="w-full" disabled={ketQua.isLoading}>
          {ketQua.isLoading ? 'Đang đổi mật khẩu…' : 'Đổi mật khẩu'}
        </Button>
      </form>
    </AuthLayout>
  )
}
