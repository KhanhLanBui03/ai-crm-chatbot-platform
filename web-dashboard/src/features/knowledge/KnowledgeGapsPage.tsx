import type { SortingState } from '@tanstack/react-table'
import { formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { MessageCircleQuestion, Users } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { useDanhDauKhoangTrongMutation, useDanhSachKhoangTrongQuery } from '@/api/knowledge'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { NHAN_LOAI_KHOANG_TRONG } from '@/features/knowledge/nhan'
import type { KhoangTrongTriThuc, LoaiKhoangTrong } from '@/types/schema'

const NHAN_TRANG_THAI: Record<string, { nhan: string; sacThai: 'warning' | 'success' | 'neutral' }> =
  {
    OPEN: { nhan: 'Chưa xử lý', sacThai: 'warning' },
    RESOLVED: { nhan: 'Đã bổ sung', sacThai: 'success' },
    IGNORED: { nhan: 'Bỏ qua', sacThai: 'neutral' },
  }

/**
 * SCR034 — khoảng trống tri thức. Mẫu M1.
 *
 * Sắp mặc định theo **số khách khác nhau**, không phải số lần hỏi. Một khách hỏi đi hỏi lại mười
 * lần vì chưa hiểu câu trả lời là một vấn đề khác hẳn mười khách cùng hỏi một câu — và chỉ vấn đề
 * thứ hai mới đáng bỏ công viết thêm tài liệu.
 *
 * Loại khoảng trống quyết định cách xử lý, nên nó không chỉ là một nhãn phân loại:
 * `OUT_OF_SCOPE_DATA` cần nối công cụ MCP chứ viết bao nhiêu tài liệu cũng không giải quyết được.
 */
export function KnowledgeGapsPage() {
  const dieuHuong = useNavigate()
  const [boLoc, datBoLoc] = useState<{
    tuKhoa?: string
    trangThai?: string
    loai?: LoaiKhoangTrong
    trang?: number
  }>({ trangThai: 'OPEN', trang: 0 })
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'distinctContactCount', desc: true }])
  const [danhDau] = useDanhDauKhoangTrongMutation()

  const truyVan = useDanhSachKhoangTrongQuery(boLoc)

  const cot = useMemo<CotBang<KhoangTrongTriThuc>[]>(
    () => [
      {
        id: 'questionText',
        accessorKey: 'questionText',
        header: 'Câu khách hỏi mà tác tử không trả lời được',
        cell: ({ row }) => (
          <p className="max-w-lg text-[13px] font-medium">{row.original.questionText}</p>
        ),
      },
      {
        id: 'gapType',
        accessorKey: 'gapType',
        header: 'Loại',
        cell: ({ row }) => {
          const l = NHAN_LOAI_KHOANG_TRONG[row.original.gapType]
          return (
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <StatusChip sacThai={l.sacThai}>{l.nhan}</StatusChip>
                </span>
              </TooltipTrigger>
              <TooltipContent className="max-w-64">{l.moTa}</TooltipContent>
            </Tooltip>
          )
        },
      },
      {
        id: 'distinctContactCount',
        accessorKey: 'distinctContactCount',
        header: 'Số khách hỏi',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="flex items-center gap-1.5 font-medium tabular-nums">
            <Users className="text-muted-foreground size-3.5" />
            {row.original.distinctContactCount.toLocaleString('vi-VN')}
          </span>
        ),
      },
      {
        id: 'occurrenceCount',
        accessorKey: 'occurrenceCount',
        header: 'Số lần hỏi',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {row.original.occurrenceCount.toLocaleString('vi-VN')}
          </span>
        ),
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const t = NHAN_TRANG_THAI[row.original.status] ?? NHAN_TRANG_THAI.OPEN
          return <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
        },
      },
      {
        id: 'lastSeenAt',
        accessorKey: 'lastSeenAt',
        header: 'Gặp gần nhất',
        enableSorting: true,
        cell: ({ row }) => {
          const l = row.original.lastSeenAt
          return (
            <span className="text-muted-foreground tabular-nums">
              {l ? formatDistanceToNowStrict(new Date(l), { locale: vi, addSuffix: true }) : '—'}
            </span>
          )
        },
      },
    ],
    [],
  )

  async function danhDauNhieu(ids: string[], status: 'RESOLVED' | 'IGNORED') {
    await Promise.all(ids.map((id) => danhDau({ id, status }).unwrap()))
    toast.success(
      status === 'RESOLVED'
        ? `Đã đánh dấu ${ids.length} khoảng trống là đã bổ sung tài liệu.`
        : `Đã bỏ qua ${ids.length} khoảng trống.`,
    )
  }

  return (
    <ListPage
      tieuDe="Khoảng trống tri thức"
      moTa="Những câu khách hỏi mà kho tri thức không trả lời được. Sắp theo số khách khác nhau — tín hiệu mạnh hơn số lần hỏi."
      cot={cot}
      trang={truyVan.data}
      dangTai={truyVan.isLoading}
      timKiem={{
        goiY: 'Tìm trong nội dung câu hỏi…',
        giaTri: boLoc.tuKhoa ?? '',
        onDoi: (v) => datBoLoc((cu) => ({ ...cu, tuKhoa: v, trang: 0 })),
      }}
      boLoc={[
        {
          khoa: 'trangThai',
          nhan: 'Trạng thái',
          luaChon: Object.entries(NHAN_TRANG_THAI).map(([giaTri, v]) => ({
            giaTri,
            nhan: v.nhan,
          })),
        },
        {
          khoa: 'loai',
          nhan: 'Loại',
          luaChon: Object.entries(NHAN_LOAI_KHOANG_TRONG).map(([giaTri, v]) => ({
            giaTri,
            nhan: v.nhan,
          })),
        },
      ]}
      giaTriBoLoc={{ trangThai: boLoc.trangThai, loai: boLoc.loai }}
      onDoiBoLoc={(khoa, giaTri) =>
        datBoLoc((cu) => ({
          ...cu,
          trang: 0,
          ...(khoa === 'trangThai' ? { trangThai: giaTri } : { loai: giaTri as LoaiKhoangTrong }),
        }))
      }
      onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
      sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
      onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
      thaoTacChinh={{
        nhan: 'Tải lên tài liệu bổ sung',
        onClick: () => dieuHuong('/tri-thuc'),
      }}
      thaoTacHangLoat={[
        { nhan: 'Đã bổ sung tài liệu', onClick: (ids) => danhDauNhieu(ids, 'RESOLVED') },
        { nhan: 'Bỏ qua', onClick: (ids) => danhDauNhieu(ids, 'IGNORED') },
      ]}
      khiChuaCoDuLieu={{
        BieuTuong: MessageCircleQuestion,
        tieuDe: 'Chưa ghi nhận khoảng trống nào',
        moTa: 'Mỗi lần tác tử AI từ chối vì không đủ căn cứ, câu hỏi được gom vào đây.',
      }}
    />
  )
}
