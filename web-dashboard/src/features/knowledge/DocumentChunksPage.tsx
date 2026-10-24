import { Archive, ChevronLeft, FileText, Pencil, RefreshCw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import {
  useChiTietTaiLieuQuery,
  useDanhSachDoanQuery,
  useNapLaiTaiLieuMutation,
  useXoaTaiLieuMutation,
} from '@/api/knowledge'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { ArchiveDocumentDialog } from '@/features/knowledge/ArchiveDocumentDialog'
import { EditDocumentDialog } from '@/features/knowledge/EditDocumentDialog'
import { coTep, NHAN_LOAI_NGUON, NHAN_TRANG_THAI_TAI_LIEU } from '@/features/knowledge/nhan'
import type { DoanTaiLieu } from '@/types/schema'

/** Câu lỗi của máy chủ (403 thiếu quyền, 409 đang nạp, 502 ai-service) — không tự viết lại. */
const cauLoi = (loi: unknown, macDinh: string) => (laLoiTruyVan(loi) ? loi.message : macDinh)

/**
 * SCR032 — các đoạn của một tài liệu. Mẫu M1.
 *
 * Đây là màn để trả lời "vì sao truy hồi trả về đoạn này": người xem đọc đúng khối văn bản mà mô
 * hình nhận được, kèm đường mục và số token. Không hiển thị vector nhúng — 1024 chiều số thực
 * không nói được gì cho người đọc mà tốn vài chục KB mỗi đoạn.
 *
 * `embeddingVersion` nằm trên **từng đoạn**, không phải cấp tài liệu. Đổi mô hình nhúng thì hai
 * phiên bản cùng tồn tại trong lúc xây lại chỉ mục, và cột này là chỗ duy nhất nhìn ra điều đó.
 *
 * Ba thao tác của UC020 bước 5 đặt ở đầu màn: sửa thông tin, nạp lại, gỡ khỏi kho. Nút không bị
 * khoá theo trạng thái — máy chủ là bên quyết định (409 khi đang nạp, 403 khi thiếu quyền) và câu
 * lỗi của nó hiện ra nguyên văn.
 */
export function DocumentChunksPage() {
  const { id = '' } = useParams()
  const dieuHuong = useNavigate()
  const [trang, datTrang] = useState(0)
  const [moSua, datMoSua] = useState(false)
  const [moGo, datMoGo] = useState(false)
  const [napLai, ketQuaNap] = useNapLaiTaiLieuMutation()
  const [go, ketQuaGo] = useXoaTaiLieuMutation()

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
        // Ô bảng mặc định không xuống dòng — để nguyên thì đoạn dài đẩy cột token và mô hình nhúng
        // (đặc tả UC020 bước 4) ra khỏi khung nhìn. Xuống dòng, giữ 3 dòng đầu; đủ để nhận ra đoạn.
        cell: ({ row }) => (
          <p
            className="text-muted-foreground line-clamp-3 max-w-xl min-w-80 text-[13px] leading-relaxed whitespace-normal"
            title={row.original.content}
          >
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
  // 404 cho cả "không tồn tại" lẫn "của doanh nghiệp khác" — máy chủ cố ý không phân biệt
  const khongThay = laLoiTruyVan(taiLieu.error) && taiLieu.error.status === 404
  // Lỗi khác (502 khi ai-service không phản hồi…) — nói thẳng, không treo ở "Đang tải"
  const loiKhac = taiLieu.isError && !khongThay ? taiLieu.error : doan.isError ? doan.error : undefined
  const thongTin = t
    ? [
        NHAN_TRANG_THAI_TAI_LIEU[t.status].nhan,
        NHAN_LOAI_NGUON[t.sourceType],
        coTep(t.sizeBytes),
        `${t.chunkCount.toLocaleString('vi-VN')} đoạn`,
        t.language === 'en' ? 'Tiếng Anh' : 'Tiếng Việt',
        `v${t.version ?? 1}`,
        t.uploadedByName ? `tải lên bởi ${t.uploadedByName}` : null,
      ]
        .filter(Boolean)
        .join(' · ')
    : undefined
  const moTa = t ? [t.description, thongTin].filter(Boolean).join(' — ') : undefined

  async function napLaiTaiLieu() {
    try {
      const viec = await napLai(id).unwrap()
      toast.success('Đã xếp tài liệu vào hàng đợi nạp lại. Bản hiện tại vẫn phục vụ tới khi bản mới xong.')
      // Bản bóng có id MỚI (ADR-0031) — theo dõi tiến độ của nó, không phải của id đang xem
      dieuHuong(`/tri-thuc/tai-lieu/${viec.documentId}/tien-do`)
    } catch (loi) {
      toast.error(cauLoi(loi, 'Không xếp được tài liệu vào hàng đợi nạp lại.'))
    }
  }

  async function goKhoiKho() {
    try {
      await go(id).unwrap()
      toast.success('Đã gỡ tài liệu khỏi kho tri thức.')
      datMoGo(false)
      dieuHuong('/tri-thuc')
    } catch (loi) {
      datMoGo(false)
      toast.error(cauLoi(loi, 'Không gỡ được tài liệu.'))
    }
  }

  const veKho = { nhan: 'Về kho tri thức', BieuTuong: ChevronLeft, onClick: () => dieuHuong('/tri-thuc') }

  return (
    <>
      <ListPage
        tieuDe={
          khongThay
            ? 'Không tìm thấy tài liệu'
            : (t?.title ?? (loiKhac ? 'Không tải được tài liệu' : 'Đang tải tài liệu…'))
        }
        moTa={khongThay ? 'Tài liệu không tồn tại hoặc đã bị xoá.' : moTa}
        cot={cot}
        trang={khongThay ? undefined : doan.data}
        dangTai={!khongThay && !loiKhac && (doan.isLoading || taiLieu.isLoading)}
        loi={loiKhac}
        onThuLai={() => {
          taiLieu.refetch()
          doan.refetch()
        }}
        onDoiTrang={datTrang}
        thaoTacChinh={
          t
            ? {
                nhan: ketQuaNap.isLoading ? 'Đang xếp hàng…' : 'Nạp lại tài liệu',
                BieuTuong: RefreshCw,
                onClick: napLaiTaiLieu,
              }
            : undefined
        }
        thaoTacPhu={
          t
            ? [
                veKho,
                { nhan: 'Sửa thông tin', BieuTuong: Pencil, onClick: () => datMoSua(true) },
                { nhan: 'Gỡ khỏi kho', BieuTuong: Archive, onClick: () => datMoGo(true) },
              ]
            : [veKho]
        }
        khiChuaCoDuLieu={{
          BieuTuong: FileText,
          tieuDe: khongThay ? 'Không có gì để hiển thị' : 'Tài liệu chưa có đoạn nào',
          moTa: khongThay
            ? 'Quay về kho tri thức để chọn tài liệu khác.'
            : 'Đường ống nạp chưa chạy xong, hoặc chạy xong nhưng không trích được chữ nào từ tệp.',
        }}
      />

      {t && <EditDocumentDialog taiLieu={t} mo={moSua} onDoiMo={datMoSua} />}
      <ArchiveDocumentDialog
        mo={moGo}
        onDoiMo={datMoGo}
        doiTuong={t?.title ?? 'tài liệu này'}
        dangXuLy={ketQuaGo.isLoading}
        onXacNhan={goKhoiKho}
      />
    </>
  )
}
