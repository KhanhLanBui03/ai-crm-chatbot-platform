import { Check, Eye, Minus, Pencil } from 'lucide-react'

import { useDanhSachVaiTroQuery } from '@/api/platform'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { StatusChip } from '@/components/ui/status-chip'
import { cn } from '@/utils/cn'

/** Nhóm chức năng → nhãn tiếng Việt. Khoá lấy đúng từ `roles.permissions` (jsonb) của ERD. */
const NHAN_NHOM: Record<string, string> = {
  conversations: 'Hội thoại',
  contacts: 'Khách hàng',
  knowledge: 'Tri thức',
  sales: 'Bán hàng',
  analytics: 'Phân tích',
  settings: 'Cấu hình',
  audit: 'Kiểm toán',
  billing: 'Gói và hoá đơn',
}

const MUC: Record<string, { nhan: string; BieuTuong: typeof Check; mau: string }> = {
  FULL: { nhan: 'Toàn quyền', BieuTuong: Check, mau: 'text-chart-2' },
  READ_WRITE: { nhan: 'Xem và sửa', BieuTuong: Pencil, mau: 'text-chart-1' },
  READ: { nhan: 'Chỉ xem', BieuTuong: Eye, mau: 'text-muted-foreground' },
  NONE: { nhan: 'Không có quyền', BieuTuong: Minus, mau: 'text-muted-foreground/50' },
}

/**
 * SCR010 — ma trận phân quyền.
 *
 * **Chỉ đọc, và cố ý như vậy.** Đặc tả SCR010 ban đầu nêu bốn vai trò (Admin/Manager/Agent/Sales)
 * nhưng `platform.roles` của ERD chỉ có hai. Chỗ lệch này đã chốt theo ERD (ADR-0011): màn hình
 * hiển thị đúng `roles.permissions` dạng jsonb, thay vì bốn vai trò cứng không tồn tại trong cơ
 * sở dữ liệu.
 *
 * Sửa được ma trận thì phải sửa cả cách máy chủ đọc quyền, nên nó là việc của một phiên bản sau.
 */
export function RolesPage() {
  const { data: vaiTro, isLoading } = useDanhSachVaiTroQuery()

  if (isLoading || !vaiTro) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-64 w-full max-w-3xl" />
      </div>
    )
  }

  const nhom = Object.keys(vaiTro[0]?.permissions ?? {})

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="flex max-w-3xl flex-col gap-5 p-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-semibold tracking-tight">Phân quyền</h1>
          <p className="text-muted-foreground text-[13px]">
            Quyền gắn với vai trò, không gắn với từng người. Đổi vai trò của một người ở màn
            Người dùng.
          </p>
        </div>

        <Alert>
          <AlertDescription>
            Hệ thống có <strong>hai</strong> vai trò. Máy chủ luôn là nơi quyết định — giao diện ẩn
            hay hiện gì chỉ để gọn mắt, không phải để bảo mật.
          </AlertDescription>
        </Alert>

        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-40">Nhóm chức năng</TableHead>
                {vaiTro.map((v) => (
                  <TableHead key={v.code}>
                    <div className="flex flex-col gap-0.5 py-1">
                      <span className="text-foreground font-medium">{v.name}</span>
                      <span className="text-muted-foreground text-xs font-normal">
                        {v.userCount ?? 0} người
                      </span>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {nhom.map((k) => (
                <TableRow key={k}>
                  <TableCell className="font-medium">{NHAN_NHOM[k] ?? k}</TableCell>
                  {vaiTro.map((v) => {
                    const m = MUC[v.permissions[k]] ?? MUC.NONE
                    return (
                      <TableCell key={v.code}>
                        <span className={cn('flex items-center gap-1.5 text-[13px]', m.mau)}>
                          <m.BieuTuong className="size-3.5" />
                          {m.nhan}
                        </span>
                      </TableCell>
                    )
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <div className="flex flex-col gap-2">
          {vaiTro.map((v) => (
            <div key={v.code} className="flex items-start gap-2.5">
              <StatusChip sacThai={v.code === 'TENANT_ADMIN' ? 'info' : 'neutral'}>
                {v.name}
              </StatusChip>
              <span className="text-muted-foreground flex-1 text-[13px] leading-relaxed">
                {v.description}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
