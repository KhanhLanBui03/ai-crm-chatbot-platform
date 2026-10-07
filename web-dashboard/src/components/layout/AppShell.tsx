import { useState } from 'react'
import { Bell, Building2, ChevronRight, LogOut, Moon, Search, Settings, Sun, User } from 'lucide-react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { useDangXuatMutation } from '@/api/auth'
import { dangXuat } from '@/app/store/authSlice'
import { useAppDispatch, useAppSelector } from '@/app/store/hooks'
import { AppSidebar } from '@/components/layout/AppSidebar'
import { ChiBaoThoiGianThuc } from '@/components/layout/ChiBaoThoiGianThuc'
import { XacNhanDangXuatDialog } from '@/components/layout/XacNhanDangXuatDialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { useCheDo } from '@/hooks/useCheDo'
import { useKetNoiThoiGianThuc } from '@/hooks/useThoiGianThuc'
import { chuCaiDau } from '@/utils/ten'

/** Nhãn hiển thị cho từng đoạn đường dẫn. Đoạn không có ở đây thì dùng nguyên văn. */
const NHAN_DUONG_DAN: Record<string, string> = {
  'tong-quan': 'Tổng quan',
  'quan-tri': 'Bảng điều khiển quản trị',
  'hop-thu': 'Hộp thư',
  'khach-hang': 'Khách hàng',
  'ban-hang': 'Bán hàng',
  'co-hoi-tiem-nang': 'Cơ hội tiềm năng',
  pheu: 'Phễu bán hàng',
  'hoat-dong': 'Hoạt động',
  'tri-thuc': 'Tri thức',
  'tai-lieu': 'Tài liệu',
  'tim-thu': 'Tìm thử',
  'tien-do': 'Tiến độ nạp',
  'khoang-trong': 'Khoảng trống tri thức',
  'tac-tu-ai': 'Tác tử AI',
  'luot-xu-ly': 'Lượt xử lý',
  'goi-cong-cu': 'Nhật ký gọi công cụ',
  mcp: 'Máy chủ MCP',
  'cong-cu': 'Sổ đăng ký công cụ',
  'hieu-qua-ai': 'Hiệu quả tác tử AI',
  'phan-tich': 'Phân tích',
  'kiem-toan': 'Kiểm toán',
  'nhat-ky': 'Nhật ký kiểm toán',
  'yeu-cau-xoa': 'Yêu cầu xoá dữ liệu',
  'xem-truoc-xoa': 'Xem trước phạm vi xoá',
  'cai-dat': 'Cài đặt',
  'doanh-nghiep': 'Hồ sơ doanh nghiệp',
  'nguoi-dung': 'Người dùng',
  'phan-quyen': 'Phân quyền',
  'thue-bao': 'Thuê bao',
  'han-muc': 'Hạn mức',
  'muc-su-dung': 'Mức sử dụng theo ngày',
  kenh: 'Kênh',
  widget: 'Web Widget',
  phien: 'Phiên đăng nhập',
  'quy-tac-phan-cong': 'Quy tắc phân công',
  'hoi-thoai': 'Hội thoại theo ngày',
  'chu-de': 'Chủ đề hội thoại',
  'bao-cao': 'Tệp báo cáo',
}

/**
 * Khung ứng dụng — sidebar 16rem + thanh trên 56px, mỗi route chỉ dựng phần nội dung.
 * Đây là bản chuyển từ artboard "Khung ứng dụng" ở canvas Hệ thống thiết kế.
 */
