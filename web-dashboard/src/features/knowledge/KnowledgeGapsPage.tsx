import { formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { MessageCircleQuestion, Users } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useDanhSachKhoangTrongQuery } from '@/api/knowledge'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { NHAN_LOAI_KHOANG_TRONG } from '@/features/knowledge/nhan'
import type { KhoangTrongTriThuc, LoaiKhoangTrong } from '@/types/schema'

/**
 * SCR034 — khoảng trống tri thức. Mẫu M1.
 *
 * Sắp mặc định theo **số khách khác nhau**, không phải số lần hỏi. Một khách hỏi đi hỏi lại mười
 * lần vì chưa hiểu câu trả lời là một vấn đề khác hẳn mười khách cùng hỏi một câu — và chỉ vấn đề
 * thứ hai mới đáng bỏ công viết thêm tài liệu.
 *
 * Loại khoảng trống quyết định cách xử lý, nên nó không chỉ là một nhãn phân loại:
 * `OUT_OF_SCOPE_DATA` cần nối công cụ MCP chứ viết bao nhiêu tài liệu cũng không giải quyết được.
 *
 * **Không có thao tác đánh dấu đã xử lý.** Danh sách này là truy vấn gộp trên `ai_interactions`
 * chứ không phải một bảng có trạng thái riêng, và không use case nào cho phép đóng một mục bằng
 * tay: một khoảng trống tự biến mất khi tài liệu mới được nạp và lượt từ chối ngừng phát sinh.
 * Nút "đã xử lý" ở đây sẽ là lời nói dối — nó ẩn dòng đi mà không sửa gì trong kho tri thức.
 *
 * GD2: **không có ô tìm kiếm và không sắp lại theo cột** — máy chủ không nhận `q` và luôn sắp theo số
 * khách rồi số lần (đặc tả UC025 8.1). Để ô tìm hay mũi tên sắp xếp ở đây là giao diện hứa một việc máy
 * chủ không làm. "Số khách" xấp xỉ bằng số hội thoại khác nhau: lượt xử lý AI không lưu mã khách.
 */
export function KnowledgeGapsPage() {
  const dieuHuong = useNavigate()
  const [boLoc, datBoLoc] = useState<{
    loai?: LoaiKhoangTrong
    trang?: number
  }>({ trang: 0 })

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
        header: 'Số khách hỏi (≈)',
        cell: ({ row }) => (
          <span
            className="flex items-center gap-1.5 font-medium tabular-nums"
            title="Xấp xỉ theo số hội thoại khác nhau"
          >
            <Users className="text-muted-foreground size-3.5" />
            {row.original.distinctContactCount.toLocaleString('vi-VN')}
          </span>
        ),
      },
      {
        id: 'occurrenceCount',
        accessorKey: 'occurrenceCount',
        header: 'Số lần hỏi',
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {row.original.occurrenceCount.toLocaleString('vi-VN')}
          </span>
        ),
      },
      {
        id: 'lastSeenAt',
        accessorKey: 'lastSeenAt',
        header: 'Gặp gần nhất',
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

  return (
    <ListPage
      tieuDe="Khoảng trống tri thức"
      moTa="Những câu khách hỏi mà kho tri thức không trả lời được trong 30 ngày qua. Sắp theo số khách khác nhau — tín hiệu mạnh hơn số lần hỏi. Số khách xấp xỉ theo số hội thoại."
      cot={cot}
      trang={truyVan.data}
      dangTai={truyVan.isLoading}
      loi={truyVan.error}
      onThuLai={() => void truyVan.refetch()}
      boLoc={[
        {
          khoa: 'loai',
          nhan: 'Loại',
          luaChon: Object.entries(NHAN_LOAI_KHOANG_TRONG).map(([giaTri, v]) => ({
            giaTri,
            nhan: v.nhan,
          })),
        },
      ]}
      giaTriBoLoc={{ loai: boLoc.loai }}
      onDoiBoLoc={(_khoa, giaTri) =>
        datBoLoc((cu) => ({ ...cu, trang: 0, loai: giaTri as LoaiKhoangTrong }))
      }
      onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
      onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
      thaoTacChinh={{
        nhan: 'Tải lên tài liệu bổ sung',
        onClick: () => dieuHuong('/tri-thuc'),
      }}
      khiChuaCoDuLieu={{
        BieuTuong: MessageCircleQuestion,
        tieuDe: 'Chưa ghi nhận khoảng trống nào',
        moTa: 'Mỗi lần tác tử AI từ chối vì không đủ căn cứ, câu hỏi được gom vào đây.',
      }}
    />
  )
}
