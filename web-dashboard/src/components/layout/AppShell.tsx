import { Bell, ChevronRight, Moon, Search, Sun } from 'lucide-react'
import { Outlet, useLocation } from 'react-router-dom'

import { AppSidebar } from '@/components/layout/AppSidebar'
import { ChiBaoThoiGianThuc } from '@/components/layout/ChiBaoThoiGianThuc'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { useCheDo } from '@/hooks/useCheDo'
import { useKetNoiThoiGianThuc } from '@/hooks/useThoiGianThuc'

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

  // Vòng đời của khung ứng dụng chính là vòng đời cần có của socket: dựng khi đã đăng nhập,
  // tháo khi đăng xuất.
  useKetNoiThoiGianThuc()

  const doan = viTri.pathname.split('/').filter(Boolean)

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-3 border-b px-6">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="h-4" />

          <nav aria-label="Đường dẫn phân cấp" className="flex items-center gap-2 text-sm">
            {doan.map((d, i) => (
              <div key={d} className="flex items-center gap-2">
                {i > 0 && <ChevronRight className="text-muted-foreground size-3.5" />}
                <span
                  className={
                    i === doan.length - 1 ? 'font-medium' : 'text-muted-foreground'
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
            className="border-input text-muted-foreground flex h-8 w-[280px] items-center gap-2 rounded-lg border px-2.5 text-sm"
          >
            <Search className="size-3.5 shrink-0" />
            <span className="flex-1 text-left">Tìm khách hàng, hội thoại…</span>
            <kbd className="border-border rounded-sm border px-1.5 text-[11px]">⌘K</kbd>
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
        </header>

        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  )
}
