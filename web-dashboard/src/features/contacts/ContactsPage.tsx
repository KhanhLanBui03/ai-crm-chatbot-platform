import type { SortingState } from '@tanstack/react-table'
import { formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { Download, ShieldCheck, ShieldOff, Users } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useDanhSachKhachHangQuery, type BoLocKhachHang } from '@/api/contacts'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { CreateContactDialog } from '@/features/contacts/CreateContactDialog'
import { NHAN_KENH } from '@/features/conversations/nhan'
import type { KenhChinh, KhachHang } from '@/types/schema'
import { chuCaiDau } from '@/utils/ten'

const NHAN_KENH_CHINH: Record<KenhChinh, string> = {
  ...NHAN_KENH,
  PHONE: 'Nhập tay',
}

/**
 * SCR026 — danh bạ khách hàng.
 *
 * Toàn bộ màn hình là **một object cấu hình cắm vào mẫu M1**: định nghĩa cột, hai bộ lọc, một ô
 * tìm kiếm. Không có bố cục riêng, không có trạng thái rỗng viết tay, không có phân trang viết
 * tay — đó là điều 18 màn danh sách còn lại sẽ thừa hưởng.
 */
export function ContactsPage() {
  const dieuHuong = useNavigate()
  const [moTao, datMoTao] = useState(false)
  const [boLoc, datBoLoc] = useState<BoLocKhachHang>({ trang: 0 })
  const [sapXep, datSapXep] = useState<SortingState>([
    { id: 'lastInteractionAt', desc: true },
  ])

  const truyVan = useDanhSachKhachHangQuery({
    ...boLoc,
    sapXep: sapXep[0] ? `${sapXep[0].desc ? '-' : ''}${sapXep[0].id}` : undefined,
  })

  const cot = useMemo<CotBang<KhachHang>[]>(
    () => [
      {
        id: 'fullName',
        accessorKey: 'fullName',
        header: 'Khách hàng',
        enableSorting: true,
        cell: ({ row }) => {
          const k = row.original
          const ten = k.fullName ?? 'Chưa có tên'
          return (
            <div className="flex items-center gap-2.5">
              <div className="bg-secondary text-secondary-foreground flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium">
                {chuCaiDau(ten)}
              </div>
              <div className="flex min-w-0 flex-col">
                <span className="truncate font-medium">{ten}</span>
                {k.email && (
                  <span className="text-muted-foreground truncate text-xs">{k.email}</span>
                )}
              </div>
            </div>
          )
        },
      },
      {
        id: 'phone',
        accessorKey: 'phone',
        header: 'Điện thoại',
        cell: ({ row }) => (
          <span className="tabular-nums">{row.original.phone ?? '—'}</span>
        ),
      },
      {
        id: 'primaryChannel',
        accessorKey: 'primaryChannel',
        header: 'Kênh chính',
        cell: ({ row }) => {
          const kenh = row.original.primaryChannel
          return (
            <span className="text-muted-foreground">{kenh ? NHAN_KENH_CHINH[kenh] : '—'}</span>
          )
        },
      },
      {
        id: 'tags',
        header: 'Thẻ',
        cell: ({ row }) => {
          const the = row.original.tags ?? []
          if (the.length === 0) return <span className="text-muted-foreground">—</span>
          return (
            <div className="flex flex-wrap gap-1">
              {the.slice(0, 2).map((t) => (
                <StatusChip key={t.id}>{t.name}</StatusChip>
              ))}
              {the.length > 2 && (
                <span className="text-muted-foreground text-xs">+{the.length - 2}</span>
              )}
            </div>
          )
        },
      },
      {
        id: 'consentGranted',
        accessorKey: 'consentGranted',
        header: 'Đồng ý dữ liệu',
        cell: ({ row }) =>
          // Nghị định 13: khách chưa đồng ý thì không được dùng dữ liệu cho mục đích tiếp thị.
          // Hiện thẳng trên danh sách để nhân viên thấy trước khi mở hồ sơ.
          row.original.consentGranted ? (
            <StatusChip sacThai="success" BieuTuong={ShieldCheck}>
              Đã đồng ý
            </StatusChip>
          ) : (
            <StatusChip sacThai="warning" BieuTuong={ShieldOff}>
              Chưa đồng ý
            </StatusChip>
          ),
      },
      {
        id: 'lastInteractionAt',
        accessorKey: 'lastInteractionAt',
        header: 'Tương tác gần nhất',
        enableSorting: true,
        cell: ({ row }) => {
          const luc = row.original.lastInteractionAt
          return (
            <span className="text-muted-foreground tabular-nums">
              {luc ? formatDistanceToNowStrict(new Date(luc), { locale: vi, addSuffix: true }) : '—'}
            </span>
          )
        },
      },
    ],
    [],
  )

  return (
    <>
    <ListPage
      tieuDe="Khách hàng"
      moTa="Danh bạ hợp nhất từ mọi kênh. Bản ghi đã hợp nhất không hiện ở đây."
      cot={cot}
      trang={truyVan.data}
      dangTai={truyVan.isLoading}
      onChonDong={(k) => dieuHuong(`/khach-hang/${k.id}`)}
      timKiem={{
        goiY: 'Tìm theo tên, số điện thoại, email…',
        giaTri: boLoc.tuKhoa ?? '',
        onDoi: (v) => datBoLoc((cu) => ({ ...cu, tuKhoa: v, trang: 0 })),
      }}
      boLoc={[
        {
          khoa: 'trangThai',
          nhan: 'Trạng thái',
          luaChon: [
            { giaTri: 'ACTIVE', nhan: 'Đang hoạt động' },
            { giaTri: 'MERGED', nhan: 'Đã hợp nhất' },
            { giaTri: 'ANONYMIZED', nhan: 'Đã ẩn danh hoá' },
          ],
        },
        {
          khoa: 'daDongY',
          nhan: 'Đồng ý dữ liệu',
          luaChon: [
            { giaTri: 'true', nhan: 'Đã đồng ý' },
            { giaTri: 'false', nhan: 'Chưa đồng ý' },
          ],
        },
      ]}
      giaTriBoLoc={{
        trangThai: boLoc.trangThai,
        daDongY: boLoc.daDongY === undefined ? undefined : String(boLoc.daDongY),
      }}
      onDoiBoLoc={(khoa, giaTri) =>
        datBoLoc((cu) => ({
          ...cu,
          trang: 0,
          ...(khoa === 'trangThai'
            ? { trangThai: giaTri as BoLocKhachHang['trangThai'] }
            : { daDongY: giaTri === undefined ? undefined : giaTri === 'true' }),
        }))
      }
      onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
      sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
      onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
      thaoTacChinh={{ nhan: 'Thêm khách hàng', onClick: () => datMoTao(true) }}
      thaoTacPhu={[{ nhan: 'Xuất CSV', BieuTuong: Download, onClick: () => {} }]}
      thaoTacHangLoat={[
        { nhan: 'Gắn thẻ', onClick: () => {} },
        { nhan: 'Xuất danh sách', onClick: () => {} },
      ]}
      khiChuaCoDuLieu={{
        BieuTuong: Users,
        tieuDe: 'Chưa có khách hàng nào',
        moTa: 'Khách hàng được tạo tự động khi có tin nhắn đầu tiên từ bất kỳ kênh nào.',
      }}
    />
    <CreateContactDialog mo={moTao} onDoiMo={datMoTao} />
    </>
  )
}