export function AppShell() {
  const viTri = useLocation()
  const { toi, doiCheDo } = useCheDo()
  const nguoiDung = useAppSelector((s) => s.auth.nguoiDung)
  const dispatch = useAppDispatch()
  const dieuHuong = useNavigate()
  const [hienXacNhan, datHienXacNhan] = useState(false)
  const [guiDangXuat, { isLoading: dangDangXuat }] = useDangXuatMutation()

  async function xuLyDangXuat() {
    try {
      await guiDangXuat().unwrap()
    } catch {
      // Bỏ qua lỗi mạng
    } finally {
      dispatch(dangXuat())
      toast.success('Đã đăng xuất thành công')
      dieuHuong('/dang-nhap', { replace: true })
    }
  }

  // Vòng đời của khung ứng dụng chính là vòng đời cần có của socket: dựng khi đã đăng nhập,
  // tháo khi đăng xuất.
  useKetNoiThoiGianThuc()

  const doan = viTri.pathname.split('/').filter(Boolean)

  return (
    <SidebarProvider>
      <AppSidebar />
      {/* min-w-0: nội dung rộng (bảng phễu 5 cột) không được đẩy cả trang tràn ngang dưới thanh bên */}
      <SidebarInset className="min-w-0">
        <header className="flex h-14 shrink-0 items-center gap-2 sm:gap-3 border-b px-3 sm:px-6">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="h-4 hidden sm:block" />

          <nav aria-label="Đường dẫn phân cấp" className="hidden sm:flex items-center gap-2 text-sm max-w-[200px] lg:max-w-none overflow-hidden">
            {doan.map((d, i) => (
              <div key={d} className="flex items-center gap-2 truncate">
                {i > 0 && <ChevronRight className="text-muted-foreground size-3.5 shrink-0" />}
                <span
                  className={
                    i === doan.length - 1 ? 'font-medium truncate' : 'text-muted-foreground truncate'
                  }
                >
                  {NHAN_DUONG_DAN[d] ?? d}
                </span>
              </div>
            ))}
          </nav>

          <div className="flex-1" />

          <button
            type="button"
            className="border-input text-muted-foreground hidden md:flex h-8 w-[220px] lg:w-[280px] items-center gap-2 rounded-lg border px-2.5 text-sm"
          >
            <Search className="size-3.5 shrink-0" />
            <span className="flex-1 text-left truncate">Tìm khách hàng, hội thoại…</span>
            <kbd className="border-border rounded-sm border px-1.5 text-[11px] shrink-0">⌘K</kbd>
          </button>

          <ChiBaoThoiGianThuc />

          <Button
            variant="ghost"
            size="icon"
            onClick={doiCheDo}
            aria-label={toi ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
          >
            {toi ? <Sun /> : <Moon />}
          </Button>

          <Button variant="ghost" size="icon" aria-label="Thông báo" className="relative">
            <Bell />
            <span className="bg-destructive ring-background absolute top-1.5 right-1.5 size-[7px] rounded-full ring-2" />
          </Button>

          <Separator orientation="vertical" className="h-4" />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex items-center gap-2 rounded-full p-0.5 outline-none focus-visible:ring-2 focus-visible:ring-ring hover:opacity-85 transition-opacity cursor-pointer"
                aria-label="Tài khoản người dùng"
              >
                <div className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold shadow-xs">
                  {nguoiDung ? chuCaiDau(nguoiDung.fullName) : 'U'}
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" side="bottom" className="w-56 mt-1">
              <DropdownMenuLabel className="flex flex-col gap-0.5">
                <span className="font-semibold text-foreground text-sm truncate">{nguoiDung?.fullName ?? 'Người dùng'}</span>
                <span className="text-xs text-muted-foreground font-normal truncate">{nguoiDung?.email}</span>
                {nguoiDung?.tenantName && (
                  <span className="text-[11px] text-primary font-medium truncate mt-0.5">{nguoiDung.tenantName}</span>
                )}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => dieuHuong('/cai-dat/nguoi-dung')}>
                <User className="mr-2 size-4" />
                <span>Hồ sơ cá nhân</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => dieuHuong('/cai-dat/doanh-nghiep')}>
                <Building2 className="mr-2 size-4" />
                <span>Hồ sơ doanh nghiệp</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => dieuHuong('/cai-dat')}>
                <Settings className="mr-2 size-4" />
                <span>Cài đặt</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onClick={() => datHienXacNhan(true)}
                className="cursor-pointer"
              >
                <LogOut className="mr-2 size-4" />
                <span>Đăng xuất</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <Outlet />

        <XacNhanDangXuatDialog
          open={hienXacNhan}
          onOpenChange={datHienXacNhan}
          onConfirm={xuLyDangXuat}
          isLoading={dangDangXuat}
        />
      </SidebarInset>
    </SidebarProvider>
  )
}
