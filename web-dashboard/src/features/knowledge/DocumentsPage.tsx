import type { SortingState } from '@tanstack/react-table'
import { format } from 'date-fns'
import { BookOpen, TriangleAlert, Upload } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { useDanhSachTaiLieuQuery, useXoaTaiLieuMutation, type BoLocTaiLieu } from '@/api/knowledge'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { UploadDocumentDialog } from '@/features/knowledge/UploadDocumentDialog'
import {
  coTep,
  NHAN_LOAI_NGUON,
  NHAN_TRANG_THAI_TAI_LIEU,
} from '@/features/knowledge/nhan'
import type { TaiLieu } from '@/types/schema'

/**
 * SCR030 — danh sách tài liệu tri thức. Mẫu M1.
 *
 * Cột **số đoạn** đứng cạnh cột trạng thái là có chủ đích: một tài liệu `READY` mà số đoạn bằng 0
 * nghĩa là đường ống chạy xong nhưng không trích được chữ nào — thường là bản quét ảnh. Nhìn riêng
 * cột trạng thái thì tình huống đó trông y hệt một tài liệu bình thường.
 */
export function DocumentsPage() {
  const dieuHuong = useNavigate()
  const [moTaiLen, datMoTaiLen] = useState(false)
  const [boLoc, datBoLoc] = useState<BoLocTaiLieu>({ trang: 0 })
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'createdAt', desc: true }])
  const [xoa] = useXoaTaiLieuMutation()

  const truyVan = useDanhSachTaiLieuQuery(boLoc)

  const cot = useMemo<CotBang<TaiLieu>[]>(
    () => [
      {
        id: 'title',
        accessorKey: 'title',
        header: 'Tài liệu',
        enableSorting: true,
        cell: ({ row }) => {
          const t = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="truncate font-medium">{t.title}</span>
              <span className="text-muted-foreground truncate text-xs">{t.fileName}</span>
            </div>
          )
        },
      },
      {
        id: 'sourceType',
        accessorKey: 'sourceType',
        header: 'Định dạng',
        cell: ({ row }) => (
          <span className="text-muted-foreground text-[13px]">
            {NHAN_LOAI_NGUON[row.original.sourceType]}
          </span>
        ),
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const t = row.original
          const tt = NHAN_TRANG_THAI_TAI_LIEU[t.status]
          return (
            <div className="flex min-w-0 flex-col gap-1">
              <StatusChip sacThai={tt.sacThai} BieuTuong={tt.BieuTuong}>
                {tt.nhan}
              </StatusChip>
              {t.errorMessage && (
                <span className="text-destructive line-clamp-2 max-w-64 text-xs">
                  {t.errorMessage}
                </span>
              )}
            </div>
          )
        },
      },
      {
        id: 'chunkCount',
        accessorKey: 'chunkCount',
        header: 'Số đoạn',
        enableSorting: true,
        cell: ({ row }) => {
          const t = row.original
          if (t.status === 'READY' && t.chunkCount === 0) {
            return (
              <span className="text-destructive flex items-center gap-1 text-[13px]">
                <TriangleAlert className="size-3.5" />0 đoạn
              </span>
            )
          }
          return <span className="tabular-nums">{t.chunkCount.toLocaleString('vi-VN')}</span>
        },
      },
      {
        id: 'sizeBytes',
        accessorKey: 'sizeBytes',
        header: 'Dung lượng',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">{coTep(row.original.sizeBytes)}</span>
        ),
      },
      {
        id: 'version',
        accessorKey: 'version',
        header: 'Phiên bản',
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">v{row.original.version ?? 1}</span>
        ),
      },
      {
        id: 'uploadedByName',
        accessorKey: 'uploadedByName',
        header: 'Người tải lên',
        cell: ({ row }) => (
          <span className="text-[13px]">{row.original.uploadedByName ?? '—'}</span>
        ),
      },
      {
        id: 'createdAt',
        accessorKey: 'createdAt',
        header: 'Tải lên',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {format(new Date(row.original.createdAt), 'dd/MM/yyyy HH:mm')}
          </span>
        ),
      },
    ],
    [],
  )

  return (
    <>
      <ListPage
        tieuDe="Kho tri thức"
        moTa="Tác tử AI chỉ trả lời dựa trên tài liệu ở đây. Không có tài liệu thì nó từ chối chứ không đoán."
        cot={cot}
        trang={truyVan.data}
        dangTai={truyVan.isLoading}
        onChonDong={(t) => dieuHuong(`/tri-thuc/tai-lieu/${t.id}`)}
        timKiem={{
          goiY: 'Tìm theo tiêu đề, mô tả hoặc tên tệp…',
          giaTri: boLoc.tuKhoa ?? '',
          onDoi: (v) => datBoLoc((cu) => ({ ...cu, tuKhoa: v, trang: 0 })),
        }}
        boLoc={[
          {
            khoa: 'trangThai',
            nhan: 'Trạng thái',
            luaChon: Object.entries(NHAN_TRANG_THAI_TAI_LIEU).map(([giaTri, v]) => ({
              giaTri,
              nhan: v.nhan,
            })),
          },
          {
            khoa: 'loaiNguon',
            nhan: 'Định dạng',
            luaChon: Object.entries(NHAN_LOAI_NGUON).map(([giaTri, nhan]) => ({ giaTri, nhan })),
          },
        ]}
        giaTriBoLoc={{ trangThai: boLoc.trangThai, loaiNguon: boLoc.loaiNguon }}
        onDoiBoLoc={(khoa, giaTri) =>
          datBoLoc((cu) => ({
            ...cu,
            trang: 0,
            ...(khoa === 'trangThai'
              ? { trangThai: giaTri as BoLocTaiLieu['trangThai'] }
              : { loaiNguon: giaTri as BoLocTaiLieu['loaiNguon'] }),
          }))
        }
        onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
        sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
        onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
        thaoTacChinh={{
          nhan: 'Tải lên tài liệu',
          BieuTuong: Upload,
          onClick: () => datMoTaiLen(true),
        }}
        thaoTacPhu={[
          { nhan: 'Tiến độ nạp', onClick: () => dieuHuong('/tri-thuc/tien-do') },
          { nhan: 'Khoảng trống', onClick: () => dieuHuong('/tri-thuc/khoang-trong') },
          { nhan: 'Tìm thử', onClick: () => dieuHuong('/tri-thuc/tim-thu') },
        ]}
        thaoTacHangLoat={[
          {
            nhan: 'Xoá khỏi kho',
            nguyHiem: true,
            onClick: async (ids) => {
              await Promise.all(ids.map((id) => xoa(id).unwrap()))
              toast.success(`Đã xoá ${ids.length} tài liệu khỏi kho tri thức.`)
            },
          },
        ]}
        khiChuaCoDuLieu={{
          BieuTuong: BookOpen,
          tieuDe: 'Kho tri thức đang trống',
          moTa: 'Tải lên chính sách, bảng giá hoặc câu hỏi thường gặp để tác tử AI có căn cứ trả lời.',
        }}
      />

      <UploadDocumentDialog mo={moTaiLen} onDoiMo={datMoTaiLen} />
    </>
  )
}
