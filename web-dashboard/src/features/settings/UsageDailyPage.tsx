import type { SortingState } from '@tanstack/react-table'
import { format } from 'date-fns'
import { vi } from 'date-fns/locale'
import { BarChart3, Download, GitBranch, Radio } from 'lucide-react'
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
 *
 * Kênh HOẶC nhánh, không bao giờ cả hai (UC006 6.1): một hội thoại đi qua nhiều nhánh, gộp hai chiều là
 * đếm nó nhiều lần.
 */
export function UsageDailyPage() {
  const [trang, datTrang] = useState(0)
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'statDate', desc: true }])
  const [nhomTheo, datNhomTheo] = useState<'channel' | 'route'>('channel')

  const truyVan = useMucSuDungTheoNgayQuery({
    nhomTheo,
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
      ...(nhomTheo === 'channel'
        ? ([
          {
            id: 'channelType',
            accessorKey: 'channelType',
            header: 'Kênh',
            cell: ({ row }) => {
              const k = row.original.channelType
              return (
                <span className="text-muted-foreground">
                  {k ? (NHAN_KENH[k as LoaiKenh] ?? k) : 'Không rõ kênh'}
                </span>
              )
            },
          },
        ] satisfies CotBang<DiemSuDungNgay>[])
        : []),
      ...(nhomTheo === 'route'
        ? ([
          {
            id: 'route',
            accessorKey: 'route',
            header: 'Nhánh xử lý',
            cell: ({ row }) => {
              const r = row.original.route
              return r ? <StatusChip>{NHAN_NHANH[r] ?? r}</StatusChip> : <span>—</span>
            },
          },
        ] satisfies CotBang<DiemSuDungNgay>[])
        : []),
      {
        id: 'conversations',
        accessorKey: 'conversations',
        header: 'Hội thoại',
        enableSorting: true,
        cell: ({ row }) => <span className="tabular-nums">{so(row.original.conversations)}</span>,
      },
      {
        id: 'turns',
        accessorKey: 'turns',
        header: 'Lượt AI',
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">{so(row.original.turns)}</span>
        ),
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
          // Mẫu số là LƯỢT, không phải hội thoại: đệm trúng theo từng lượt hỏi. Chia cho số hội thoại
          // thì một hội thoại dài trúng đệm nhiều lần cho ra tỉ lệ trên 100%.
          const ty = d.turns > 0 ? Math.round(((d.cachedHits ?? 0) / d.turns) * 100) : 0
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
    [nhomTheo],
  )

  return (
    <ListPage
      tieuDe="Mức sử dụng theo ngày"
      moTa={
        nhomTheo === 'channel'
          ? 'Chia theo ngày và kênh — để thấy chi phí đến từ đâu, không chỉ là bao nhiêu. Hội thoại = hội thoại mở trong ngày.'
          : 'Chia theo ngày và nhánh xử lý. Một hội thoại có thể có mặt ở nhiều nhánh, nên không cộng cột hội thoại giữa các nhánh. Hội thoại theo nhánh chỉ được đếm từ khi bật tính năng này — ngày cũ hơn chỉ có số lượt.'
      }
      cot={cot}
      trang={truyVan.data}
      dangTai={truyVan.isFetching}
      layId={(d) => `${d.statDate}-${d.channelType}-${d.route}`}
      sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
      onDoiTrang={datTrang}
      thaoTacPhu={[
        {
          nhan: 'Theo kênh',
          BieuTuong: Radio,
          bienThe: nhomTheo === 'channel' ? 'default' : 'outline',
          onClick: () => {
            datNhomTheo('channel')
            datTrang(0)
          },
        },
        {
          nhan: 'Theo nhánh',
          BieuTuong: GitBranch,
          bienThe: nhomTheo === 'route' ? 'default' : 'outline',
          onClick: () => {
            datNhomTheo('route')
            datTrang(0)
          },
        },
        { nhan: 'Xuất CSV', BieuTuong: Download, onClick: () => {} },
      ]}
      khiChuaCoDuLieu={{
        BieuTuong: BarChart3,
        tieuDe: 'Chưa có dữ liệu sử dụng',
        moTa: 'Số liệu xuất hiện sau hội thoại đầu tiên đi qua tác tử AI.',
      }}
    />
  )
}
