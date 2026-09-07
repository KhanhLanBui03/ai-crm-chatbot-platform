import { zodResolver } from '@hookform/resolvers/zod'
import { AlertCircle, Check } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { useDangKyMutation } from '@/api/auth'
import { laLoiTruyVan } from '@/api/baseQuery'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { AuthLayout } from '@/features/auth/AuthLayout'
import { cn } from '@/utils/cn'

const NGANH = [
  'Bán lẻ',
  'Thương mại điện tử',
  'Giáo dục và đào tạo',
  'Dịch vụ chuyên môn',
  'Sản xuất',
  'Du lịch và lưu trú',
  'Khác',
]

/**
 * Bốn điều kiện, kiểm **từng cái một** để hiện được thanh tiến trình.
 *
 * Một thông báo "mật khẩu chưa đủ mạnh" thì người dùng phải đoán thiếu gì; bốn dòng có dấu tích
 * thì họ sửa đúng chỗ ngay lần thử thứ hai.
 */
const DIEU_KIEN = [
  { nhan: 'Ít nhất 8 ký tự', dat: (v: string) => v.length >= 8 },
  { nhan: 'Có chữ hoa', dat: (v: string) => /[A-Z]/.test(v) },
  { nhan: 'Có chữ số', dat: (v: string) => /\d/.test(v) },
  { nhan: 'Có ký tự đặc biệt', dat: (v: string) => /[^A-Za-z0-9]/.test(v) },
]

const luocDo = z
  .object({
    companyName: z
      .string()
      .min(2, 'Tên doanh nghiệp cần ít nhất 2 ký tự.')
      .max(200, 'Tên doanh nghiệp tối đa 200 ký tự.'),
    industry: z.string().optional(),
    fullName: z.string().min(2, 'Nhập họ tên người quản trị.').max(200),
    email: z.email('Địa chỉ thư không hợp lệ.'),
    password: z
      .string()
      .refine((v) => DIEU_KIEN.every((d) => d.dat(v)), 'Mật khẩu chưa đạt đủ bốn điều kiện.'),
    acceptedTerms: z.literal(true, {
      message: 'Cần đồng ý điều khoản và chính sách dữ liệu cá nhân.',
    }),
  })

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR001 — đăng ký tài khoản doanh nghiệp. Màn chữ ký.
 *
 * Chính lời gọi này **tạo ra doanh nghiệp**, nên nó là màn duy nhất không có `tenantId` ở đâu cả:
 * chưa có tenant nào để mà thuộc về. `slug` cũng không nhận từ biểu mẫu — máy chủ sinh từ tên
 * doanh nghiệp rồi tự bảo đảm duy nhất, vì để người dùng chọn là mở đường cho việc chiếm chỗ
 * những slug đẹp và đoán được doanh nghiệp nào đang dùng hệ thống.
 *
 * Đăng ký xong **chưa đăng nhập được**: phải xác thực thư trước (SCR002). Trả luôn access token
 * ở đây sẽ nhanh hơn một bước, nhưng cũng có nghĩa là bất kỳ ai gõ được một địa chỉ thư đều tạo
 * được tenant hoạt động.
 */
export function RegisterPage() {
  const dieuHuong = useNavigate()
  const [dangKy, ketQua] = useDangKyMutation()

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: {
      companyName: '',
      industry: '',
      fullName: '',
      email: '',
      password: '',
      acceptedTerms: false as unknown as true,
    },
  })

  const matKhau = form.watch('password')
  const soDat = DIEU_KIEN.filter((d) => d.dat(matKhau)).length
  const thongDiepLoi = laLoiTruyVan(ketQua.error) ? ketQua.error.message : null

  return (
    <AuthLayout
      tieuDe="Đăng ký doanh nghiệp"
      phuDe={
        <>
          Đã có tài khoản?{' '}
          <Link to="/dang-nhap" className="text-primary hover:underline">
            Đăng nhập
          </Link>
        </>
      }
      chanTrang="Dữ liệu của mỗi doanh nghiệp nằm trong vùng cô lập riêng ở tầng cơ sở dữ liệu, không phải chỉ ở tầng ứng dụng."
    >
      <form
        noValidate
        className="flex flex-col gap-4"
        onSubmit={form.handleSubmit(async (giaTri) => {
          try {
            const kq = await dangKy({
              companyName: giaTri.companyName,
              industry: giaTri.industry || null,
              fullName: giaTri.fullName,
              email: giaTri.email,
              password: giaTri.password,
              timezone: 'Asia/Ho_Chi_Minh',
              acceptedTerms: true,
            }).unwrap()
            dieuHuong(`/xac-thuc-thu?email=${encodeURIComponent(kq.email)}`, { replace: true })
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
          <FieldLabel htmlFor="dk-cong-ty">Tên doanh nghiệp</FieldLabel>
          <Input
            id="dk-cong-ty"
            placeholder="Công ty TNHH Cát Tường"
            {...form.register('companyName')}
          />
          <FieldDescription>
            Địa chỉ đăng nhập riêng của bạn được sinh từ tên này.
          </FieldDescription>
          <FieldError errors={[form.formState.errors.companyName]} />
        </Field>

        <Field>
          <FieldLabel htmlFor="dk-nganh">Lĩnh vực</FieldLabel>
          <Select
            value={form.watch('industry') || ''}
            onValueChange={(v) => form.setValue('industry', v)}
          >
            <SelectTrigger id="dk-nganh">
              <SelectValue placeholder="Chọn lĩnh vực hoạt động" />
            </SelectTrigger>
            <SelectContent>
              {NGANH.map((n) => (
                <SelectItem key={n} value={n}>
                  {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>

        <Field>
          <FieldLabel htmlFor="dk-ho-ten">Họ tên người quản trị</FieldLabel>
          <Input id="dk-ho-ten" placeholder="Phạm Hoài An" {...form.register('fullName')} />
          <FieldError errors={[form.formState.errors.fullName]} />
        </Field>

        <Field>
          <FieldLabel htmlFor="dk-email">Email công việc</FieldLabel>
          <Input
            id="dk-email"
            type="email"
            autoComplete="username"
            placeholder="an.pham@cattuong.vn"
            {...form.register('email')}
          />
          <FieldDescription>Thư xác thực sẽ gửi tới địa chỉ này.</FieldDescription>
          <FieldError errors={[form.formState.errors.email]} />
        </Field>

        <Field>
          <FieldLabel htmlFor="dk-mat-khau">Mật khẩu</FieldLabel>
          <Input
            id="dk-mat-khau"
            type="password"
            autoComplete="new-password"
            {...form.register('password')}
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
          <FieldError errors={[form.formState.errors.password]} />
        </Field>

        <Field orientation="horizontal">
          <Checkbox
            id="dk-dieu-khoan"
            checked={form.watch('acceptedTerms')}
            onCheckedChange={(v) =>
              form.setValue('acceptedTerms', (v === true) as true, { shouldValidate: true })
            }
          />
          <FieldLabel htmlFor="dk-dieu-khoan" className="text-[13px] leading-relaxed font-normal">
            Tôi đồng ý với điều khoản dịch vụ và chính sách xử lý dữ liệu cá nhân theo Nghị định
            13/2023/NĐ-CP.
          </FieldLabel>
        </Field>
        <FieldError errors={[form.formState.errors.acceptedTerms]} />

        <Button type="submit" size="lg" className="w-full" disabled={ketQua.isLoading}>
          {ketQua.isLoading ? 'Đang tạo tài khoản…' : 'Tạo tài khoản doanh nghiệp'}
        </Button>
      </form>
    </AuthLayout>
  )
}
