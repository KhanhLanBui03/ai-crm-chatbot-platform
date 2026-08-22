import { ChevronLeft, FileText, RefreshCw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import {
  useChiTietTaiLieuQuery,
  useDanhSachDoanQuery,
  useNapLaiTaiLieuMutation,
} from '@/api/knowledge'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { coTep, NHAN_LOAI_NGUON } from '@/features/knowledge/nhan'
import type { DoanTaiLieu } from '@/types/schema'

/**
 * SCR032 — các đoạn của một tài liệu. Mẫu M1.
 *
 * Đây là màn để trả lời "vì sao truy hồi trả về đoạn này": người xem đọc đúng khối văn bản mà mô
 * hình nhận được, kèm đường mục và số token. Không hiển thị vector nhúng — 1024 chiều số thực
 * không nói được gì cho người đọc mà tốn vài chục KB mỗi đoạn.
 *
 * `embeddingVersion` nằm trên **từng đoạn**, không phải cấp tài liệu. Đổi mô hình nhúng thì hai
 * phiên bản cùng tồn tại trong lúc xây lại chỉ mục, và cột này là chỗ duy nhất nhìn ra điều đó.
 */
export function DocumentChunksPage() {
  const { id = '' } = useParams()
  const dieuHuong = useNavigate()
  const [trang, datTrang] = useState(0)
  const [napLai, ketQuaNap] = useNapLaiTaiLieuMutation()

  const taiLieu = useChiTietTaiLieuQuery(id, { skip: !id })
  const doan = useDanhSachDoanQuery({ taiLieuId: id, trang }, { skip: !id })

  const cot = useMemo<CotBang<DoanTaiLieu>[]>(
    () => [
      {
        id: 'ordinal',
        accessorKey: 'ordinal',
        header: '#',
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">{row.original.ordinal}</span>
        ),
      },
      {
        id: 'sectionPath',
        accessorKey: 'sectionPath',
        header: 'Mục',
        cell: ({ row }) => (
          <span className="text-[13px] font-medium">{row.original.sectionPath ?? '—'}</span>
        ),
      },
      {
        id: 'content',
        accessorKey: 'content',
        header: 'Nội dung đoạn',
        cell: ({ row }) => (
          <p className="text-muted-foreground max-w-2xl text-[13px] leading-relaxed">
            {row.original.content}
          </p>
        ),
      },
      {
        id: 'tokenCount',
        accessorKey: 'tokenCount',
        header: 'Token',
        cell: ({ row }) => (
          <span className="tabular-nums">
            {row.original.tokenCount?.toLocaleString('vi-VN') ?? '—'}
          </span>
        ),
      },
      {
        id: 'embeddingVersion',
        accessorKey: 'embeddingVersion',
        header: 'Mô hình nhúng',
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="text-[13px]">{row.original.embeddingModel ?? '—'}</span>
            <span className="text-muted-foreground text-xs">
              {row.original.embeddingVersion ?? '—'}
            </span>
          </div>
        ),
      },
    ],
    [],
  )

  const t = taiLieu.currentData
  const moTa = t
    ? [
        NHAN_LOAI_NGUON[t.sourceType],
        coTep(t.sizeBytes),
        `${t.chunkCount.toLocaleString('vi-VN')} đoạn`,
        t.language === 'en' ? 'Tiếng Anh' : 'Tiếng Việt',
        `v${t.version ?? 1}`,
      ].join(' · ')
    : undefined

  return (
    <ListPage
      tieuDe={t?.title ?? 'Đang tải tài liệu…'}
      moTa={moTa}
      cot={cot}
      trang={doan.data}
      dangTai={doan.isLoading || taiLieu.isLoading}
      onDoiTrang={datTrang}
      thaoTacChinh={{
        nhan: ketQuaNap.isLoading ? 'Đang xếp hàng…' : 'Nạp lại tài liệu',
        BieuTuong: RefreshCw,
        onClick: async () => {
          await napLai(id).unwrap()
          toast.success('Đã xếp tài liệu vào hàng đợi nạp lại.')
          dieuHuong(`/tri-thuc/tai-lieu/${id}/tien-do`)
        },
      }}
      thaoTacPhu={[
        {
          nhan: 'Về kho tri thức',
          BieuTuong: ChevronLeft,
          onClick: () => dieuHuong('/tri-thuc'),
        },
      ]}
      khiChuaCoDuLieu={{
        BieuTuong: FileText,
        tieuDe: 'Tài liệu chưa có đoạn nào',
        moTa: 'Đường ống nạp chưa chạy xong, hoặc chạy xong nhưng không trích được chữ nào từ tệp.',
      }}
    />
  )
}
