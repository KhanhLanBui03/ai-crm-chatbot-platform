import { useState } from 'react'
import {
  BarChart3,
  Building2,
  ChevronDown,
  CreditCard,
  LayoutDashboard,
  LogOut,
  Sparkles,
} from 'lucide-react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { useDangXuatMutation } from '@/api/auth'
import { dangXuat } from '@/app/store/authSlice'
import { useAppDispatch, useAppSelector } from '@/app/store/hooks'
import { XacNhanDangXuatDialog } from '@/components/layout/XacNhanDangXuatDialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { chuCaiDau } from '@/utils/ten'

const MUC_ADMIN = [
  { duongDan: '/admin/tong-quan', nhan: 'Tổng quan nền tảng', BieuTuong: LayoutDashboard },
  { duongDan: '/admin/phan-tich', nhan: 'Phân tích & Báo cáo', BieuTuong: BarChart3 },
  { duongDan: '/admin/doanh-nghiep', nhan: 'Quản lý doanh nghiệp', BieuTuong: Building2 },
  { duongDan: '/admin/goi-dich-vu', nhan: 'Quản lý gói dịch vụ', BieuTuong: CreditCard },
  { duongDan: '/admin/tai-nguyen-ai', nhan: 'Tài nguyên & Chi phí AI', BieuTuong: Sparkles },
] as const

export function AdminSidebar() {
  const nguoiDung = useAppSelector((s) => s.auth.nguoiDung)
  const viTri = useLocation()
  const dieuHuong = useNavigate()
  const dispatch = useAppDispatch()
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

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2.5 px-1 py-1 group-data-[collapsible=icon]:justify-center">
          <div className="bg-gradient-to-br from-violet-600 to-fuchsia-500 text-white flex size-8 shrink-0 items-center justify-center rounded-md text-xs font-bold shadow-md">
            SA
          </div>
          <div className="flex min-w-0 flex-col group-data-[collapsible=icon]:hidden">
            <span className="truncate text-sm leading-tight font-semibold">
              CRM AI Platform
            </span>
            <span className="text-xs font-medium text-violet-600 dark:text-violet-400">
              Super Admin
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 group-data-[collapsible=icon]:hidden">
            Quản trị hệ thống
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {MUC_ADMIN.map(({ duongDan, nhan, BieuTuong }) => (
                <SidebarMenuItem key={duongDan}>
                  <SidebarMenuButton asChild isActive={viTri.pathname.startsWith(duongDan)} tooltip={nhan}>
                    <NavLink to={duongDan}>
                      <BieuTuong />
                      <span>{nhan}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="hover:bg-accent/50 flex w-full items-center gap-2 rounded-lg p-2 text-left transition-colors cursor-pointer outline-none focus-visible:ring-1 focus-visible:ring-ring group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-1"
            >
              <div className="bg-violet-600 text-white flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium">
                {nguoiDung ? chuCaiDau(nguoiDung.fullName) : '—'}
              </div>
              <div className="flex min-w-0 flex-1 flex-col group-data-[collapsible=icon]:hidden">
                <span className="truncate text-[13px] leading-tight font-medium">
                  {nguoiDung?.fullName ?? 'Chưa đăng nhập'}
                </span>
                <span className="text-muted-foreground text-xs">
                  Quản trị viên nền tảng
                </span>
              </div>
              <ChevronDown className="text-muted-foreground size-3.5 shrink-0 group-data-[collapsible=icon]:hidden" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" side="top" className="w-56 mb-1">
            <DropdownMenuLabel className="flex flex-col gap-0.5">
              <span className="font-semibold text-foreground text-sm truncate">
                {nguoiDung?.fullName}
              </span>
              <span className="text-xs text-muted-foreground font-normal truncate">
                {nguoiDung?.email}
              </span>
            </DropdownMenuLabel>
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

        <XacNhanDangXuatDialog
          open={hienXacNhan}
          onOpenChange={datHienXacNhan}
          onConfirm={xuLyDangXuat}
          isLoading={dangDangXuat}
        />
      </SidebarFooter>
    </Sidebar>
  )
}
