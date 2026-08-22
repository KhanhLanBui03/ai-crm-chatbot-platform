import {
  BarChart3,
  BookOpen,
  ChevronDown,
  Inbox,
  LayoutDashboard,
  ScrollText,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'

import { Progress } from '@/components/ui/progress'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import { useAppSelector } from '@/app/store/hooks'
import { useDanhSachGoiCongCuQuery } from '@/api/ai-agent'
import { chuCaiDau, vietTatDoanhNghiep } from '@/utils/ten'

/**
 * Tám mục điều hướng phủ hết 58 màn hình — xem artboard "Khung ứng dụng" ở canvas
 * Hệ thống thiết kế. Quản trị hệ thống (A04) nằm ở khu riêng, đăng nhập riêng.
 */
const MUC_CHINH = [
  { duongDan: '/tong-quan', nhan: 'Tổng quan', BieuTuong: LayoutDashboard },
  { duongDan: '/hop-thu', nhan: 'Hộp thư', BieuTuong: Inbox, huyHieu: '12' },
  { duongDan: '/khach-hang', nhan: 'Khách hàng', BieuTuong: Users },
] as const

/**
 * SCR006 — chỉ hiện với người quản trị doanh nghiệp.
 *
 * Nhân viên vào cũng đọc được đúng bộ số ấy ở "Tổng quan" (SCR048); mục này tồn tại vì người
 * quản trị cần một trang mở đầu ngày ưu tiên việc phải xử lý, không phải vì họ được xem thêm gì.
 */
const MUC_QUAN_TRI = {
  duongDan: '/quan-tri',
  nhan: 'Bảng điều khiển quản trị',
  BieuTuong: ShieldCheck,
} as const

const MUC_BAN_HANG = [
  { duongDan: '/ban-hang/co-hoi-tiem-nang', nhan: 'Cơ hội tiềm năng' },
  { duongDan: '/ban-hang/pheu', nhan: 'Phễu bán hàng' },
  { duongDan: '/ban-hang/hoat-dong', nhan: 'Hoạt động' },
] as const

const MUC_TRI_THUC = [
  { duongDan: '/tri-thuc', nhan: 'Tài liệu' },
  { duongDan: '/tri-thuc/tim-thu', nhan: 'Tìm thử' },
  { duongDan: '/tri-thuc/tien-do', nhan: 'Tiến độ nạp' },
  { duongDan: '/tri-thuc/khoang-trong', nhan: 'Khoảng trống' },
] as const

const MUC_TAC_TU = [
  { duongDan: '/tac-tu-ai/luot-xu-ly', nhan: 'Lượt xử lý' },
  { duongDan: '/tac-tu-ai/goi-cong-cu', nhan: 'Nhật ký gọi công cụ' },
  { duongDan: '/tac-tu-ai/mcp', nhan: 'Máy chủ MCP' },
  { duongDan: '/tac-tu-ai/cong-cu', nhan: 'Sổ đăng ký công cụ' },
] as const

/**
 * Kiểm toán gom riêng chứ không nhét vào Cài đặt.
 *
 * Đây là phần Nghị định 13/2023/NĐ-CP của hệ thống: nhật ký không sửa được và quyền xoá dữ liệu
 * cá nhân là nghĩa vụ pháp lý, không phải một tuỳ chọn cấu hình.
 */
const MUC_KIEM_TOAN = [
  { duongDan: '/kiem-toan/nhat-ky', nhan: 'Nhật ký kiểm toán' },
  { duongDan: '/kiem-toan/yeu-cau-xoa', nhan: 'Yêu cầu xoá dữ liệu' },
  { duongDan: '/kiem-toan/xem-truoc-xoa', nhan: 'Xem trước phạm vi xoá' },
] as const

const MUC_PHAN_TICH = [
  { duongDan: '/phan-tich/hoi-thoai', nhan: 'Hội thoại theo ngày' },
  { duongDan: '/phan-tich/pheu', nhan: 'Phễu chuyển đổi' },
  { duongDan: '/phan-tich/chu-de', nhan: 'Chủ đề hội thoại' },
  { duongDan: '/phan-tich/hieu-qua-ai', nhan: 'Hiệu quả tác tử AI' },
  { duongDan: '/phan-tich/bao-cao', nhan: 'Tệp báo cáo' },
] as const

export function AppSidebar() {
  const nguoiDung = useAppSelector((s) => s.auth.nguoiDung)
  const viTri = useLocation()
  const moBanHang = viTri.pathname.startsWith('/ban-hang')
  const moPhanTich = viTri.pathname.startsWith('/phan-tich')
  const moTriThuc = viTri.pathname.startsWith('/tri-thuc')
  const moTacTu = viTri.pathname.startsWith('/tac-tu-ai')
  const moKiemToan = viTri.pathname.startsWith('/kiem-toan')

  // Số lời gọi công cụ đang chờ duyệt lấy thẳng từ cache RTK Query — cùng truy vấn với SCR035,
  // nên mở thanh bên không tốn thêm một lượt gọi mạng nào.
  const soChoDuyet =
    useDanhSachGoiCongCuQuery({ trangThaiDuyet: 'PENDING' }).data?.totalItems ?? 0

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center gap-2.5 px-1 py-1">
          <div className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-md text-sm font-semibold">
            {nguoiDung ? vietTatDoanhNghiep(nguoiDung.tenantName) : '—'}
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm leading-tight font-semibold">
              {nguoiDung?.tenantName ?? 'Doanh nghiệp'}
            </span>
            <span className="text-muted-foreground truncate text-xs">
              Gói {nguoiDung?.planName ?? '—'}
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {MUC_CHINH.map(({ duongDan, nhan, BieuTuong, ...rest }) => (
                <SidebarMenuItem key={duongDan}>
                  <SidebarMenuButton asChild isActive={viTri.pathname.startsWith(duongDan)}>
                    <NavLink to={duongDan}>
                      <BieuTuong />
                      <span>{nhan}</span>
                    </NavLink>
                  </SidebarMenuButton>
                  {'huyHieu' in rest && rest.huyHieu ? (
                    <SidebarMenuBadge>{rest.huyHieu}</SidebarMenuBadge>
                  ) : null}
                </SidebarMenuItem>
              ))}

              {nguoiDung?.roleCode === 'TENANT_ADMIN' && (
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={viTri.pathname.startsWith(MUC_QUAN_TRI.duongDan)}
                  >
                    <NavLink to={MUC_QUAN_TRI.duongDan}>
                      <MUC_QUAN_TRI.BieuTuong />
                      <span>{MUC_QUAN_TRI.nhan}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}

              <SidebarMenuItem>
                <SidebarMenuButton isActive={moBanHang}>
                  <TrendingUp />
                  <span>Bán hàng</span>
                  <ChevronDown className="ml-auto" />
                </SidebarMenuButton>
                <SidebarMenuSub>
                  {MUC_BAN_HANG.map(({ duongDan, nhan }) => (
                    <SidebarMenuSubItem key={duongDan}>
                      <SidebarMenuSubButton asChild isActive={viTri.pathname === duongDan}>
                        <NavLink to={duongDan}>{nhan}</NavLink>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton isActive={moTriThuc}>
                  <BookOpen />
                  <span>Tri thức</span>
                  <ChevronDown className="ml-auto" />
                </SidebarMenuButton>
                <SidebarMenuSub>
                  {MUC_TRI_THUC.map(({ duongDan, nhan }) => (
                    <SidebarMenuSubItem key={duongDan}>
                      <SidebarMenuSubButton asChild isActive={viTri.pathname === duongDan}>
                        <NavLink to={duongDan}>{nhan}</NavLink>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton isActive={moTacTu}>
                  <Sparkles />
                  <span>Tác tử AI</span>
                  <ChevronDown className="ml-auto" />
                </SidebarMenuButton>
                {/* Huy hiệu là số lời gọi công cụ đang chờ duyệt — tác tử dừng lại tới khi có người bấm */}
                {soChoDuyet > 0 && <SidebarMenuBadge>{soChoDuyet}</SidebarMenuBadge>}
                <SidebarMenuSub>
                  {MUC_TAC_TU.map(({ duongDan, nhan }) => (
                    <SidebarMenuSubItem key={duongDan}>
                      <SidebarMenuSubButton asChild isActive={viTri.pathname === duongDan}>
                        <NavLink to={duongDan}>{nhan}</NavLink>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton isActive={moPhanTich}>
                  <BarChart3 />
                  <span>Phân tích</span>
                  <ChevronDown className="ml-auto" />
                </SidebarMenuButton>
                <SidebarMenuSub>
                  {MUC_PHAN_TICH.map(({ duongDan, nhan }) => (
                    <SidebarMenuSubItem key={duongDan}>
                      <SidebarMenuSubButton asChild isActive={viTri.pathname === duongDan}>
                        <NavLink to={duongDan}>{nhan}</NavLink>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton isActive={moKiemToan}>
                  <ScrollText />
                  <span>Kiểm toán</span>
                  <ChevronDown className="ml-auto" />
                </SidebarMenuButton>
                <SidebarMenuSub>
                  {MUC_KIEM_TOAN.map(({ duongDan, nhan }) => (
                    <SidebarMenuSubItem key={duongDan}>
                      <SidebarMenuSubButton asChild isActive={viTri.pathname === duongDan}>
                        <NavLink to={duongDan}>{nhan}</NavLink>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              </SidebarMenuItem>

              <SidebarSeparator />

              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={viTri.pathname.startsWith('/cai-dat')}>
                  <NavLink to="/cai-dat">
                    <Settings />
                    <span>Cài đặt</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        {/* Hạn mức là nhắc thường trực — UC006 chặn trả lời tự động khi chạm trần */}
        <div className="bg-card ring-foreground/10 flex flex-col gap-2 rounded-lg p-3 ring-1">
          <div className="flex items-baseline justify-between">
            <span className="text-xs font-medium">Hạn mức hội thoại</span>
            <span className="text-muted-foreground text-xs tabular-nums">1.842/2.000</span>
          </div>
          <Progress value={92} className="h-1.5" />
          <span className="text-warning text-xs">Còn 158 lượt trong chu kỳ này</span>
        </div>

        <div className="flex items-center gap-2 rounded-lg p-2">
          <div className="bg-secondary text-secondary-foreground flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium">
            {nguoiDung ? chuCaiDau(nguoiDung.fullName) : '—'}
          </div>
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-[13px] leading-tight font-medium">
              {nguoiDung?.fullName ?? 'Chưa đăng nhập'}
            </span>
            <span className="text-muted-foreground text-xs">
              {nguoiDung?.roleCode === 'TENANT_ADMIN' ? 'Quản trị viên' : 'Nhân viên'}
            </span>
          </div>
          <ChevronDown className="text-muted-foreground size-3.5 shrink-0" />
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
