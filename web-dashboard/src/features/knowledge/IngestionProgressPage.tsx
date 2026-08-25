import { format } from 'date-fns'
import { Check, Loader2 } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { useChiTietTaiLieuQuery, useDanhSachCongViecNapQuery } from '@/api/knowledge'
import { StatusPage, type TrangThaiTrang } from '@/components/layout/StatusPage'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { StatusChip } from '@/components/ui/status-chip'
import { HangThongTin } from '@/components/layout/DetailPage'
import { CHUOI_NAP, NHAN_TRANG_THAI_NAP } from '@/features/knowledge/nhan'
import { tienVnd } from '@/features/ai-agent/nhan'
import { cn } from '@/utils/cn'
import type { CongViecNap } from '@/types/schema'

const DANG_CHAY = ['QUEUED', 'EXTRACTING', 'CHUNKING', 'EMBEDDING', 'INDEXING'] as const

function dangChay(c: CongViecNap | null | undefined): boolean {
  return c != null && (DANG_CHAY as readonly string[]).includes(c.state)
}

/**
 * SCR033 — tiến độ nạp tài liệu. Mẫu M6.
 *
 * Một màn, hai đường vào: `/tri-thuc/tai-lieu/:id/tien-do` theo dõi đúng tài liệu vừa tải lên,
 * còn `/tri-thuc/tien-do` theo dõi việc đang chạy đầu hàng đợi. Cả hai cùng một câu hỏi — "xong
 * chưa" — nên tách thành hai màn là nhân đôi chỗ phải sửa mà không thêm gì.
 *
 * **Chỉ hỏi lại máy chủ khi còn việc đang chạy.** Đường ống nạp mất vài chục giây; để nguyên
 * `pollingInterval` sau khi việc đã xong là gõ cửa máy chủ mãi mãi cho một màn không còn đổi.
 */
export function IngestionProgressPage() {
  const { id } = useParams()
  const dieuHuong = useNavigate()

  const taiLieu = useChiTietTaiLieuQuery(id ?? '', { skip: !id })
  const viecCuaTaiLieu = taiLieu.currentData?.latestJob ?? null

  const hangDoi = useDanhSachCongViecNapQuery(
    { co: 8 },
    // Trang hàng đợi luôn phải hỏi lại; trang một tài liệu chỉ cần hàng đợi làm nền, không cần dồn dập
    { pollingInterval: id ? 0 : 2_500 },
  )
  const viecDangChay = hangDoi.data?.items.find((c) => dangChay(c)) ?? hangDoi.data?.items[0] ?? null
  const viec = id ? viecCuaTaiLieu : viecDangChay

  // Đường vào theo tài liệu tự hỏi lại chừng nào việc của **chính nó** chưa kết thúc
  useChiTietTaiLieuQuery(id ?? '', {
    skip: !id || !dangChay(viecCuaTaiLieu),
    pollingInterval: 2_000,
  })

  const trangThai: TrangThaiTrang = !viec
    ? 'thanh-cong'
    : viec.state === 'DONE'
      ? 'thanh-cong'
      : viec.state === 'FAILED'
        ? 'that-bai'
        : viec.state === 'PAUSED'
          ? 'cho-thao-tac'
          : 'dang-xu-ly'

  const tieuDe = !viec
    ? 'Hàng đợi nạp đang trống'
    : viec.state === 'DONE'
      ? 'Đã nạp xong tài liệu'
      : viec.state === 'FAILED'
        ? 'Nạp tài liệu thất bại'
        : viec.state === 'PAUSED'
          ? 'Việc nạp đang tạm dừng'
          : 'Đang nạp tài liệu vào kho tri thức'

  const moTa = !viec
    ? 'Không có tài liệu nào đang chờ nạp. Tải lên tài liệu mới để bắt đầu.'
    : viec.state === 'DONE'
      ? `${viec.documentTitle ?? 'Tài liệu'} đã có ${(viec.chunksCreated ?? 0).toLocaleString('vi-VN')} đoạn trong chỉ mục và sẵn sàng để tác tử AI truy hồi.`
      : viec.state === 'FAILED'
        ? (viec.errorMessage ?? 'Đường ống nạp dừng lại vì lỗi không xác định.')
        : `${viec.documentTitle ?? 'Tài liệu'} đang đi qua đường ống nạp. Có thể rời khỏi trang này — quá trình vẫn chạy nền.`

  return (
    <StatusPage
      trangThai={trangThai}
      tieuDe={tieuDe}
      moTa={moTa}
      thaoTacChinh={
        viec?.state === 'DONE' && viec.documentId
          ? {
              nhan: 'Xem các đoạn đã tách',
              onClick: () => dieuHuong(`/tri-thuc/tai-lieu/${viec.documentId}`),
            }
          : { nhan: 'Về kho tri thức', onClick: () => dieuHuong('/tri-thuc') }
      }
      thaoTacPhu={
        viec?.state === 'DONE' ? { nhan: 'Về kho tri thức', onClick: () => dieuHuong('/tri-thuc') } : undefined
      }
      chiTiet={
        <div className="flex flex-col gap-3 text-left">
          {viec && <BuocNap viec={viec} />}
          {viec && <ThongSoViec viec={viec} />}
          {!id && (hangDoi.data?.totalItems ?? 0) > 1 && (
            <HangDoi
              danhSach={(hangDoi.data?.items ?? []).filter((c) => c.id !== viec?.id).slice(0, 5)}
            />
          )}
        </div>
      }
    />
  )
}

