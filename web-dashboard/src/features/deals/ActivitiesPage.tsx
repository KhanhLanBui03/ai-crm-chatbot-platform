import type { SortingState } from '@tanstack/react-table'
import { format, formatDistanceToNowStrict, isPast } from 'date-fns'
import { vi } from 'date-fns/locale'
import { BellRing, Phone, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useDanhSachHoatDongQuery } from '@/api/sales'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { NHAN_KET_QUA, NHAN_LOAI_HOAT_DONG } from '@/features/leads/nhan'
import type { HoatDong, LoaiHoatDong, TrangThaiNhacViec } from '@/types/schema'

/**
 * SCR047 — hoạt động chăm sóc và nhắc việc. Mẫu M1.
 *
 * Cột **Nhắc việc** là lý do màn này tồn tại chứ không phải cột "loại hoạt động": một lời nhắc
 * đã quá hạn mà chưa ai làm là việc bị bỏ rơi, và nó phải nhìn thấy được từ danh sách.
 */
export function ActivitiesPage() {
  const dieuHuong = useNavigate()
  const [trang, datTrang] = useState(0)
  const [loai, datLoai] = useState<LoaiHoatDong | undefined>()
  const [nhacViec, datNhacViec] = useState<TrangThaiNhacViec | undefined>()
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'performedAt', desc: true }])

  const truyVan = useDanhSachHoatDongQuery({
    trang,
    loai,
    nhacViec,
    sapXep: sapXep[0] ? `${sapXep[0].desc ? '-' : ''}${sapXep[0].id}` : undefined,
  })

  const cot = useMemo<CotBang<HoatDong>[]>(
    () => [
      {
        id: 'type',
        accessorKey: 'type',
        header: 'Loại',
        cell: ({ row }) => <StatusChip>{NHAN_LOAI_HOAT_DONG[row.original.type]}</StatusChip>,
      },
      {
        id: 'subject',
        accessorKey: 'subject',
        header: 'Nội dung',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-[13px] font-medium">{row.original.subject ?? '—'}</span>
        ),
      },
      {
        id: 'contactName',
        accessorKey: 'contactName',
        header: 'Khách hàng',
        cell: ({ row }) => <span className="text-[13px]">{row.original.contactName}</span>,
      },
      {
        id: 'outcome',
        accessorKey: 'outcome',
        header: 'Kết quả',
        cell: ({ row }) => {
          const o = row.original.outcome
          if (!o) return <span className="text-muted-foreground">Chưa ghi</span>
          const k = NHAN_KET_QUA[o]
          return <StatusChip sacThai={k.sacThai}>{k.nhan}</StatusChip>
        },
      },
      {
        id: 'remindAt',
        accessorKey: 'remindAt',
        header: 'Nhắc việc',
        enableSorting: true,
        cell: ({ row }) => {
          const h = row.original
          if (!h.remindAt || h.remindStatus === 'NONE') {
            return <span className="text-muted-foreground">—</span>
          }
          const quaHan = isPast(new Date(h.remindAt)) && h.remindStatus !== 'DONE'
          return (
            <span
              className={
                quaHan
                  ? 'text-destructive flex items-center gap-1 text-[13px] font-medium'
                  : 'text-muted-foreground text-[13px]'
              }
            >
              {quaHan && <BellRing className="size-3.5" />}
              {format(new Date(h.remindAt), 'dd/MM HH:mm', { locale: vi })}
              {quaHan && ' · quá hạn'}
            </span>
          )
        },
      },
      {
        id: 'performedByName',
        accessorKey: 'performedByName',
        header: 'Người thực hiện',
        cell: ({ row }) => {
          const h = row.original
          return (
            <span className="flex items-center gap-1.5 text-[13px]">
              {/* Hoạt động do hệ thống tự ghi khác hẳn hoạt động do người làm — trộn lẫn hai
                  loại là thổi phồng số liệu chăm sóc khách */}
              {h.source === 'AUTO' && <Sparkles className="text-muted-foreground size-3.5" />}
              {h.performedByName}
            </span>
          )
        },
      },
      {
        id: 'performedAt',
        accessorKey: 'performedAt',
        header: 'Thực hiện lúc',
        enableSorting: true,
        cell: ({ row }) => {
          const luc = row.original.performedAt
          return (
            <span className="text-muted-foreground tabular-nums">
              {luc
                ? formatDistanceToNowStrict(new Date(luc), { locale: vi, addSuffix: true })
                : '—'}
            </span>
          )
        },
      },
    ],
    [],
  )

  return (
    <ListPage
      tieuDe="Hoạt động chăm sóc"
      moTa="Cuộc gọi, buổi gặp, báo giá và các lời nhắc gắn với chúng."
      cot={cot}
      trang={truyVan.data}
      dangTai={truyVan.isLoading}
      onChonDong={(h) =>
        dieuHuong(h.dealId ? `/ban-hang/pheu/${h.dealId}` : `/khach-hang/${h.contactId}`)
      }
      boLoc={[
        {
          khoa: 'loai',
          nhan: 'Loại',
          luaChon: Object.entries(NHAN_LOAI_HOAT_DONG).map(([giaTri, nhan]) => ({ giaTri, nhan })),
        },
        {
          khoa: 'nhacViec',
          nhan: 'Nhắc việc',
          luaChon: [
            { giaTri: 'PENDING', nhan: 'Đang chờ' },
            { giaTri: 'SENT', nhan: 'Đã gửi' },
            { giaTri: 'DONE', nhan: 'Đã xong' },
            { giaTri: 'NONE', nhan: 'Không nhắc' },
          ],
        },
      ]}
      giaTriBoLoc={{ loai, nhacViec }}
      onDoiBoLoc={(khoa, giaTri) => {
        datTrang(0)
        if (khoa === 'loai') datLoai(giaTri as LoaiHoatDong | undefined)
        else datNhacViec(giaTri as TrangThaiNhacViec | undefined)
      }}
      onGoHetBoLoc={() => {
        datLoai(undefined)
        datNhacViec(undefined)
        datTrang(0)
      }}
      sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
      onDoiTrang={datTrang}
      khiChuaCoDuLieu={{
        BieuTuong: Phone,
        tieuDe: 'Chưa có hoạt động nào',
        moTa: 'Hoạt động được ghi từ trang chi tiết của một cơ hội tiềm năng hoặc cơ hội bán hàng.',
      }}
    />
  )
}
