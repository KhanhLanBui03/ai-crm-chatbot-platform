import type { SortingState } from '@tanstack/react-table'
import { differenceInDays, format, formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { MessageSquareShare, Plug, RefreshCw, Unplug } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import {
  useDanhSachKenhQuery,
  useNgatKenhMutation,
  useXacMinhKenhMutation,
} from '@/api/channels'
import { ListPage } from '@/components/layout/ListPage'
import { Button } from '@/components/ui/button'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { ConnectChannelDialog } from '@/features/settings/ConnectChannelDialog'
import type { Kenh, TrangThaiKenh } from '@/types/schema'
import type { Page } from '@/types/api'

const NHAN_LOAI: Record<string, string> = { ZALO: 'Zalo OA', FACEBOOK: 'Facebook Messenger' }

const NHAN_TRANG_THAI: Record<
  TrangThaiKenh,
  { nhan: string; sacThai: 'success' | 'warning' | 'destructive' | 'neutral' }
> = {
  ACTIVE: { nhan: 'Đang hoạt động', sacThai: 'success' },
  PENDING_VERIFY: { nhan: 'Chờ xác minh', sacThai: 'warning' },
  ERROR: { nhan: 'Lỗi kết nối', sacThai: 'destructive' },
  DISCONNECTED: { nhan: 'Đã ngắt', sacThai: 'neutral' },
}

/** Còn bấy nhiêu ngày thì phải nhắc — gia hạn token cần thao tác trên cổng của nền tảng kia. */
const NGAY_CANH_BAO_TOKEN = 14

/**
 * SCR016 — danh sách kênh đã kết nối. Mẫu M1, cộng hộp thoại kết nối của SCR017.
 *
 * Web Widget **không** nằm trong bảng này: theo giao ước, `channels.channel_type` chỉ nhận `ZALO`
 * và `FACEBOOK`, còn widget có bảng cấu hình riêng và một màn riêng (SCR018). Gộp chúng lại cho
 * "gọn" là làm mờ mất khác biệt thật — widget không có token cần gia hạn và không có cửa sổ gửi
 * tin.
 */
export function ChannelsPage() {
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'accountName', desc: false }])
  const [moHopThoai, datMoHopThoai] = useState(false)
  const truyVan = useDanhSachKenhQuery()
  const [xacMinh] = useXacMinhKenhMutation()
  const [ngat] = useNgatKenhMutation()

  // Endpoint này trả mảng chứ không phải trang — bọc lại cho khớp mẫu M1. Danh sách kênh của một
  // doanh nghiệp SME không bao giờ dài tới mức cần phân trang.
  const trang: Page<Kenh> | undefined = useMemo(() => {
    if (!truyVan.data) return undefined
    const ds = [...truyVan.data]
    const khoa = sapXep[0]
    if (khoa) {
      ds.sort((a, b) => {
        const va = String(a[khoa.id as keyof Kenh] ?? '')
        const vb = String(b[khoa.id as keyof Kenh] ?? '')
        return (khoa.desc ? -1 : 1) * va.localeCompare(vb, 'vi')
      })
    }
    return { items: ds, page: 0, size: ds.length, totalItems: ds.length, totalPages: 1 }
  }, [truyVan.data, sapXep])

  const cot = useMemo<CotBang<Kenh>[]>(
    () => [
      {
        id: 'accountName',
        accessorKey: 'accountName',
        header: 'Tài khoản',
        enableSorting: true,
        cell: ({ row }) => {
          const k = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="truncate font-medium">{k.accountName ?? 'Chưa đặt tên'}</span>
              <span className="text-muted-foreground truncate font-mono text-xs">
                {k.externalAccountId}
              </span>
            </div>
          )
        },
      },
      {
        id: 'channelType',
        accessorKey: 'channelType',
        header: 'Nền tảng',
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {NHAN_LOAI[row.original.channelType] ?? row.original.channelType}
          </span>
        ),
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const k = row.original
          const t = NHAN_TRANG_THAI[k.status]
          return (
            <div className="flex flex-col gap-1">
              <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
              {k.lastError && (
                <span className="text-destructive max-w-64 text-xs leading-snug">
                  {k.lastError}
                </span>
              )}
            </div>
          )
        },
      },
      {
        id: 'tokenExpiresAt',
        accessorKey: 'tokenExpiresAt',
        header: 'Hạn token',
        cell: ({ row }) => {
          const han = row.original.tokenExpiresAt
          if (!han) return <span className="text-muted-foreground">Không hết hạn</span>
          const conLai = differenceInDays(new Date(han), new Date())
          // Token hết hạn là nguyên nhân số một khiến kênh im lặng. Nhắc trước hai tuần vì gia
          // hạn phải làm trên cổng của Zalo/Facebook, không bấm một nút ở đây là xong.
          const sapHet = conLai <= NGAY_CANH_BAO_TOKEN
          return (
            <span className={sapHet ? 'text-destructive font-medium' : 'text-muted-foreground'}>
              {format(new Date(han), 'dd/MM/yyyy', { locale: vi })}
              {sapHet && conLai >= 0 && ` · còn ${conLai} ngày`}
              {conLai < 0 && ' · đã hết hạn'}
            </span>
          )
        },
      },
      {
        id: 'sendWindowHours',
        accessorKey: 'sendWindowHours',
        header: 'Cửa sổ gửi',
        cell: ({ row }) => {
          const gio = row.original.sendWindowHours
          return (
            <span className="text-muted-foreground tabular-nums">
              {gio ? `${gio} giờ` : 'Không giới hạn'}
            </span>
          )
        },
      },
      {
        id: 'conversationCount',
        accessorKey: 'conversationCount',
        header: 'Hội thoại',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="tabular-nums">
            {new Intl.NumberFormat('vi-VN').format(row.original.conversationCount ?? 0)}
          </span>
        ),
      },
      {
        id: 'verifiedAt',
        accessorKey: 'verifiedAt',
        // KHÔNG đặt là "Xác minh": trùng chữ với nút thao tác cùng bảng, và một cột tên giống
        // hệt một nút thì người đọc phải dừng lại đoán xem cái nào làm gì.
        header: 'Xác minh lúc',
        cell: ({ row }) => {
          const luc = row.original.verifiedAt
          return (
            <span className="text-muted-foreground text-xs">
              {luc
                ? formatDistanceToNowStrict(new Date(luc), { locale: vi, addSuffix: true })
                : 'Chưa xác minh'}
            </span>
          )
        },
      },
      {
        id: 'thaoTac',
        header: '',
        cell: ({ row }) => {
          const k = row.original
          return (
            <div className="flex items-center justify-end gap-1">
              {(k.status === 'PENDING_VERIFY' || k.status === 'ERROR') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async (su) => {
                    su.stopPropagation()
                    await xacMinh(k.id).unwrap()
                    toast.success('Đã xác minh webhook. Kênh bắt đầu nhận tin.')
                  }}
                >
                  <RefreshCw />
                  Xác minh
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={async (su) => {
                  su.stopPropagation()
                  await ngat(k.id).unwrap()
                  toast.success('Đã ngắt kênh. Hội thoại cũ vẫn giữ nguyên.')
                }}
              >
                <Unplug />
                Ngắt
              </Button>
            </div>
          )
        },
      },
    ],
    [xacMinh, ngat],
  )

  return (
    <>
      <ListPage
        tieuDe="Kênh"
        moTa="Zalo OA và Facebook Messenger. Web Widget cấu hình ở trang riêng."
        cot={cot}
        trang={trang}
        dangTai={truyVan.isLoading}
        sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
        onDoiTrang={() => {}}
        thaoTacChinh={{
          nhan: 'Kết nối kênh',
          BieuTuong: Plug,
          onClick: () => datMoHopThoai(true),
        }}
        khiChuaCoDuLieu={{
          BieuTuong: MessageSquareShare,
          tieuDe: 'Chưa kết nối kênh nào',
          moTa: 'Kết nối Zalo OA hoặc Facebook để tin nhắn của khách chảy về hộp thư.',
        }}
      />

      <ConnectChannelDialog mo={moHopThoai} onDoiMo={datMoHopThoai} />
    </>
  )
}
