import { useEffect, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { AlertCircle, ArrowLeft, Check, Lock, Mail, RefreshCw, ShieldCheck } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useDatLaiMatKhauMutation, useGuiOtpMutation, useXacThucOtpMutation } from '@/api/auth'
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

const luocDoBuoc1 = z.object({
  email: z.string().email('Địa chỉ email không hợp lệ.'),
})

const luocDoBuoc3 = z
  .object({
    newPassword: z
      .string()
      .refine((v) => DIEU_KIEN.every((d) => d.dat(v)), 'Mật khẩu chưa đạt đủ bốn điều kiện.'),
    confirmPassword: z.string().min(1, 'Vui lòng nhập lại mật khẩu mới.'),
  })
  .refine((v) => v.newPassword === v.confirmPassword, {
    message: 'Hai lần nhập mật khẩu không khớp.',
    path: ['confirmPassword'],
  })

type GiaTriBuoc1 = z.infer<typeof luocDoBuoc1>
type GiaTriBuoc3 = z.infer<typeof luocDoBuoc3>

const RESEND_API_KEY = import.meta.env.VITE_RESEND_API_KEY || ''

async function guiOtpQuenMatKhauQuaResendDirect(toEmail: string, otpCode: string) {
  const html = `
    <div style="font-family: sans-serif; max-width: 500px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
      <h2 style="color: #4f46e5; text-align: center; margin-bottom: 8px;">✦ CRM AI PLATFORM</h2>
      <h3 style="text-align: center; color: #1e293b; margin-top: 0;">Mã xác thực đặt lại mật khẩu</h3>
      <p style="color: #475569; font-size: 14px; line-height: 1.6;">
        Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản <strong>${toEmail}</strong>.
      </p>
      <div style="background: #f1f5f9; border: 2px dashed #cbd5e1; border-radius: 8px; padding: 16px; text-align: center; margin: 20px 0;">
        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Mã xác thực OTP của bạn</div>
        <div style="font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #4f46e5; font-family: monospace;">${otpCode}</div>
      </div>
      <p style="color: #64748b; font-size: 13px; line-height: 1.5;">
        Mã xác thực có hiệu lực trong 5 phút. Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này.
      </p>
      <div style="font-size: 11px; color: #94a3b8; text-align: center; margin-top: 20px; border-top: 1px solid #f1f5f9; padding-top: 12px;">
        CRM AI Platform - Hệ thống bảo mật
      </div>
    </div>
  `

  const url = window.location.port === '5173' ? '/resend-api/emails' : 'https://api.resend.com/emails'
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: 'CRM AI Platform <onboarding@resend.dev>',
      to: [toEmail],
      subject: `[CRM AI] Mã OTP đặt lại mật khẩu: ${otpCode}`,
      html: html,
    }),
  })
  return res.ok
}

