import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useDangNhapMutation } from '@/api/auth'
import { laLoiTruyVan } from '@/api/baseQuery'
import { dangNhap } from '@/app/store/authSlice'
import { useAppDispatch } from '@/app/store/hooks'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuthLayout } from '@/features/auth/AuthLayout'

/** SCR003 — bản chuyển từ artboard "Đăng nhập" ở canvas Nền tảng và tài khoản. */
export function LoginPage() {
  const [email, datEmail] = useState('an.pham@cattuong.vn')
  const [matKhau, datMatKhau] = useState('matkhau-mau')
  const dispatch = useAppDispatch()
  const dieuHuong = useNavigate()
  const viTri = useLocation()
  const dich = (viTri.state as { tu?: string } | null)?.tu ?? '/hop-thu'

  const [guiDangNhap, ketQua] = useDangNhapMutation()

  async function xuLyGui(su: React.FormEvent) {
    su.preventDefault()
    try {
      // `.unwrap()` ném lỗi ra thay vì trả về nhánh `{ error }` — nhờ vậy hai việc phải làm khi
      // thành công (lưu phiên rồi điều hướng) nằm gọn trong luồng thẳng bên dưới.
      const kq = await guiDangNhap({ email, password: matKhau }).unwrap()
      dispatch(dangNhap({ accessToken: kq.accessToken, nguoiDung: kq.nguoiDung }))
      dieuHuong(dich, { replace: true })
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
            <Link to="/quen-mat-khau" className="text-primary text-[13px] hover:underline">
              Quên mật khẩu?
            </Link>
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

        <Button type="submit" size="lg" className="w-full" disabled={ketQua.isLoading}>
          {ketQua.isLoading ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </Button>
      </form>
    </AuthLayout>
  )
}
