import { useState, useEffect } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { AlertCircle, ArrowLeft, Check, Mail, RefreshCw } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useDangKyMutation, useGuiOtpMutation } from '@/api/auth'
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
    email: z.string().email('Địa chỉ email không hợp lệ.'),
    password: z
      .string()
      .refine((v) => DIEU_KIEN.every((d) => d.dat(v)), 'Mật khẩu chưa đạt đủ bốn điều kiện.'),
    confirmPassword: z.string().min(1, 'Vui lòng nhập lại mật khẩu.'),
    acceptedTerms: z.literal(true, {
      message: 'Cần đồng ý điều khoản và chính sách dữ liệu cá nhân.',
    }),
  })
  .refine((v) => v.password === v.confirmPassword, {
    message: 'Hai lần nhập mật khẩu không khớp.',
    path: ['confirmPassword'],
  })

type GiaTri = z.infer<typeof luocDo>

const RESEND_API_KEY = import.meta.env.VITE_RESEND_API_KEY || ''

async function guiOtpQuaResendDirect(toEmail: string, companyName: string, otpCode: string) {
  const html = `
    <div style="font-family: sans-serif; max-width: 500px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
      <h2 style="color: #4f46e5; text-align: center; margin-bottom: 8px;">✦ CRM AI PLATFORM</h2>
      <h3 style="text-align: center; color: #1e293b; margin-top: 0;">Mã xác thực đăng ký tài khoản</h3>
      <p style="color: #475569; font-size: 14px; line-height: 1.6;">
        Chào bạn, cảm ơn bạn đã đăng ký tài khoản CRM AI cho <strong>${companyName || 'Doanh nghiệp của bạn'}</strong>.
      </p>
      <div style="background: #f1f5f9; border: 2px dashed #cbd5e1; border-radius: 8px; padding: 16px; text-align: center; margin: 20px 0;">
        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Mã OTP của bạn</div>
        <div style="font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #4f46e5; font-family: monospace;">${otpCode}</div>
      </div>
      <p style="color: #64748b; font-size: 13px; line-height: 1.5;">
        Mã xác thực có hiệu lực trong 5 phút. Vui lòng không chia sẻ mã này cho bất kỳ ai vì lý do bảo mật.
      </p>
      <div style="font-size: 11px; color: #94a3b8; text-align: center; margin-top: 20px; border-top: 1px solid #f1f5f9; padding-top: 12px;">
        CRM AI Platform - Hệ thống tự động
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
      subject: `[CRM AI] Mã OTP xác nhận đăng ký: ${otpCode}`,
      html: html,
    }),
  })
  return res.ok
}

export function RegisterPage() {
  const [buoc, datBuoc] = useState<1 | 2>(1)
  const [otp, datOtp] = useState(['', '', '', '', '', ''])
  const [demNguoc, datDemNguoc] = useState(60)
  const [dangGuiLai, datDangGuiLai] = useState(false)
  const [loiOtp, datLoiOtp] = useState<string | null>(null)

  const dieuHuong = useNavigate()
  const [dangKy, ketQuaDangKy] = useDangKyMutation()
  const [guiOtp, ketQuaOtp] = useGuiOtpMutation()

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: {
      companyName: '',
      industry: '',
      fullName: '',
      email: '',
      password: '',
      confirmPassword: '',
      acceptedTerms: false as unknown as true,
    },
  })

  const matKhau = form.watch('password')
  const emailHienTai = form.watch('email')
  const tenCtyHienTai = form.watch('companyName')
  const soDat = DIEU_KIEN.filter((d) => d.dat(matKhau)).length

  // Đếm ngược 60s khi ở bước 2
  useEffect(() => {
    if (buoc !== 2 || demNguoc <= 0) return
    const timer = setInterval(() => {
      datDemNguoc((prev) => prev - 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [buoc, demNguoc])

  // Xử lý gửi mã OTP ở bước 1
  async function xuLyBuoc1(giaTri: GiaTri) {
    sessionStorage.removeItem(`otp_reg_${giaTri.email.toLowerCase().trim()}`)

    try {
      await guiOtp({
        email: giaTri.email.trim(),
        companyName: giaTri.companyName,
        purpose: 'REGISTER',
      }).unwrap()
      toast.success(`Mã xác thực OTP đã được gửi đến ${giaTri.email}!`, { duration: 6000 })
    } catch {
      const randomOtp = String(Math.floor(100000 + Math.random() * 900000))
      sessionStorage.setItem(`otp_reg_${giaTri.email.toLowerCase().trim()}`, randomOtp)
      await guiOtpQuaResendDirect(giaTri.email.trim(), giaTri.companyName, randomOtp).catch(() => {})
      toast.info(`Mã OTP xác thực của bạn là: ${randomOtp}`, { duration: 10000 })
    }

    datBuoc(2)
    datDemNguoc(60)
    datLoiOtp(null)
  }

  // Gửi lại mã OTP
  async function xuLyGuiLaiOtp() {
    if (demNguoc > 0 || dangGuiLai) return
    datDangGuiLai(true)
    sessionStorage.removeItem(`otp_reg_${emailHienTai.toLowerCase().trim()}`)
    try {
      await guiOtp({
        email: emailHienTai.trim(),
        companyName: tenCtyHienTai,
        purpose: 'REGISTER',
      }).unwrap()
      toast.success('Đã gửi lại mã OTP mới vào hộp thư!', { duration: 6000 })
    } catch {
      const randomOtp = String(Math.floor(100000 + Math.random() * 900000))
      sessionStorage.setItem(`otp_reg_${emailHienTai.toLowerCase().trim()}`, randomOtp)
      await guiOtpQuaResendDirect(emailHienTai.trim(), tenCtyHienTai, randomOtp).catch(() => {})
      toast.info(`Mã OTP mới của bạn là: ${randomOtp}`, { duration: 10000 })
    } finally {
      datDemNguoc(60)
      datOtp(['', '', '', '', '', ''])
      datLoiOtp(null)
      datDangGuiLai(false)
    }
  }

  // Thay đổi từng ô OTP
  function xuLyThayDoiOtp(index: number, val: string) {
    const kyTu = val.replace(/\D/g, '').slice(-1)
    const mangMoi = [...otp]
    mangMoi[index] = kyTu
    datOtp(mangMoi)
    datLoiOtp(null)

    // Tự động nhảy ô tiếp theo
    if (kyTu && index < 5) {
      const nextInput = document.getElementById(`otp-input-${index + 1}`)
      nextInput?.focus()
    }
  }

  // Xử lý Paste 6 số OTP
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
    document.getElementById(`otp-input-${targetIdx}`)?.focus()
  }

  // Xử lý Backspace lùi ô
  function xuLyKeyDownOtp(index: number, e: React.KeyboardEvent) {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      const prevInput = document.getElementById(`otp-input-${index - 1}`)
      prevInput?.focus()
    }
  }

  // Hoàn tất xác nhận đăng ký bước 2
  async function xuLyHoanTatDangKy(e: React.FormEvent) {
    e.preventDefault()
    const maOtp = otp.join('')
    if (maOtp.length < 6) {
      datLoiOtp('Vui lòng nhập đủ 6 chữ số mã OTP.')
      return
    }

    const giaTri = form.getValues()
    const savedOtp = sessionStorage.getItem(`otp_reg_${giaTri.email.toLowerCase().trim()}`)
    if (savedOtp && savedOtp !== maOtp) {
      datLoiOtp('Mã OTP không chính xác hoặc đã hết hạn. Vui lòng thử lại.')
      return
    }

    try {
      await dangKy({
        companyName: giaTri.companyName,
        industry: giaTri.industry || null,
        fullName: giaTri.fullName,
        email: giaTri.email,
        password: giaTri.password,
        timezone: 'Asia/Ho_Chi_Minh',
        acceptedTerms: true,
        otpCode: maOtp,
      }).unwrap()

      toast.success('Xác thực tài khoản doanh nghiệp thành công!')
      dieuHuong(`/xac-thuc-thu?email=${encodeURIComponent(giaTri.email)}`, { replace: true })
    } catch (err) {
      if (laLoiTruyVan(err)) {
        datLoiOtp(err.message)
      } else {
        datLoiOtp('Mã OTP không hợp lệ hoặc đã hết hạn.')
      }
    }
  }

  return (
    <AuthLayout
      tieuDe={buoc === 1 ? 'Đăng ký doanh nghiệp' : 'Xác thực địa chỉ Email'}
      phuDe={
        buoc === 1 ? (
          <>
            Đã có tài khoản?{' '}
            <Link to="/dang-nhap" className="text-primary hover:underline">
              Đăng nhập
            </Link>
          </>
        ) : (
          <span>Mã xác thực 6 số đã được gửi tới <strong>{emailHienTai}</strong></span>
        )
      }
      chanTrang="Dữ liệu của mỗi doanh nghiệp nằm trong vùng cô lập riêng ở tầng cơ sở dữ liệu, đảm bảo tuân thủ Nghị định 13/2023/NĐ-CP."
    >
      {buoc === 1 ? (
        /* BƯỚC 1: NHẬP THÔNG TIN TÀI KHOẢN */
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={form.handleSubmit(xuLyBuoc1)}
        >
          {laLoiTruyVan(ketQuaOtp.error) && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{ketQuaOtp.error.message}</AlertDescription>
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
            <FieldDescription>Mã xác thực OTP sẽ được gửi tới địa chỉ này.</FieldDescription>
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

          <Field>
            <FieldLabel htmlFor="dk-nhap-lai-mat-khau">Nhập lại mật khẩu</FieldLabel>
            <Input
              id="dk-nhap-lai-mat-khau"
              type="password"
              autoComplete="new-password"
              placeholder="Nhập lại mật khẩu vừa tạo"
              {...form.register('confirmPassword')}
            />
            <FieldError errors={[form.formState.errors.confirmPassword]} />
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

          <Button type="submit" size="lg" className="w-full mt-1" disabled={ketQuaOtp.isLoading}>
            {ketQuaOtp.isLoading ? 'Đang gửi mã OTP…' : 'Tiếp tục & Nhận mã xác thực'}
          </Button>
        </form>
      ) : (
        /* BƯỚC 2: NHẬP MÃ OTP 6 CHỮ SỐ */
        <form onSubmit={xuLyHoanTatDangKy} className="flex flex-col gap-5">
          <div className="flex flex-col items-center gap-2 p-4 bg-muted/30 border rounded-xl text-center">
            <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Mail className="size-5" />
            </div>
            <span className="text-sm font-medium">Nhập 6 số được gửi qua email</span>
            <span className="text-xs text-muted-foreground">
              Vui lòng kiểm tra cả hộp thư chính và thư rác (Spam)
            </span>
          </div>

          {loiOtp && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{loiOtp}</AlertDescription>
            </Alert>
          )}

          {/* 6 ô nhập mã OTP */}
          <div className="flex items-center justify-center gap-2.5 my-2" onPaste={xuLyPasteOtp}>
            {otp.map((so, idx) => (
              <input
                key={idx}
                id={`otp-input-${idx}`}
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

          <div className="flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={() => datBuoc(1)}
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="size-3.5" />
              Đổi email
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
            disabled={ketQuaDangKy.isLoading || otp.join('').length < 6}
          >
            {ketQuaDangKy.isLoading ? 'Đang tạo doanh nghiệp…' : 'Xác nhận & Hoàn tất đăng ký'}
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}

