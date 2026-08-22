import type { SortingState } from '@tanstack/react-table'
import { formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { AlertTriangle, Mail, UserPlus, Users } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import {
  useDanhSachNguoiDungQuery,
  useGuiLaiLoiMoiMutation,
  type BoLocNguoiDung,
} from '@/api/platform'
import { ListPage } from '@/components/layout/ListPage'
import { Button } from '@/components/ui/button'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { InviteUserDialog } from '@/features/settings/InviteUserDialog'
import type { NguoiDung, TrangThaiNguoiDung } from '@/types/schema'
import { chuCaiDau } from '@/utils/ten'

const NHAN_TRANG_THAI: Record<
  TrangThaiNguoiDung,
  { nhan: string; sacThai: 'success' | 'warning' | 'neutral' }
> = {
  ACTIVE: { nhan: 'Đang hoạt động', sacThai: 'success' },
  PENDING: { nhan: 'Chờ kích hoạt', sacThai: 'warning' },
  DISABLED: { nhan: 'Đã vô hiệu hoá', sacThai: 'neutral' },
}

/** SCR008 — danh sách người dùng. Mẫu M1, cộng hộp thoại mời của SCR009. */
export function UsersPage() {
  const [boLoc, datBoLoc] = useState<BoLocNguoiDung>({ trang: 0 })
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'fullName', desc: false }])
  const [moHopThoai, datMoHopThoai] = useState(false)
  const [guiLaiLoiMoi] = useGuiLaiLoiMoiMutation()

  const truyVan = useDanhSachNguoiDungQuery({
    ...boLoc,
    sapXep: sapXep[0] ? `${sapXep[0].desc ? '-' : ''}${sapXep[0].id}` : undefined,
  })

  const cot = useMemo<CotBang<NguoiDung>[]>(
    () => [
      {
        id: 'fullName',
        accessorKey: 'fullName',
        header: 'Người dùng',
        enableSorting: true,
        cell: ({ row }) => {
          const u = row.original
          return (
            <div className="flex items-center gap-2.5">
              <div className="bg-secondary text-secondary-foreground flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium">
                {chuCaiDau(u.fullName ?? u.email)}
              </div>
              <div className="flex min-w-0 flex-col">
                <span className="truncate font-medium">{u.fullName ?? 'Chưa đặt tên'}</span>
                <span className="text-muted-foreground truncate text-xs">{u.email}</span>
              </div>
            </div>
          )
        },
      },
      {
        id: 'roleName',
        accessorKey: 'roleName',
        header: 'Vai trò',
        cell: ({ row }) => (
          <StatusChip sacThai={row.original.roleCode === 'TENANT_ADMIN' ? 'info' : 'neutral'}>
            {row.original.roleName ?? row.original.roleCode}
          </StatusChip>
        ),
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const t = NHAN_TRANG_THAI[row.original.status]
          return <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
        },
      },
      {
        id: 'assignedConversationCount',
        accessorKey: 'assignedConversationCount',
        header: 'Đang phụ trách',
        enableSorting: true,
        cell: ({ row }) => {
          const u = row.original
          const so = u.assignedConversationCount ?? 0
          // Người đã vô hiệu hoá mà còn hội thoại là hội thoại không ai trả lời. Đây là lý do
          // ERD giữ cột này trên danh sách thay vì để trong trang chi tiết.
          const boRoi = u.status === 'DISABLED' && so > 0
          return (
            <span
              className={
                boRoi ? 'text-destructive flex items-center gap-1 font-medium' : 'tabular-nums'
              }
            >
              {boRoi && <AlertTriangle className="size-3.5" />}
              {so}
            </span>
          )
        },
      },
      {
        id: 'lastLoginAt',
        accessorKey: 'lastLoginAt',
        header: 'Đăng nhập gần nhất',
        enableSorting: true,
        cell: ({ row }) => {
          const luc = row.original.lastLoginAt
          return (
            <span className="text-muted-foreground tabular-nums">
              {luc ? formatDistanceToNowStrict(new Date(luc), { locale: vi, addSuffix: true }) : '—'}
            </span>
          )
        },
      },
      {
        id: 'thaoTac',
        header: '',
        cell: ({ row }) =>
          row.original.status === 'PENDING' ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={async (su) => {
                su.stopPropagation()
                await guiLaiLoiMoi(row.original.id).unwrap()
                toast.success('Đã gửi lại lời mời.')
              }}
            >
              <Mail />
              Gửi lại lời mời
            </Button>
          ) : null,
      },
    ],
    [guiLaiLoiMoi],
  )

  return (
    <>
      <ListPage
        tieuDe="Người dùng"
        moTa="Người dùng của doanh nghiệp. Số lượng tính vào hạn mức của gói."
        cot={cot}
        trang={truyVan.data}
        dangTai={truyVan.isLoading}
        timKiem={{
          goiY: 'Tìm theo tên hoặc địa chỉ thư…',
          giaTri: boLoc.tuKhoa ?? '',
          onDoi: (v) => datBoLoc((cu) => ({ ...cu, tuKhoa: v, trang: 0 })),
        }}
        boLoc={[
          {
            khoa: 'trangThai',
            nhan: 'Trạng thái',
            luaChon: [
              { giaTri: 'ACTIVE', nhan: 'Đang hoạt động' },
              { giaTri: 'PENDING', nhan: 'Chờ kích hoạt' },
              { giaTri: 'DISABLED', nhan: 'Đã vô hiệu hoá' },
            ],
          },
          {
            khoa: 'vaiTro',
            nhan: 'Vai trò',
            luaChon: [
              { giaTri: 'TENANT_ADMIN', nhan: 'Quản trị doanh nghiệp' },
              { giaTri: 'AGENT', nhan: 'Nhân viên chăm sóc' },
            ],
          },
        ]}
        giaTriBoLoc={{ trangThai: boLoc.trangThai, vaiTro: boLoc.vaiTro }}
        onDoiBoLoc={(khoa, giaTri) =>
          datBoLoc((cu) => ({
            ...cu,
            trang: 0,
            ...(khoa === 'trangThai'
              ? { trangThai: giaTri as BoLocNguoiDung['trangThai'] }
              : { vaiTro: giaTri as BoLocNguoiDung['vaiTro'] }),
          }))
        }
        onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
        sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
        onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
        thaoTacChinh={{
          nhan: 'Mời người dùng',
          BieuTuong: UserPlus,
          onClick: () => datMoHopThoai(true),
        }}
        khiChuaCoDuLieu={{
          BieuTuong: Users,
          tieuDe: 'Chưa có người dùng nào ngoài bạn',
          moTa: 'Mời đồng nghiệp để chia nhau xử lý hộp thư.',
        }}
      />

      <InviteUserDialog mo={moHopThoai} onDoiMo={datMoHopThoai} />
    </>
  )
}
