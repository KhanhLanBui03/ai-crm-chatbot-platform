import type { SortingState } from '@tanstack/react-table'
import { format, formatDistanceToNowStrict, isPast } from 'date-fns'
import { vi } from 'date-fns/locale'
import { Download, FileSpreadsheet, ShieldAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { useDanhSachTepBaoCaoQuery, useYeuCauXuatBaoCaoMutation } from '@/api/analytics'
import { ListPage } from '@/components/layout/ListPage'
import { Button } from '@/components/ui/button'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import type { SacThai } from '@/components/ui/status-chip'
import type { LoaiBaoCao, TepBaoCao, TrangThaiTepBaoCao } from '@/types/schema'

const NHAN_LOAI: Record<LoaiBaoCao, string> = {
  OVERVIEW: 'Tổng quan',
  FUNNEL: 'Phễu chuyển đổi',
  TOPICS: 'Chủ đề hội thoại',
  AI_PERFORMANCE: 'Hiệu quả tác tử AI',
  AUDIT_LOG: 'Nhật ký kiểm toán',
}

const NHAN_TRANG_THAI: Record<TrangThaiTepBaoCao, { nhan: string; sacThai: SacThai }> = {
  QUEUED: { nhan: 'Đang xếp hàng', sacThai: 'neutral' },
  RUNNING: { nhan: 'Đang chạy', sacThai: 'info' },
  READY: { nhan: 'Sẵn sàng', sacThai: 'success' },
  FAILED: { nhan: 'Thất bại', sacThai: 'destructive' },
  EXPIRED: { nhan: 'Đã hết hạn', sacThai: 'neutral' },
}

function coTep(v: number | null | undefined): string {
  if (v == null) return '—'
  if (v >= 1_048_576) return `${(v / 1_048_576).toFixed(1)} MB`
  if (v >= 1024) return `${Math.round(v / 1024)} KB`
  return `${v} B`
}

/**
 * SCR053 — danh sách tệp báo cáo đã xuất. Mẫu M1.
 *
 * Hai chi tiết không được bỏ:
 *
 * - **Cảnh báo dữ liệu cá nhân.** Tệp kiểm toán chứa dữ liệu cá nhân; người tải phải biết trước
 *   khi nó nằm trong thư mục Downloads của họ (Nghị định 13, bề mặt T8).
 * - **Hạn tự xoá.** Tệp hết hạn thì không tải lại được và phải xuất lại — nếu chỉ hiện trạng thái
 *   "Đã hết hạn" mà không nói hạn là bao lâu thì người dùng không biết phải tải sớm cỡ nào.
 */
export function ReportExportsPage() {
  const [trang, datTrang] = useState(0)
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'requestedAt', desc: true }])
  const truyVan = useDanhSachTepBaoCaoQuery({
    trang,
    sapXep: sapXep[0] ? `${sapXep[0].desc ? '-' : ''}${sapXep[0].id}` : undefined,
  })
  const [xuat, ketQuaXuat] = useYeuCauXuatBaoCaoMutation()

  const cot = useMemo<CotBang<TepBaoCao>[]>(
    () => [
      {
        id: 'reportType',
        accessorKey: 'reportType',
        header: 'Báo cáo',
        enableSorting: true,
        cell: ({ row }) => {
          const t = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="font-medium">{NHAN_LOAI[t.reportType]}</span>
              <span className="text-muted-foreground text-xs">
                {t.format}
                {t.partTotal != null && ` · phần ${t.partIndex}/${t.partTotal}`}
              </span>
            </div>
          )
        },
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const t = row.original
          const n = NHAN_TRANG_THAI[t.status]
          return (
            <div className="flex flex-col gap-1">
              <StatusChip sacThai={n.sacThai}>{n.nhan}</StatusChip>
              {t.errorMessage && (
                <span className="text-destructive max-w-64 text-xs leading-snug">
                  {t.errorMessage}
                </span>
              )}
            </div>
          )
        },
      },
      {
        id: 'containsPersonalData',
        accessorKey: 'containsPersonalData',
        header: 'Dữ liệu cá nhân',
        cell: ({ row }) =>
          row.original.containsPersonalData ? (
            <StatusChip sacThai="warning" BieuTuong={ShieldAlert}>
              Có
            </StatusChip>
          ) : (
            <span className="text-muted-foreground">Không</span>
          ),
      },
      {
        id: 'rowCount',
        accessorKey: 'rowCount',
        header: 'Kích thước',
        cell: ({ row }) => {
          const t = row.original
          return (
            <span className="text-muted-foreground tabular-nums">
              {t.rowCount != null ? `${new Intl.NumberFormat('vi-VN').format(t.rowCount)} dòng` : '—'}
              {t.fileSizeBytes != null && ` · ${coTep(t.fileSizeBytes)}`}
            </span>
          )
        },
      },
      {
        id: 'expiresAt',
        accessorKey: 'expiresAt',
        header: 'Hạn tải',
        cell: ({ row }) => {
          const han = row.original.expiresAt
          if (!han) return <span className="text-muted-foreground">—</span>
          const het = isPast(new Date(han))
          return (
            <span className={het ? 'text-muted-foreground' : 'text-[13px] tabular-nums'}>
              {het
                ? 'Đã hết hạn'
                : `còn ${formatDistanceToNowStrict(new Date(han), { locale: vi })}`}
            </span>
          )
        },
      },
      {
        id: 'requestedAt',
        accessorKey: 'requestedAt',
        header: 'Yêu cầu lúc',
        enableSorting: true,
        cell: ({ row }) => {
          const t = row.original
          return (
            <div className="flex flex-col">
              <span className="tabular-nums">
                {format(new Date(t.requestedAt), 'dd/MM HH:mm', { locale: vi })}
              </span>
              <span className="text-muted-foreground text-xs">{t.requestedByName}</span>
            </div>
          )
        },
      },
      {
        id: 'thaoTac',
        header: '',
        cell: ({ row }) => {
          const t = row.original
          if (t.status !== 'READY') return null
          return (
            <Button
              variant="ghost"
              size="sm"
              onClick={(su) => {
                su.stopPropagation()
                toast.info('Bản mock chưa sinh tệp thật — nút này sẽ tải khi nối máy chủ.')
              }}
            >
              <Download />
              Tải về
            </Button>
          )
        },
      },
    ],
    [],
  )

  return (
    <ListPage
      tieuDe="Tệp báo cáo"
      moTa="Xuất báo cáo chạy nền. Tệp có hạn tự xoá — tải về trước khi hết hạn."
      cot={cot}
      trang={truyVan.data}
      dangTai={truyVan.isLoading}
      sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
      onDoiTrang={datTrang}
      thaoTacChinh={{
        nhan: 'Xuất tổng quan',
        BieuTuong: FileSpreadsheet,
        onClick: async () => {
          await xuat({ reportType: 'OVERVIEW', format: 'XLSX' }).unwrap()
          toast.success('Đã xếp hàng. Tệp sẽ xuất hiện ở đầu danh sách.')
        },
      }}
      thaoTacPhu={
        ketQuaXuat.isLoading ? [{ nhan: 'Đang xếp hàng…', onClick: () => {} }] : undefined
      }
      khiChuaCoDuLieu={{
        BieuTuong: FileSpreadsheet,
        tieuDe: 'Chưa xuất báo cáo nào',
        moTa: 'Bấm "Xuất báo cáo" ở các màn phân tích để tạo tệp.',
      }}
    />
  )
}
