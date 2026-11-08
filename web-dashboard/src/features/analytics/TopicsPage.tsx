import type { SortingState } from '@tanstack/react-table'
import { Boxes, MessagesSquare, Tags, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'

import { format } from 'date-fns'

import { useKyPhanCumQuery, useThongKeChuDeQuery } from '@/api/analytics'
import { laLoiTruyVan } from '@/api/baseQuery'
import { ListPage } from '@/components/layout/ListPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { CotBang } from '@/components/ui/data-table'
import { Progress } from '@/components/ui/progress'
import { StatusChip } from '@/components/ui/status-chip'
import type { Page } from '@/types/api'
import type { KyPhanCum, ThongKeChuDe } from '@/types/schema'
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

type Lop = ThongKeChuDe['dimension']

const MO_TA: Record<Lop, string> = {
  INTENT:
    'Nhóm theo 7 ý định của bộ định tuyến. Đếm theo hội thoại, sắp mặc định theo tỉ lệ từ chối — chỗ tác tử đang bí, không phải chỗ khách hỏi nhiều.',
  CLUSTER:
    'Nhóm theo cụm ngữ nghĩa, tính hằng tuần; tên cụm do mô hình đặt. Cụm thay đổi giữa các kỳ nên không so một cụm qua nhiều kỳ.',
}

/** Ngưỡng hội thoại tối thiểu của đặc tả UC038 — kỳ chạy với ngưỡng thấp hơn phải nói ra. */
const NGUONG_DAC_TA = 200

const NGUON_VECTOR: Record<string, string> = {
  'bge-m3': 'gom theo nghĩa câu (bge-m3)',
  'router-tfidf-ngram': 'gom theo CHỮ (n-gram của router) — nguồn thay thế, chưa phải theo nghĩa',
}

const DAT_TEN: Record<string, string> = {
  llm: 'tên do mô hình ngôn ngữ đặt',
  'tu-khoa': 'tên lấy từ từ khoá hay gặp',
  'hon-hop': 'tên do mô hình đặt, cụm nào hỏng thì lấy từ khoá',
}

/** Một câu cho biết kỳ phân cụm đang dùng — hoặc vì sao chưa có cụm. Không bao giờ để bảng trống câm. */
function moTaKy(ky: KyPhanCum | null | undefined): string | undefined {
  if (ky === undefined) return undefined
  if (ky === null) return 'Chưa có kỳ phân cụm nào. Kỳ chạy hằng tuần, tách riêng từng doanh nghiệp.'
  const ngay = format(new Date(ky.startedAt), 'dd/MM/yyyy HH:mm')
  const nguong =
    ky.minConversations < NGUONG_DAC_TA
      ? ` Ngưỡng đã hạ còn ${ky.minConversations} hội thoại để trình diễn (đặc tả: ${NGUONG_DAC_TA}).`
      : ''
  if (ky.status !== 'DONE') {
    const lyDo =
      ky.skipReason === 'TOO_FEW_CONVERSATIONS'
        ? `chỉ có ${ky.conversationCount} hội thoại, cần tối thiểu ${ky.minConversations}`
        : ky.skipReason === 'EMBED_UNAVAILABLE'
          ? 'dịch vụ biến câu thành vector chưa sẵn sàng'
          : 'dịch vụ phân cụm lỗi'
    return `Kỳ ${ngay} bỏ qua: ${lyDo}.${nguong}`
  }
  const nguon = NGUON_VECTOR[ky.vectorSource ?? ''] ?? ky.vectorSource
  const ten = DAT_TEN[ky.namingMethod ?? ''] ?? ky.namingMethod
  return `Kỳ ${ngay}: ${ky.k} cụm từ ${ky.conversationCount} hội thoại, ${nguon}; ${ten}.${nguong}`
}

/**
 * SCR052 — thống kê chủ đề hội thoại (UC038). Mẫu M1.
 *
 * Hai lớp: **ý định** (7 nhãn router, có ngay từ lượt đầu) và **cụm ngữ nghĩa** (công việc phân cụm hằng
 * tuần — cho thấy khách thật sự hỏi gì ngoài 7 nhãn định sẵn).
 *
 * Cột đáng giá nhất là **tỉ lệ từ chối**, không phải số hội thoại: một chủ đề hỏi nhiều mà tác tử
 * trả lời tốt thì không cần làm gì; một chủ đề hỏi ít mà từ chối 34% là một lỗ hổng trong kho tri
 * thức, và nó phải nổi bật lên dù nằm cuối bảng theo số lượng.
 */
export function TopicsPage() {
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'refusalRate', desc: true }])
  const [lop, datLop] = useState<Lop>('INTENT')
  const truyVan = useThongKeChuDeQuery({ lop })
  const ky = useKyPhanCumQuery(undefined, { skip: lop !== 'CLUSTER' })

  /** Số liệu về theo từng ngày — gộp lại theo chủ đề trước khi hiển thị. */
  const trang: Page<DongChuDe> | undefined = useMemo(() => {
    if (!truyVan.data) return undefined
    const gop = new Map<string, DongChuDe>()
    for (const d of truyVan.data) {
      const cu = gop.get(d.topicKey) ?? {
        id: d.topicKey,
        topicLabel: d.topicLabel,
        conversationCount: 0,
        botResolvedCount: 0,
        refusalCount: 0,
      }
      cu.conversationCount += d.conversationCount
      cu.botResolvedCount += d.botResolvedCount ?? 0
      cu.refusalCount += d.refusalCount ?? 0
      gop.set(d.topicKey, cu)
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
        // Nhãn cụm do mô hình đặt trên nội dung khách — chỉ hiển thị như văn bản thuần
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

  const loi = truyVan.error && laLoiTruyVan(truyVan.error) ? truyVan.error : undefined
  const thongTinKy = lop === 'CLUSTER' ? moTaKy(ky.data) : undefined

  return (
    <>
      {(loi || thongTinKy) && (
        <div className="px-4 pt-4 md:px-6">
          {/* Lỗi khác với "chưa có cụm" — không hiện bảng rỗng khi không lấy được dữ liệu */}
          <Alert variant={loi ? 'destructive' : 'default'}>
            <AlertDescription>{loi ? loi.message : thongTinKy}</AlertDescription>
          </Alert>
        </div>
      )}
      <ListPage
        tieuDe="Chủ đề hội thoại"
        moTa={MO_TA[lop]}
        thaoTacPhu={[
          {
            nhan: 'Theo ý định',
            BieuTuong: Tags,
            bienThe: lop === 'INTENT' ? 'default' : 'outline',
            onClick: () => datLop('INTENT'),
          },
          {
            nhan: 'Theo cụm chủ đề',
            BieuTuong: Boxes,
            bienThe: lop === 'CLUSTER' ? 'default' : 'outline',
            onClick: () => datLop('CLUSTER'),
          },
        ]}
        cot={cot}
        trang={loi ? undefined : trang}
        dangTai={truyVan.isFetching}
        sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
        onDoiTrang={() => {}}
        khiChuaCoDuLieu={{
          BieuTuong: MessagesSquare,
          tieuDe: 'Chưa có số liệu chủ đề',
          moTa:
            lop === 'INTENT'
              ? 'Số liệu xuất hiện ngay sau lượt chat đầu tiên mà tác tử AI xử lý.'
              : 'Cụm chủ đề được tính hằng tuần, khi doanh nghiệp có đủ hội thoại trong 30 ngày gần nhất.',
        }}
      />
    </>
  )
}
