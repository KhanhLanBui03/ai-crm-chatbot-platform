import { formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { Sparkles, Target, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useDanhSachLeadQuery, type BoLocLead } from '@/api/sales'
import { useAppSelector } from '@/app/store/hooks'
import { ListPage } from '@/components/layout/ListPage'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { CreateLeadDialog } from '@/features/leads/CreateLeadDialog'
import {
  NHAN_MUC_DO,
  NHAN_TRANG_THAI_LEAD,
  sacThaiDiem,
  tienGon,
} from '@/features/leads/nhan'
import type { Lead } from '@/types/schema'

/**
 * SCR041 — danh sách cơ hội tiềm năng. Màn chữ ký, dựng trên mẫu M1.
 *
 * Sắp mặc định theo **điểm giảm dần**, không phải theo ngày tạo: giá trị của màn này là trả lời
 * "gọi ai trước", và câu trả lời đó nằm ở điểm chứ không ở thứ tự thời gian.
 *
 * Thứ tự do MÁY CHỦ quyết định (điểm giảm dần, lead chưa chấm điểm xếp cuối — UC032 bước 3), nên
 * các cột không bấm để sắp: sắp lại trên một trang 10 dòng là sắp sai cả danh sách.
 */
export function LeadsPage() {
  const dieuHuong = useNavigate()
  const [moTao, datMoTao] = useState(false)
  const [boLoc, datBoLoc] = useState<BoLocLead>({ trang: 0 })
  const toi = useAppSelector((s) => s.auth.nguoiDung)

  const truyVan = useDanhSachLeadQuery(boLoc)

  const cot = useMemo<CotBang<Lead>[]>(
    () => ([
      {
        id: 'currentScore',
        accessorKey: 'currentScore',
        header: 'Điểm',
        cell: ({ row }) => {
          const l = row.original
          if (l.currentScore == null) {
            return <span className="text-muted-foreground text-[13px]">Chưa chấm điểm</span>
          }
          return (
            <StatusChip sacThai={sacThaiDiem(l.currentScore)}>
              <span className="tabular-nums">{l.currentScore}</span>
            </StatusChip>
          )
        },
      },
      {
        id: 'contactName',
        accessorKey: 'contactName',
        header: 'Khách hàng',
        cell: ({ row }) => {
          const l = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="truncate font-medium">{l.contactName}</span>
              <span className="text-muted-foreground truncate text-xs">
                {l.contactPhone ?? 'Chưa có số'}
              </span>
            </div>
          )
        },
      },
      {
        id: 'interestedProduct',
        accessorKey: 'interestedProduct',
        header: 'Quan tâm',
        cell: ({ row }) => (
          <span className="text-[13px]">{row.original.interestedProduct ?? '—'}</span>
        ),
      },
      {
        id: 'budget',
        header: 'Ngân sách',
        cell: ({ row }) => {
          const l = row.original
          if (l.budgetMin == null && l.budgetMax == null) {
            return <span className="text-muted-foreground">Chưa rõ</span>
          }
          return (
            <span className="tabular-nums">
              {tienGon(l.budgetMin)} – {tienGon(l.budgetMax)}
            </span>
          )
        },
      },
      {
        id: 'urgency',
        accessorKey: 'urgency',
        header: 'Mức gấp',
        cell: ({ row }) => {
          const u = row.original.urgency
          return u ? (
            <span className="text-muted-foreground text-[13px]">{NHAN_MUC_DO[u]}</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )
        },
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const t = NHAN_TRANG_THAI_LEAD[row.original.status]
          return <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
        },
      },
      {
        id: 'source',
        accessorKey: 'source',
        header: 'Nguồn',
        cell: ({ row }) =>
          row.original.source === 'AI_AUTO' ? (
            <StatusChip sacThai="info" BieuTuong={Sparkles}>
              Tác tử AI
            </StatusChip>
          ) : (
            <StatusChip>Nhập tay</StatusChip>
          ),
      },
      {
        id: 'ownerName',
        accessorKey: 'ownerName',
        header: 'Phụ trách',
        cell: ({ row }) => {
          const l = row.original
          // Cơ hội chưa ai nhận là cơ hội đang nguội đi — phải nổi bật, không phải một gạch ngang
          return l.ownerName ? (
            <span className="text-[13px]">{l.ownerName}</span>
          ) : (
            <span className="text-destructive flex items-center gap-1 text-[13px]">
              <TriangleAlert className="size-3.5" />
              Chưa ai nhận
            </span>
          )
        },
      },
      {
        id: 'createdAt',
        accessorKey: 'createdAt',
        header: 'Tạo lúc',
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {formatDistanceToNowStrict(new Date(row.original.createdAt), {
              locale: vi,
              addSuffix: true,
            })}
          </span>
        ),
      },
    ] satisfies CotBang<Lead>[]).map((c): CotBang<Lead> => ({ ...c, enableSorting: false })),
    [],
  )

  return (
    <>
      <ListPage
        tieuDe="Lead"
        moTa="Sắp theo điểm giảm dần — trả lời câu hỏi gọi ai trước, không phải ai đến trước."
        cot={cot}
        trang={truyVan.data}
        dangTai={truyVan.isLoading}
        onChonDong={(l) => dieuHuong(`/ban-hang/co-hoi-tiem-nang/${l.id}`)}
        timKiem={{
          goiY: 'Tìm theo tên hoặc số điện thoại khách…',
          giaTri: boLoc.tuKhoa ?? '',
          onDoi: (v) => datBoLoc((cu) => ({ ...cu, tuKhoa: v, trang: 0 })),
        }}
        boLoc={[
          {
            khoa: 'trangThai',
            nhan: 'Trạng thái',
            luaChon: Object.entries(NHAN_TRANG_THAI_LEAD).map(([giaTri, v]) => ({
              giaTri,
              nhan: v.nhan,
            })),
          },
          {
            khoa: 'nguon',
            nhan: 'Nguồn',
            luaChon: [
              { giaTri: 'AI_AUTO', nhan: 'Tác tử AI tạo' },
              { giaTri: 'MANUAL', nhan: 'Nhập tay' },
            ],
          },
          {
            khoa: 'chuSoHuu',
            nhan: 'Phụ trách',
            luaChon: toi ? [{ giaTri: toi.id, nhan: 'Của tôi' }] : [],
          },
          {
            khoa: 'diemToiThieu',
            nhan: 'Điểm từ',
            luaChon: [
              { giaTri: '80', nhan: '80 trở lên' },
              { giaTri: '60', nhan: '60 trở lên' },
            ],
          },
        ]}
        giaTriBoLoc={{
          trangThai: boLoc.trangThai,
          nguon: boLoc.nguon,
          chuSoHuu: boLoc.chuSoHuu,
          diemToiThieu: boLoc.diemToiThieu?.toString(),
        }}
        onDoiBoLoc={(khoa, giaTri) =>
          datBoLoc((cu) => ({
            ...cu,
            trang: 0,
            ...(khoa === 'trangThai'
              ? { trangThai: giaTri as BoLocLead['trangThai'] }
              : khoa === 'nguon'
                ? { nguon: giaTri as BoLocLead['nguon'] }
                : khoa === 'chuSoHuu'
                  ? { chuSoHuu: giaTri || undefined }
                  : { diemToiThieu: giaTri ? Number(giaTri) : undefined }),
          }))
        }
        onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
        onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
        thaoTacChinh={{ nhan: 'Tạo lead', onClick: () => datMoTao(true) }}
        khiChuaCoDuLieu={{
          BieuTuong: Target,
          tieuDe: 'Chưa có lead nào',
          moTa: 'Bấm "Tạo lead" để nhập tay, hoặc tạo từ một hội thoại trong Hộp thư.',
        }}
      />

      <CreateLeadDialog mo={moTao} onDoiMo={datMoTao} />
    </>
  )
}
