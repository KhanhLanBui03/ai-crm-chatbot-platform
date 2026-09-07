import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'

import { useGuiLaiThuXacThucMutation, useXacThucThuMutation } from '@/api/auth'
import { laLoiTruyVan } from '@/api/baseQuery'
import { StatusPage, type TrangThaiTrang } from '@/components/layout/StatusPage'

/**
 * SCR002 — xác thực địa chỉ thư. Mẫu M6, ngoài phạm vi đăng nhập.
 *
 * Hai đường vào cùng một màn:
 *
 * - **Có `?token=`** — người dùng vừa bấm liên kết trong thư. Xác thực chạy ngay, không có nút
 *   nào để bấm; bắt họ bấm thêm một lần nữa sau khi đã bấm liên kết là thêm một bước vô nghĩa.
 * - **Không có token** — vừa đăng ký xong. Đây là trạng thái `cho-thao-tac`, **không phải**
 *   `thanh-cong`: "đã gửi thư" mà hiện dấu tích xanh thì người dùng đóng tab rồi không bao giờ
 *   mở hộp thư ra xác thực.
 */
export function VerifyEmailPage() {
  const [thamSo] = useSearchParams()
  const dieuHuong = useNavigate()
  const token = thamSo.get('token')
  const email = thamSo.get('email')

  const [xacThuc, ketQua] = useXacThucThuMutation()
  const [guiLai, ketQuaGuiLai] = useGuiLaiThuXacThucMutation()

  // React 19 ở chế độ nghiêm ngặt gọi effect hai lần khi dựng; cờ này giữ cho lời gọi xác thực
  // chỉ chạy một lần, vì token dùng một lần và lần thứ hai sẽ trả về 410.
  const daChay = useRef(false)
  useEffect(() => {
    if (!token || daChay.current) return
    daChay.current = true
    xacThuc({ token })
  }, [token, xacThuc])

  const trangThai: TrangThaiTrang = !token
    ? 'cho-thao-tac'
    : ketQua.isSuccess
      ? 'thanh-cong'
      : ketQua.isError
        ? 'that-bai'
        : 'dang-xu-ly'

  const thongDiepLoi = laLoiTruyVan(ketQua.error) ? ketQua.error.message : null

  const noiDung: Record<TrangThaiTrang, { tieuDe: string; moTa: string }> = {
    'cho-thao-tac': {
      tieuDe: 'Kiểm tra hộp thư của bạn',
      moTa: email
        ? `Chúng tôi vừa gửi liên kết xác thực tới ${email}. Mở thư và bấm vào liên kết để kích hoạt tài khoản — liên kết có hiệu lực 24 giờ.`
        : 'Mở thư và bấm vào liên kết để kích hoạt tài khoản. Liên kết có hiệu lực 24 giờ.',
    },
    'dang-xu-ly': {
      tieuDe: 'Đang xác thực địa chỉ thư…',
      moTa: 'Chỉ mất vài giây. Đừng đóng tab này.',
    },
    'thanh-cong': {
      tieuDe: 'Đã xác thực địa chỉ thư',
      moTa: 'Tài khoản quản trị của doanh nghiệp đã kích hoạt. Đăng nhập để bắt đầu nối kênh và tải tài liệu lên kho tri thức.',
    },
    'that-bai': {
      tieuDe: 'Không xác thực được',
      moTa: thongDiepLoi ?? 'Liên kết xác thực đã hết hạn hoặc đã được dùng.',
    },
  }

  return (
    <StatusPage
      toanManHinh
      trangThai={trangThai}
      tieuDe={noiDung[trangThai].tieuDe}
      moTa={noiDung[trangThai].moTa}
      thaoTacChinh={
        trangThai === 'thanh-cong'
          ? { nhan: 'Đăng nhập', onClick: () => dieuHuong('/dang-nhap', { replace: true }) }
          : trangThai === 'dang-xu-ly'
            ? undefined
            : {
                nhan: ketQuaGuiLai.isLoading ? 'Đang gửi lại…' : 'Gửi lại thư xác thực',
                onClick: async () => {
                  if (!email) {
                    toast.error('Không rõ địa chỉ thư. Đăng ký lại hoặc liên hệ hỗ trợ.')
                    return
                  }
                  await guiLai({ email }).unwrap()
                  toast.success('Đã gửi lại thư xác thực. Kiểm tra cả mục thư rác.')
                },
              }
      }
      thaoTacPhu={
        trangThai === 'dang-xu-ly'
          ? undefined
          : { nhan: 'Về trang đăng nhập', onClick: () => dieuHuong('/dang-nhap') }
      }
    />
  )
}
