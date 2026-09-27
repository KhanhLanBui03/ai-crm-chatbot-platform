import { ChevronRight, Moon, Sun } from 'lucide-react'
import { Outlet, useLocation } from 'react-router-dom'

import { useAppSelector } from '@/app/store/hooks'
import { AdminSidebar } from '@/components/layout/AdminSidebar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { useCheDo } from '@/hooks/useCheDo'
import { chuCaiDau } from '@/utils/ten'

const NHAN_DUONG_DAN: Record<string, string> = {
  admin: 'Quản trị nền tảng',
  'tong-quan': 'Tổng quan',
  'phan-tich': 'Phân tích & Báo cáo',
  'doanh-nghiep': 'Quản lý doanh nghiệp',
  'goi-dich-vu': 'Quản lý gói dịch vụ',
  'tai-nguyen-ai': 'Tài nguyên & Chi phí AI',
}

/**
 * Khung layout cho Cổng Quản trị Nền tảng — tương tự AppShell nhưng dùng AdminSidebar
 * và có badge nhận diện "SUPER ADMIN" trên header.
 */
export function AdminShell() {
  const viTri = useLocation()
  const { toi, doiCheDo } = useCheDo()
  const nguoiDung = useAppSelector((s) => s.auth.nguoiDung)

  const doan = viTri.pathname.split('/').filter(Boolean)

  return (
    <SidebarProvider>
      <AdminSidebar />
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

          {/* Badge nhận diện Super Admin */}
          <div className="bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 text-[11px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wide">
            Super Admin
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={doiCheDo}
            aria-label={toi ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
          >
            {toi ? <Sun /> : <Moon />}
          </Button>

          <Separator orientation="vertical" className="h-4" />

          <div className="bg-violet-600 text-white flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold shadow-xs">
            {nguoiDung ? chuCaiDau(nguoiDung.fullName) : 'A'}
          </div>
        </header>

        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  )
}
