import { zodResolver } from '@hookform/resolvers/zod'
import { MailCheck } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { useQuenMatKhauMutation } from '@/api/auth'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { AuthLayout } from '@/features/auth/AuthLayout'

const luocDo = z.object({ email: z.email('Địa chỉ thư không hợp lệ.') })
type GiaTri = z.infer<typeof luocDo>

/**
 * SCR004 — yêu cầu đặt lại mật khẩu. Mẫu M3 dựng thành trang, ngoài phạm vi đăng nhập.
 *
 * Màn này **luôn** báo thành công, kể cả khi địa chỉ thư không tồn tại trong hệ thống. Trả lời
 * khác nhau cho hai trường hợp là biến biểu mẫu này thành công cụ dò tài khoản: gõ lần lượt một
 * danh sách thư rồi đọc thông báo là biết ai đang dùng hệ thống (bề mặt T7).
 */
export function ForgotPasswordPage() {
  const dieuHuong = useNavigate()
  const [gui, ketQua] = useQuenMatKhauMutation()

  const form = useForm<GiaTri>({ resolver: zodResolver(luocDo), defaultValues: { email: '' } })
  const thu = form.getValues('email')

  if (ketQua.isSuccess) {
    return (
      <AuthLayout
        tieuDe="Đã gửi hướng dẫn đặt lại"
        phuDe={<>Kiểm tra hộp thư của bạn để tiếp tục.</>}
      >
        <Alert>
          <MailCheck />
          <AlertDescription>
            Nếu <strong>{thu}</strong> có tài khoản trong hệ thống, một liên kết đặt lại mật khẩu
            vừa được gửi tới đó. Liên kết có hiệu lực <strong>30 phút</strong> và chỉ dùng được
            một lần.
          </AlertDescription>
        </Alert>

        <div className="flex flex-col gap-2">
          <Button size="lg" onClick={() => dieuHuong('/dang-nhap')}>
            Về trang đăng nhập
          </Button>
          <Button variant="outline" size="lg" onClick={() => ketQua.reset()}>
            Gửi lại cho địa chỉ khác
          </Button>
        </div>

        <p className="text-muted-foreground text-xs leading-relaxed">
          Không thấy thư? Kiểm tra mục thư rác trước khi gửi lại — gửi nhiều lần liên tiếp sẽ bị
          giới hạn tần suất.
        </p>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      tieuDe="Quên mật khẩu"
      phuDe={
        <>
          Nhớ ra rồi?{' '}
          <Link to="/dang-nhap" className="text-primary hover:underline">
            Quay lại đăng nhập
          </Link>
        </>
      }
      chanTrang="Đặt lại mật khẩu sẽ thu hồi toàn bộ phiên đăng nhập đang mở của tài khoản này."
    >
      <form
        noValidate
        className="flex flex-col gap-4"
        onSubmit={form.handleSubmit(async (giaTri) => {
          await gui({ email: giaTri.email }).unwrap()
        })}
      >
        <Field>
          <FieldLabel htmlFor="qm-email">Email công việc</FieldLabel>
          <Input
            id="qm-email"
            type="email"
            autoComplete="username"
            placeholder="an.pham@cattuong.vn"
            {...form.register('email')}
          />
          <FieldDescription>
            Nhập đúng địa chỉ đã dùng để đăng nhập. Hệ thống không tiết lộ địa chỉ nào có tài khoản.
          </FieldDescription>
          <FieldError errors={[form.formState.errors.email]} />
        </Field>

        <Button type="submit" size="lg" className="w-full" disabled={ketQua.isLoading}>
          {ketQua.isLoading ? 'Đang gửi…' : 'Gửi liên kết đặt lại'}
        </Button>
      </form>
    </AuthLayout>
  )
}