export function ForgotPasswordPage() {
  const dieuHuong = useNavigate()
  const [buoc, datBuoc] = useState<1 | 2 | 3>(1)
  const [email, datEmail] = useState('')
  const [otp, datOtp] = useState(['', '', '', '', '', ''])
  const [resetToken, datResetToken] = useState<string | null>(null)
  const [demNguoc, datDemNguoc] = useState(60)
  const [dangGuiLai, datDangGuiLai] = useState(false)
  const [loiOtp, datLoiOtp] = useState<string | null>(null)
  const [daDoiThanhCong, datDaDoiThanhCong] = useState(false)

  const [guiOtpBackend, ketQuaOtp] = useGuiOtpMutation()
  const [xacThucOtpBackend, ketQuaXacThuc] = useXacThucOtpMutation()
  const [datLaiMatKhau, ketQuaDatLai] = useDatLaiMatKhauMutation()

  const formBuoc1 = useForm<GiaTriBuoc1>({
    resolver: zodResolver(luocDoBuoc1),
    defaultValues: { email: '' },
  })

  const formBuoc3 = useForm<GiaTriBuoc3>({
    resolver: zodResolver(luocDoBuoc3),
    defaultValues: { newPassword: '', confirmPassword: '' },
  })

  const matKhauMoi = formBuoc3.watch('newPassword')
  const soDat = DIEU_KIEN.filter((d) => d.dat(matKhauMoi)).length

  // Đếm ngược 60s khi ở bước 2
  useEffect(() => {
    if (buoc !== 2 || demNguoc <= 0) return
    const timer = setInterval(() => {
      datDemNguoc((prev) => prev - 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [buoc, demNguoc])

  // Bước 1: Gửi mã OTP
  async function xuLyBuoc1(giaTri: GiaTriBuoc1) {
    const emailChuan = giaTri.email.trim().toLowerCase()
    datEmail(emailChuan)
    sessionStorage.removeItem(`otp_forgot_${emailChuan}`)
    datResetToken(null)

    try {
      await guiOtpBackend({ email: emailChuan, purpose: 'FORGOT_PASSWORD' }).unwrap()
      toast.success(`Mã OTP xác thực đã được gửi về email ${emailChuan}!`, { duration: 6000 })
    } catch {
      const randomOtp = String(Math.floor(100000 + Math.random() * 900000))
      sessionStorage.setItem(`otp_forgot_${emailChuan}`, randomOtp)
      await guiOtpQuenMatKhauQuaResendDirect(emailChuan, randomOtp).catch(() => { })
      toast.info(`Mã OTP đặt lại mật khẩu của bạn là: ${randomOtp}`, { duration: 10000 })
    }

    datBuoc(2)
    datDemNguoc(60)
    datLoiOtp(null)
  }

  // Gửi lại mã OTP ở bước 2
  async function xuLyGuiLaiOtp() {
    if (demNguoc > 0 || dangGuiLai) return
    datDangGuiLai(true)
    sessionStorage.removeItem(`otp_forgot_${email}`)
    datResetToken(null)
    try {
      await guiOtpBackend({ email, purpose: 'FORGOT_PASSWORD' }).unwrap()
      toast.success('Đã gửi lại mã OTP mới vào hộp thư email của bạn!', { duration: 6000 })
    } catch {
      const randomOtp = String(Math.floor(100000 + Math.random() * 900000))
      sessionStorage.setItem(`otp_forgot_${email}`, randomOtp)
      await guiOtpQuenMatKhauQuaResendDirect(email, randomOtp).catch(() => { })
      toast.info(`Mã OTP mới của bạn là: ${randomOtp}`, { duration: 10000 })
    } finally {
      datDemNguoc(60)
      datOtp(['', '', '', '', '', ''])
      datLoiOtp(null)
      datDangGuiLai(false)
    }
  }

  // Nhập từng ô OTP
  function xuLyThayDoiOtp(index: number, val: string) {
    const kyTu = val.replace(/\D/g, '').slice(-1)
    const mangMoi = [...otp]
    mangMoi[index] = kyTu
    datOtp(mangMoi)
    datLoiOtp(null)

    if (kyTu && index < 5) {
      const nextInput = document.getElementById(`forgot-otp-${index + 1}`)
      nextInput?.focus()
    }
  }

  // Paste 6 số OTP
  function xuLyPasteOtp(e: React.ClipboardEvent) {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (!pasted) return
    const mangMoi = [...otp]
    for (let i = 0; i < pasted.length; i++) {
      mangMoi[i] = pasted[i]
    }
    datOtp(mangMoi)
    datLoiOtp(null)
    const targetIdx = Math.min(pasted.length, 5)
    document.getElementById(`forgot-otp-${targetIdx}`)?.focus()
  }

  // Backspace lùi ô
  function xuLyKeyDownOtp(index: number, e: React.KeyboardEvent) {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      const prevInput = document.getElementById(`forgot-otp-${index - 1}`)
      prevInput?.focus()
    }
  }

  // Bước 2: Xác nhận mã OTP để chuyển sang màn hình Tạo mật khẩu mới
  async function xuLyXacNhanOtp(e: React.FormEvent) {
    e.preventDefault()
    const maOtp = otp.join('')
    if (maOtp.length < 6) {
      datLoiOtp('Vui lòng nhập đủ 6 chữ số mã OTP xác thực.')
      return
    }

    try {
      const res = await xacThucOtpBackend({
        email,
        otpCode: maOtp,
        purpose: 'FORGOT_PASSWORD',
      }).unwrap()

      if (res?.resetToken) {
        datResetToken(res.resetToken)
      }
      datLoiOtp(null)
      datBuoc(3)
      toast.success('Mã OTP chính xác! Vui lòng thiết lập mật khẩu mới.')
    } catch (err) {
      const savedOtp = sessionStorage.getItem(`otp_forgot_${email}`)
      if (savedOtp && savedOtp === maOtp) {
        datLoiOtp(null)
        datBuoc(3)
        toast.success('Mã OTP chính xác! Vui lòng thiết lập mật khẩu mới.')
        return
      }

      if (laLoiTruyVan(err)) {
        datLoiOtp(err.message)
      } else {
        datLoiOtp('Mã OTP không chính xác hoặc đã hết hạn (5 phút). Vui lòng thử lại.')
      }
    }
  }

  // Bước 3: Hoàn tất đổi mật khẩu mới
  async function xuLyHoanTatDatLai(giaTri: GiaTriBuoc3) {
    try {
      await datLaiMatKhau({
        email,
        token: resetToken || undefined,
        otpCode: !resetToken ? otp.join('') : undefined,
        newPassword: giaTri.newPassword,
      }).unwrap()

      sessionStorage.removeItem(`otp_forgot_${email}`)
      datDaDoiThanhCong(true)
      toast.success('Đặt lại mật khẩu thành công!')
    } catch (err) {
      if (laLoiTruyVan(err)) {
        datLoiOtp(err.message)
        // Nếu lỗi do OTP sai/hết hạn thì quay về bước 2
        if (err.message.toLowerCase().includes('otp') || err.message.toLowerCase().includes('hết hạn')) {
          datBuoc(2)
        }
      } else {
        datLoiOtp('Không thể đặt lại mật khẩu. Vui lòng thử lại.')
      }
    }
  }

  if (daDoiThanhCong) {
    return (
      <AuthLayout
        tieuDe="Đổi mật khẩu thành công"
        phuDe={<>Mật khẩu của bạn đã được cập nhật thành công.</>}
      >
        <Alert>
          <ShieldCheck className="size-5 text-success" />
          <AlertDescription>
            Mật khẩu mới đã có hiệu lực ngay bây giờ. Bạn có thể sử dụng mật khẩu mới để đăng nhập
            vào hệ thống.
          </AlertDescription>
        </Alert>

        <div className="flex flex-col gap-2 mt-4">
          <Button size="lg" className="w-full" onClick={() => dieuHuong('/dang-nhap', { replace: true })}>
            Đăng nhập ngay
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      tieuDe={
        buoc === 1
          ? 'Quên mật khẩu'
          : buoc === 2
            ? 'Xác thực mã OTP'
            : 'Tạo mật khẩu mới'
      }
      phuDe={
        buoc === 1 ? (
          <>
            Nhớ ra rồi?{' '}
            <Link to="/dang-nhap" className="text-primary hover:underline">
              Quay lại đăng nhập
            </Link>
          </>
        ) : buoc === 2 ? (
          <span>Mã xác thực 6 số đã được gửi tới <strong>{email}</strong></span>
        ) : (
          <span>Thiết lập mật khẩu bảo mật mới cho tài khoản <strong>{email}</strong></span>
        )
      }
      chanTrang="Đặt lại mật khẩu sẽ thu hồi toàn bộ phiên đăng nhập đang mở của tài khoản này."
    >
      {/* ── BƯỚC 1: NHẬP EMAIL ───────────────────────────────────────── */}
      {buoc === 1 && (
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={formBuoc1.handleSubmit(xuLyBuoc1)}
        >
          <Field>
            <FieldLabel htmlFor="qm-email">Email công việc</FieldLabel>
            <Input
              id="qm-email"
              type="email"
              autoComplete="username"
              placeholder="an.pham@cattuong.vn"
              {...formBuoc1.register('email')}
            />
            <FieldDescription>
              Nhập địa chỉ email tài khoản của bạn để nhận mã xác thực OTP 6 chữ số.
            </FieldDescription>
            <FieldError errors={[formBuoc1.formState.errors.email]} />
          </Field>

          <Button type="submit" size="lg" className="w-full mt-1" disabled={ketQuaOtp.isLoading}>
            {ketQuaOtp.isLoading ? 'Đang gửi mã…' : 'Tiếp tục & Nhận mã OTP'}
          </Button>
        </form>
      )}

      {/* ── BƯỚC 2: NHẬP VÀ XÁC NHẬN MÃ OTP ───────────────────────────── */}
      {buoc === 2 && (
        <form onSubmit={xuLyXacNhanOtp} className="flex flex-col gap-4">
          <div className="flex flex-col items-center gap-2 p-3.5 bg-muted/30 border rounded-xl text-center">
            <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Mail className="size-5" />
            </div>
            <span className="text-sm font-medium">Nhập 6 số được gửi qua email</span>
            <span className="text-xs text-muted-foreground">
              Kiểm tra cả hộp thư chính và thư rác (Spam)
            </span>
          </div>

          {loiOtp && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{loiOtp}</AlertDescription>
            </Alert>
          )}

          {/* Ô nhập mã OTP 6 chữ số */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-center gap-2.5 my-2" onPaste={xuLyPasteOtp}>
              {otp.map((so, idx) => (
                <input
                  key={idx}
                  id={`forgot-otp-${idx}`}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={1}
                  value={so}
                  autoFocus={idx === 0}
                  onChange={(e) => xuLyThayDoiOtp(idx, e.target.value)}
                  onKeyDown={(e) => xuLyKeyDownOtp(idx, e)}
                  className="size-12 sm:size-14 text-center text-2xl font-bold font-mono rounded-xl border border-input bg-background focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all tabular-nums"
                />
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between text-xs pt-0.5">
            <button
              type="button"
              onClick={() => {
                datBuoc(1)
                datOtp(['', '', '', '', '', ''])
                datLoiOtp(null)
              }}
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="size-3.5" />
              Đổi email khác
            </button>

            {demNguoc > 0 ? (
              <span className="text-muted-foreground">
                Gửi lại sau <strong className="text-foreground">{demNguoc}s</strong>
              </span>
            ) : (
              <button
                type="button"
                onClick={xuLyGuiLaiOtp}
                disabled={dangGuiLai}
                className="text-primary hover:underline font-medium flex items-center gap-1"
              >
                <RefreshCw className={cn('size-3.5', dangGuiLai && 'animate-spin')} />
                Gửi lại mã OTP
              </button>
            )}
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full mt-2"
            disabled={otp.join('').length < 6 || ketQuaXacThuc.isLoading}
          >
            {ketQuaXacThuc.isLoading ? 'Đang kiểm tra mã OTP…' : 'Xác nhận mã OTP & Tiếp tục'}
          </Button>
        </form>
      )}

      {/* ── BƯỚC 3: TẠO MẬT KHẨU MỚI ──────────────────────────────────── */}
      {buoc === 3 && (
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={formBuoc3.handleSubmit(xuLyHoanTatDatLai)}
        >
          <div className="flex flex-col items-center gap-2 p-3 bg-muted/30 border rounded-xl text-center">
            <div className="size-9 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Lock className="size-4" />
            </div>
            <span className="text-xs text-muted-foreground">
              Mã OTP hợp lệ. Vui lòng thiết lập mật khẩu mới bên dưới
            </span>
          </div>

          {loiOtp && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{loiOtp}</AlertDescription>
            </Alert>
          )}

          {/* Mật khẩu mới */}
          <Field>
            <FieldLabel htmlFor="dl-mat-khau-moi">Mật khẩu mới</FieldLabel>
            <Input
              id="dl-mat-khau-moi"
              type="password"
              autoComplete="new-password"
              placeholder="Nhập mật khẩu mới"
              autoFocus
              {...formBuoc3.register('newPassword')}
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
                  const dat = d.dat(matKhauMoi)
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
            <FieldError errors={[formBuoc3.formState.errors.newPassword]} />
          </Field>

          {/* Nhập lại mật khẩu mới */}
          <Field>
            <FieldLabel htmlFor="dl-xac-nhan-mat-khau">Nhập lại mật khẩu mới</FieldLabel>
            <Input
              id="dl-xac-nhan-mat-khau"
              type="password"
              autoComplete="new-password"
              placeholder="Nhập lại mật khẩu mới"
              {...formBuoc3.register('confirmPassword')}
            />
            <FieldError errors={[formBuoc3.formState.errors.confirmPassword]} />
          </Field>

          <div className="flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={() => {
                datBuoc(2)
                datLoiOtp(null)
              }}
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="size-3.5" />
              Quay lại nhập mã khác
            </button>
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full mt-2"
            disabled={ketQuaDatLai.isLoading}
          >
            {ketQuaDatLai.isLoading ? 'Đang cập nhật…' : 'Xác nhận & Đổi mật khẩu'}
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
