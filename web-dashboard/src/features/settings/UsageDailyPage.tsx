import type { SortingState } from '@tanstack/react-table'
import { format } from 'date-fns'
import { vi } from 'date-fns/locale'
import { BarChart3, Download } from 'lucide-react'
import { useMemo, useState } from 'react'

import { useMucSuDungTheoNgayQuery } from '@/api/platform'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { NHAN_KENH } from '@/features/conversations/nhan'
import type { DiemSuDungNgay, LoaiKenh } from '@/types/schema'

const so = (v: number) => new Intl.NumberFormat('vi-VN').format(v)
const tien = (v: number) => new Intl.NumberFormat('vi-VN').format(Math.round(v)) + ' ₫'

const NHAN_NHANH: Record<string, string> = {
  SMALL_TALK: 'Trò chuyện',
  RAG: 'Truy hồi tri thức',
  TOOL_CALL: 'Gọi công cụ',
  CLARIFY: 'Hỏi lại',
  HANDOFF: 'Chuyển người',
  SUMMARY: 'Tóm tắt',
  EXTRACTION: 'Trích xuất',
}

/**
 * SCR015 — mức sử dụng theo ngày. Mẫu M1.
 *
 * Đây là màn để trả lời câu hỏi "vì sao tháng này tốn nhiều token thế": chia theo ngày, theo kênh
 * và theo nhánh xử lý. Cộng dồn cả tháng thì SCR014 đã có — ở đây phải chẻ nhỏ ra mới thấy nguyên
 * nhân.
 */
export function UsageDailyPage() {
  const [trang, datTrang] = useState(0)
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'statDate', desc: true }])

  const truyVan = useMucSuDungTheoNgayQuery({
    trang,
    sapXep: sapXep[0] ? `${sapXep[0].desc ? '-' : ''}${sapXep[0].id}` : undefined,
  })

  const cot = useMemo<CotBang<DiemSuDungNgay>[]>(
    () => [
      {
        id: 'statDate',
        accessorKey: 'statDate',
        header: 'Ngày',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="font-medium tabular-nums">
            {format(new Date(row.original.statDate), 'EEEE dd/MM', { locale: vi })}
          </span>
        ),
      },
      {
        id: 'channelType',
        accessorKey: 'channelType',
        header: 'Kênh',
        cell: ({ row }) => {
          const k = row.original.channelType
          return (
            <span className="text-muted-foreground">
              {k ? (NHAN_KENH[k as LoaiKenh] ?? k) : 'Tất cả'}
            </span>
          )
        },
      },
      {
        id: 'route',
        accessorKey: 'route',
        header: 'Nhánh xử lý',
        cell: ({ row }) => {
          const r = row.original.route
          return r ? <StatusChip>{NHAN_NHANH[r] ?? r}</StatusChip> : <span>—</span>
        },
      },
      {
        id: 'conversations',
        accessorKey: 'conversations',
        header: 'Hội thoại',
        enableSorting: true,
        cell: ({ row }) => <span className="tabular-nums">{so(row.original.conversations)}</span>,
      },
      {
        id: 'promptTokens',
        accessorKey: 'promptTokens',
        header: 'Token vào',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {so(row.original.promptTokens)}
          </span>
        ),
      },
      {
        id: 'completionTokens',
        accessorKey: 'completionTokens',
        header: 'Token ra',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {so(row.original.completionTokens)}
          </span>
        ),
      },
      {
        id: 'cachedHits',
        accessorKey: 'cachedHits',
        header: 'Dùng lại cache',
        cell: ({ row }) => {
          const d = row.original
          const ty = d.conversations > 0 ? Math.round(((d.cachedHits ?? 0) / d.conversations) * 100) : 0
          // Tỉ lệ dùng lại cache là đòn bẩy chi phí trực tiếp: mỗi lần trúng cache là một lần
          // không phải gọi mô hình
          return (
            <span className="tabular-nums">
              {so(d.cachedHits ?? 0)}{' '}
              <span className="text-muted-foreground text-xs">({ty}%)</span>
            </span>
          )
        },
      },
      {
        id: 'costVnd',
        accessorKey: 'costVnd',
        header: 'Chi phí',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="font-medium tabular-nums">{tien(row.original.costVnd)}</span>
        ),
      },
    ],
    [],
  )

  return (
    <ListPage
      tieuDe="Mức sử dụng theo ngày"
      moTa="Chia theo ngày, kênh và nhánh xử lý — để thấy chi phí đến từ đâu, không chỉ là bao nhiêu."
      cot={cot}
      trang={truyVan.data}
      dangTai={truyVan.isLoading}
      layId={(d) => `${d.statDate}-${d.channelType}-${d.route}`}
      sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
      onDoiTrang={datTrang}
      thaoTacPhu={[{ nhan: 'Xuất CSV', BieuTuong: Download, onClick: () => {} }]}
      khiChuaCoDuLieu={{
        BieuTuong: BarChart3,
        tieuDe: 'Chưa có dữ liệu sử dụng',
        moTa: 'Số liệu xuất hiện sau hội thoại đầu tiên đi qua tác tử AI.',
      }}
    />
  )
}
