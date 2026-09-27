import type { SortingState } from '@tanstack/react-table'
import { formatDistanceToNowStrict, isValid } from 'date-fns'
import { vi } from 'date-fns/locale'
import {
  AlertTriangle,
  Mail,
  MoreHorizontal,
  Pencil,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  UserX,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import {
  useDanhSachNguoiDungQuery,
  useGuiLaiLoiMoiMutation,
  useKichHoatNguoiDungMutation,
  useVoHieuHoaNguoiDungMutation,
  useXoaNguoiDungMutation,
  type BoLocNguoiDung,
} from '@/api/platform'
import { ListPage } from '@/components/layout/ListPage'
import { Button } from '@/components/ui/button'
import type { CotBang } from '@/components/ui/data-table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { StatusChip } from '@/components/ui/status-chip'
import { EditUserDialog } from '@/features/settings/EditUserDialog'
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

function dinhDangThoiGian(luc: string | null | undefined): string {
  if (!luc) return '—'
  try {
    const d = new Date(luc)
    if (!isValid(d)) return '—'
    return formatDistanceToNowStrict(d, { locale: vi, addSuffix: true })
  } catch {
    return '—'
  }
}

/** SCR008 — danh sách người dùng. Mẫu M1, cộng hộp thoại mời của SCR009 và chỉnh sửa phân quyền. */
export function UsersPage() {
  const [boLoc, datBoLoc] = useState<BoLocNguoiDung>({ trang: 0 })
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'fullName', desc: false }])
  const [moHopThoaiMoi, datMoHopThoaiMoi] = useState(false)
  const [nguoiDungChinhSua, datNguoiDungChinhSua] = useState<NguoiDung | null>(null)
  const [moHopThoaiSua, datMoHopThoaiSua] = useState(false)

  const [guiLaiLoiMoi] = useGuiLaiLoiMoiMutation()
  const [voHieuHoa] = useVoHieuHoaNguoiDungMutation()
  const [kichHoat] = useKichHoatNguoiDungMutation()
  const [xoaNguoiDung] = useXoaNguoiDungMutation()

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
          const t = NHAN_TRANG_THAI[row.original.status] ?? { nhan: row.original.status, sacThai: 'neutral' }
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
          return (
            <span className="text-muted-foreground tabular-nums">
              {dinhDangThoiGian(row.original.lastLoginAt)}
            </span>
          )
        },
      },
      {
        id: 'thaoTac',
        header: '',
        cell: ({ row }) => {
          const u = row.original
          return (
            <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="size-8 p-0">
                    <MoreHorizontal className="size-4" />
                    <span className="sr-only">Thao tác</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem
                    onClick={() => {
                      datNguoiDungChinhSua(u)
                      datMoHopThoaiSua(true)
                    }}
                  >
                    <Pencil className="mr-2 size-4" />
                    Đổi vai trò / Sửa
                  </DropdownMenuItem>

                  {u.status === 'PENDING' && (
                    <DropdownMenuItem
                      onClick={async () => {
                        try {
                          await guiLaiLoiMoi(u.id).unwrap()
                          toast.success('Đã gửi lại thư kích hoạt tài khoản.')
                        } catch {
                          toast.error('Gửi lại lời mời thất bại.')
                        }
                      }}
                    >
                      <Mail className="mr-2 size-4" />
                      Gửi lại thư kích hoạt
                    </DropdownMenuItem>
                  )}

                  {u.status === 'ACTIVE' && (
                    <DropdownMenuItem
                      className="text-amber-600 focus:text-amber-600"
                      onClick={async () => {
                        try {
                          await voHieuHoa(u.id).unwrap()
                          toast.success(`Đã vô hiệu hoá tài khoản ${u.email}`)
                        } catch {
                          toast.error('Không thể vô hiệu hoá tài khoản.')
                        }
                      }}
                    >
                      <UserX className="mr-2 size-4" />
                      Vô hiệu hoá
                    </DropdownMenuItem>
                  )}

                  {u.status === 'DISABLED' && (
                    <DropdownMenuItem
                      className="text-emerald-600 focus:text-emerald-600"
                      onClick={async () => {
                        try {
                          await kichHoat(u.id).unwrap()
                          toast.success(`Đã kích hoạt lại tài khoản ${u.email}`)
                        } catch {
                          toast.error('Không thể kích hoạt lại tài khoản.')
                        }
                      }}
                    >
                      <UserCheck className="mr-2 size-4" />
                      Kích hoạt lại
                    </DropdownMenuItem>
                  )}

                  <DropdownMenuSeparator />

                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={async () => {
                      if (window.confirm(`Bạn có chắc muốn xoá thành viên ${u.email} khỏi hệ thống?`)) {
                        try {
                          await xoaNguoiDung(u.id).unwrap()
                          toast.success(`Đã xoá ${u.email} thành công.`)
                        } catch {
                          toast.error('Không thể xoá người dùng.')
                        }
                      }
                    }}
                  >
                    <Trash2 className="mr-2 size-4" />
                    Xoá người dùng
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )
        },
      },
    ],
    [guiLaiLoiMoi, voHieuHoa, kichHoat, xoaNguoiDung],
  )

  return (
    <>
      <ListPage
        tieuDe="Người dùng"
        moTa="Danh sách thành viên của doanh nghiệp. Số lượng tính vào hạn mức người dùng của gói."
        cot={cot}
        trang={truyVan.data}
        dangTai={truyVan.isLoading}
        timKiem={{
          goiY: 'Tìm theo tên hoặc địa chỉ email…',
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
          onClick: () => datMoHopThoaiMoi(true),
        }}
        khiChuaCoDuLieu={{
          BieuTuong: Users,
          tieuDe: 'Chưa có người dùng nào ngoài bạn',
          moTa: 'Mời đồng nghiệp để cùng xử lý hội thoại và tương tác khách hàng.',
        }}
      />

      <InviteUserDialog mo={moHopThoaiMoi} onDoiMo={datMoHopThoaiMoi} />
      {nguoiDungChinhSua && (
        <EditUserDialog
          nguoiDung={nguoiDungChinhSua}
          mo={moHopThoaiSua}
          onDoiMo={(m) => {
            datMoHopThoaiSua(m)
            if (!m) datNguoiDungChinhSua(null)
          }}
        />
      )}
    </>
  )
}
