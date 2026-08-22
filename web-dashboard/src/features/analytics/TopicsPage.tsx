import type { SortingState } from '@tanstack/react-table'
import { MessagesSquare, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'

import { useThongKeChuDeQuery } from '@/api/analytics'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { Progress } from '@/components/ui/progress'
import { StatusChip } from '@/components/ui/status-chip'
import type { Page } from '@/types/api'
import { cn } from '@/utils/cn'

interface DongChuDe {
  id: string
  topicLabel: string
  conversationCount: number
  botResolvedCount: number
  refusalCount: number
}

const so = (v: number) => new Intl.NumberFormat('vi-VN').format(v)

/** Từ mức này trở lên thì chủ đề đang là khoảng trống tri thức, không phải chuyện nhỏ. */
const NGUONG_TU_CHOI = 0.2

/**
 * SCR052 — thống kê chủ đề hội thoại. Mẫu M1.
 *
 * Cột đáng giá nhất là **tỉ lệ từ chối**, không phải số hội thoại: một chủ đề hỏi nhiều mà tác tử
 * trả lời tốt thì không cần làm gì; một chủ đề hỏi ít mà từ chối 34% là một lỗ hổng trong kho tri
 * thức, và nó phải nổi bật lên dù nằm cuối bảng theo số lượng.
 */
export function TopicsPage() {
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'refusalRate', desc: true }])
  const truyVan = useThongKeChuDeQuery({})

  /** Số liệu về theo từng ngày — gộp lại theo chủ đề trước khi hiển thị. */
  const trang: Page<DongChuDe> | undefined = useMemo(() => {
    if (!truyVan.data) return undefined
    const gop = new Map<string, DongChuDe>()
    for (const d of truyVan.data) {
      const cu = gop.get(d.clusterId) ?? {
        id: d.clusterId,
        topicLabel: d.topicLabel,
        conversationCount: 0,
        botResolvedCount: 0,
        refusalCount: 0,
      }
      cu.conversationCount += d.conversationCount
      cu.botResolvedCount += d.botResolvedCount ?? 0
      cu.refusalCount += d.refusalCount ?? 0
      gop.set(d.clusterId, cu)
    }
    const ds = [...gop.values()]
    const khoa = sapXep[0]
    if (khoa) {
      const lay = (r: DongChuDe) =>
        khoa.id === 'refusalRate'
          ? r.conversationCount > 0
            ? r.refusalCount / r.conversationCount
            : 0
          : (r[khoa.id as keyof DongChuDe] as number | string)
      ds.sort((a, b) => {
        const va = lay(a)
        const vb = lay(b)
        if (typeof va === 'number' && typeof vb === 'number') return (khoa.desc ? -1 : 1) * (va - vb)
        return (khoa.desc ? -1 : 1) * String(va).localeCompare(String(vb), 'vi')
      })
    }
    return { items: ds, page: 0, size: ds.length, totalItems: ds.length, totalPages: 1 }
  }, [truyVan.data, sapXep])

  const cot = useMemo<CotBang<DongChuDe>[]>(
    () => [
      {
        id: 'topicLabel',
        accessorKey: 'topicLabel',
        header: 'Chủ đề',
        enableSorting: true,
        cell: ({ row }) => <span className="font-medium">{row.original.topicLabel}</span>,
      },
      {
        id: 'conversationCount',
        accessorKey: 'conversationCount',
        header: 'Số hội thoại',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="tabular-nums">{so(row.original.conversationCount)}</span>
        ),
      },
      {
        id: 'botResolvedRate',
        header: 'Tác tử tự xử lý',
        cell: ({ row }) => {
          const r = row.original
          const ty = r.conversationCount > 0 ? r.botResolvedCount / r.conversationCount : 0
          return (
            <div className="flex w-32 items-center gap-2">
              <Progress value={ty * 100} className="flex-1" />
              <span className="text-muted-foreground w-10 shrink-0 text-right text-xs tabular-nums">
                {(ty * 100).toFixed(0)}%
              </span>
            </div>
          )
        },
      },
      {
        id: 'refusalRate',
        header: 'Tỉ lệ từ chối',
        enableSorting: true,
        cell: ({ row }) => {
          const r = row.original
          const ty = r.conversationCount > 0 ? r.refusalCount / r.conversationCount : 0
          const cao = ty >= NGUONG_TU_CHOI
          return (
            <span
              className={cn(
                'flex items-center gap-1 tabular-nums',
                cao ? 'text-destructive font-medium' : 'text-muted-foreground',
              )}
            >
              {cao && <TriangleAlert className="size-3.5" />}
              {(ty * 100).toFixed(1)}%
              <span className="text-xs">({so(r.refusalCount)})</span>
            </span>
          )
        },
      },
      {
        id: 'danhGia',
        header: 'Đánh giá',
        cell: ({ row }) => {
          const r = row.original
          const ty = r.conversationCount > 0 ? r.refusalCount / r.conversationCount : 0
          return ty >= NGUONG_TU_CHOI ? (
            <StatusChip sacThai="destructive">Thiếu tri thức</StatusChip>
          ) : ty >= 0.1 ? (
            <StatusChip sacThai="warning">Cần bổ sung</StatusChip>
          ) : (
            <StatusChip sacThai="success">Phủ tốt</StatusChip>
          )
        },
      },
    ],
    [],
  )

  return (
    <ListPage
      tieuDe="Chủ đề hội thoại"
      moTa="Nhóm theo cụm ngữ nghĩa. Sắp mặc định theo tỉ lệ từ chối — chỗ tác tử đang bí, không phải chỗ khách hỏi nhiều."
      cot={cot}
      trang={trang}
      dangTai={truyVan.isLoading}
      sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
      onDoiTrang={() => {}}
      khiChuaCoDuLieu={{
        BieuTuong: MessagesSquare,
        tieuDe: 'Chưa có số liệu chủ đề',
        moTa: 'Cụm chủ đề được tính theo mẻ hằng đêm từ nội dung hội thoại.',
      }}
    />
  )
}
