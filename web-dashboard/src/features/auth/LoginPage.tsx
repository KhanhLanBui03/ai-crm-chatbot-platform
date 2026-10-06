import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useDangNhapMutation } from '@/api/auth'
import { laLoiTruyVan } from '@/api/baseQuery'
import { dangNhap } from '@/app/store/authSlice'
import { useAppDispatch } from '@/app/store/hooks'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuthLayout } from '@/features/auth/AuthLayout'

const KHOA_GHI_NHO_TRANG_THAI = 'auth_ghi_nho_dang_nhap'
const KHOA_GHI_NHO_EMAIL = 'auth_ghi_nho_email'

/** SCR003 — bản chuyển từ artboard "Đăng nhập" ở canvas Nền tảng và tài khoản. */
export function LoginPage() {
  const [ghiNho, datGhiNho] = useState<boolean>(() => {
    try {
      // Dọn dẹp key mật khẩu cũ nếu còn sót từ phiên trước
      localStorage.removeItem('auth_ghi_nho_mat_khau')
      return localStorage.getItem(KHOA_GHI_NHO_TRANG_THAI) === 'true'
    } catch {
      return false
    }
  })
  const [email, datEmail] = useState(() => {
    try {
      return localStorage.getItem(KHOA_GHI_NHO_EMAIL) || ''
    } catch {
      return ''
    }
  })
  const [matKhau, datMatKhau] = useState('')
  const dispatch = useAppDispatch()
  const dieuHuong = useNavigate()
  const viTri = useLocation()

  const [guiDangNhap, ketQua] = useDangNhapMutation()

  async function xuLyGui(su: React.FormEvent) {
    su.preventDefault()
    try {
      // `.unwrap()` ném lỗi ra thay vì trả về nhánh `{ error }` — nhờ vậy hai việc phải làm khi
      // thành công (lưu phiên rồi điều hướng) nằm gọn trong luồng thẳng bên dưới.
      const kq = await guiDangNhap({ email, password: matKhau }).unwrap()

      // Xử lý ghi nhớ đăng nhập (chỉ lưu email và trạng thái, tuyệt đối không lưu plaintext password)
      try {
        localStorage.removeItem('auth_ghi_nho_mat_khau')
        if (ghiNho) {
          localStorage.setItem(KHOA_GHI_NHO_TRANG_THAI, 'true')
          localStorage.setItem(KHOA_GHI_NHO_EMAIL, email)
        } else {
          localStorage.removeItem(KHOA_GHI_NHO_TRANG_THAI)
          localStorage.removeItem(KHOA_GHI_NHO_EMAIL)
        }
      } catch {
        // Tránh gián đoạn nếu môi trường chặn localStorage
      }

      dispatch(dangNhap({ accessToken: kq.accessToken, nguoiDung: kq.nguoiDung }))
      const laAdmin =
        kq.nguoiDung.roleCode === 'PLATFORM_ADMIN' || kq.nguoiDung.scope === 'PLATFORM'
      const tu = (viTri.state as { tu?: string } | null)?.tu
      const dichDen = laAdmin
        ? (tu && tu.startsWith('/admin') ? tu : '/admin/tong-quan')
        : (tu && !tu.startsWith('/admin') ? tu : '/hop-thu')
      dieuHuong(dichDen, { replace: true })
    } catch {
      // Lỗi đã nằm trong `ketQua.error`, phần hiển thị bên dưới đọc từ đó
    }
  }

  return (
    <AuthLayout
      tieuDe="Đăng nhập"
      phuDe={
        <>
          Chưa có tài khoản?{' '}
          <Link to="/dang-ky" className="text-primary hover:underline">
            Đăng ký doanh nghiệp
          </Link>
        </>
      }
      chanTrang="Phiên đăng nhập ghi lại địa chỉ IP và trình duyệt để bạn tự thu hồi được ở mục Bảo mật."
    >
      <form className="flex flex-col gap-4" onSubmit={xuLyGui} noValidate>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">Email công việc</Label>
          <Input
            id="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => datEmail(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between">
            <Label htmlFor="mat-khau">Mật khẩu</Label>
          </div>
          <Input
            id="mat-khau"
            type="password"
            autoComplete="current-password"
            value={matKhau}
            onChange={(e) => datMatKhau(e.target.value)}
            aria-invalid={ketQua.isError}
          />
          {ketQua.isError && (
            <span className="text-destructive text-xs leading-relaxed">
              {laLoiTruyVan(ketQua.error)
                ? ketQua.error.message
                : 'Không đăng nhập được. Thử lại sau ít phút.'}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between pt-0.5">
          <div className="flex items-center gap-2">
            <Checkbox
              id="ghi-nho-tai-khoan"
              checked={ghiNho}
              onCheckedChange={(checked) => datGhiNho(checked === true)}
            />
            <Label
              htmlFor="ghi-nho-tai-khoan"
              className="text-xs font-normal text-muted-foreground cursor-pointer select-none leading-none"
            >
              Ghi nhớ tài khoản
            </Label>
          </div>
          <Link to="/quen-mat-khau" className="text-primary text-[13px] hover:underline">
            Quên mật khẩu?
          </Link>
        </div>

        <Button type="submit" size="lg" className="w-full mt-1" disabled={ketQua.isLoading}>
          {ketQua.isLoading ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </Button>
      </form>
    </AuthLayout>
  )
}