/** Sáu bước của đường ống, hiện thẳng chứ không gộp thành một vòng xoay vô nghĩa. */
function BuocNap({ viec }: { viec: CongViecNap }) {
  const viTri = CHUOI_NAP.indexOf(viec.state)
  const hong = viec.state === 'FAILED'
  const tyLe = hong ? 100 : ((viTri + 1) / CHUOI_NAP.length) * 100

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <span className="text-[13px] font-medium">
            {NHAN_TRANG_THAI_NAP[viec.state].nhan}
          </span>
          <span className="text-muted-foreground text-xs tabular-nums">
            {hong ? 'Dừng ở bước lỗi' : `Bước ${Math.max(viTri + 1, 1)}/${CHUOI_NAP.length}`}
          </span>
        </div>
        <Progress value={tyLe} className={cn('h-1.5', hong && '[&>*]:bg-destructive')} />
        <ol className="flex flex-col gap-1.5">
          {CHUOI_NAP.map((b, i) => {
            const xong = viTri > i && !hong
            const dang = viTri === i && !hong
            return (
              <li key={b} className="flex items-center gap-2 text-xs">
                <span
                  className={cn(
                    'flex size-4 shrink-0 items-center justify-center rounded-full',
                    xong
                      ? 'bg-success/15 text-success'
                      : dang
                        ? 'bg-primary/15 text-primary'
                        : 'bg-muted text-muted-foreground',
                  )}
                >
                  {xong ? (
                    <Check className="size-2.5" />
                  ) : dang ? (
                    <Loader2 className="size-2.5 animate-spin" />
                  ) : (
                    <span className="tabular-nums">{i + 1}</span>
                  )}
                </span>
                <span className={cn(dang ? 'font-medium' : 'text-muted-foreground')}>
                  {NHAN_TRANG_THAI_NAP[b].nhan}
                </span>
              </li>
            )
          })}
        </ol>
      </CardContent>
    </Card>
  )
}

function ThongSoViec({ viec }: { viec: CongViecNap }) {
  return (
    <Card>
      <CardContent className="flex flex-col">
        <HangThongTin nhan="Nguồn kích hoạt">
          {viec.trigger === 'UPLOAD'
            ? 'Tải lên mới'
            : viec.trigger === 'REINDEX'
              ? 'Nạp lại thủ công'
              : 'Thay thế bản cũ'}
        </HangThongTin>
        <HangThongTin nhan="Lần thử">
          <span className="tabular-nums">{viec.attempt}</span>
        </HangThongTin>
        <HangThongTin nhan="Số đoạn đã tạo">
          <span className="tabular-nums">
            {(viec.chunksCreated ?? 0).toLocaleString('vi-VN')}
          </span>
        </HangThongTin>
        <HangThongTin nhan="Token đã dùng">
          <span className="tabular-nums">{(viec.tokensUsed ?? 0).toLocaleString('vi-VN')}</span>
        </HangThongTin>
        <HangThongTin nhan="Chi phí nhúng">{tienVnd(viec.costVnd)}</HangThongTin>
        <HangThongTin nhan="Bắt đầu">
          {viec.startedAt ? format(new Date(viec.startedAt), 'HH:mm:ss dd/MM/yyyy') : 'Chưa chạy'}
        </HangThongTin>
        {viec.finishedAt && (
          <HangThongTin nhan="Kết thúc">
            {format(new Date(viec.finishedAt), 'HH:mm:ss dd/MM/yyyy')}
          </HangThongTin>
        )}
        {viec.errorCode && (
          <HangThongTin nhan="Mã lỗi">
            <span className="text-destructive font-mono text-xs">{viec.errorCode}</span>
          </HangThongTin>
        )}
      </CardContent>
    </Card>
  )
}

function HangDoi({ danhSach }: { danhSach: CongViecNap[] }) {
  if (danhSach.length === 0) return null
  return (
    <Card>
      <CardContent className="flex flex-col gap-2">
        <span className="text-muted-foreground text-xs">Việc khác trong hàng đợi</span>
        {danhSach.map((c) => {
          const tt = NHAN_TRANG_THAI_NAP[c.state]
          return (
            <div key={c.id} className="flex items-center gap-2">
              <span className="min-w-0 flex-1 truncate text-[13px]">
                {c.documentTitle ?? 'Tài liệu không tên'}
              </span>
              <StatusChip sacThai={tt.sacThai}>{tt.nhan}</StatusChip>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
