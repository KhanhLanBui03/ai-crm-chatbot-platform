import { ArrowRight, Hash, Search, SearchX, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useLazyTimTriThucQuery } from '@/api/knowledge'
import { laLoiTruyVan } from '@/api/baseQuery'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import type { KetQuaTruyHoi } from '@/types/schema'

const CAU_HOI_MAU = [
  'Máy giặt được bảo hành bao lâu?',
  'Đơn 300 cái thì chiết khấu bao nhiêu?',
  'Bao lâu thì được hoàn tiền?',
  'Ship về Hà Giang mất mấy ngày?',
]

/**
 * SCR031 — tìm thử trong kho tri thức. Màn chữ ký.
 *
 * Đây là màn **chứng minh ADR-0006**, không phải một ô tìm kiếm. Giá trị của nó nằm ở chỗ hiện
 * tách bạch hai thứ hạng: một đoạn có thể đứng thứ 12 ở làn từ khoá nhưng thứ 2 ở làn vector — và
 * chính những đoạn như vậy là lý do đường ống dùng hai làn thay vì một.
 *
 * Đoạn **chỉ xuất hiện ở một làn** được đánh dấu riêng. Nếu không nói ra, người xem sẽ đọc ô trống
 * thành "hạng 0" thay vì "làn kia không tìm thấy đoạn này", và kết luận ngược hẳn.
 */
export function KnowledgeSearchPage() {
  const [oNhap, datONhap] = useState('')
  const [topK, datTopK] = useState('5')
  const [tim, ketQua] = useLazyTimTriThucQuery()

  const daTim = ketQua.isUninitialized === false
  const thongDiepLoi = laLoiTruyVan(ketQua.error) ? ketQua.error.message : null

  function chay(cauHoi: string) {
    const q = cauHoi.trim()
    if (q.length < 2) return
    datONhap(q)
    tim({ tuKhoa: q, topK: Number(topK) })
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="flex max-w-4xl flex-col gap-4 p-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-semibold tracking-tight">Tìm thử trong kho tri thức</h1>
          <p className="text-muted-foreground text-[13px]">
            Chạy đúng đường ống truy hồi mà tác tử AI dùng — hai làn song song, hợp nhất RRF, rồi
            xếp hạng lại. Dùng để kiểm tra kho trước khi khách hỏi.
          </p>
        </div>

        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(su) => {
            su.preventDefault()
            chay(oNhap)
          }}
        >
          <div className="relative min-w-64 flex-1">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
            <Input
              className="pl-8"
              placeholder="Gõ câu hỏi đúng như cách khách sẽ hỏi…"
              value={oNhap}
              onChange={(e) => datONhap(e.target.value)}
            />
          </div>
          <Select value={topK} onValueChange={datTopK}>
            <SelectTrigger size="sm" className="w-auto min-w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3">Lấy 3 đoạn</SelectItem>
              <SelectItem value="5">Lấy 5 đoạn</SelectItem>
              <SelectItem value="10">Lấy 10 đoạn</SelectItem>
            </SelectContent>
          </Select>
          <Button type="submit" size="sm" disabled={oNhap.trim().length < 2 || ketQua.isFetching}>
            {ketQua.isFetching ? 'Đang truy hồi…' : 'Tìm thử'}
          </Button>
        </form>

        {!daTim && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted-foreground text-xs">Thử nhanh:</span>
            {CAU_HOI_MAU.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => chay(c)}
                className="bg-secondary text-secondary-foreground hover:bg-secondary/70 rounded-full px-2.5 py-1 text-xs transition-colors"
              >
                {c}
              </button>
            ))}
          </div>
        )}

        <DuongOng />

        {thongDiepLoi && (
          <Alert variant="destructive">
            <AlertDescription>{thongDiepLoi}</AlertDescription>
          </Alert>
        )}

        {ketQua.isFetching && (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full rounded-lg" />
            ))}
          </div>
        )}

        {!ketQua.isFetching && daTim && !thongDiepLoi && (ketQua.data?.length ?? 0) === 0 && (
          <Card>
            <CardContent>
              <EmptyState
                BieuTuong={SearchX}
                tieuDe="Không truy hồi được đoạn nào"
                moTa="Kho tri thức chưa có nội dung trả lời câu này. Với câu hỏi thật, tác tử AI sẽ từ chối và ghi lại một khoảng trống tri thức."
              />
            </CardContent>
          </Card>
        )}

        {!ketQua.isFetching && (ketQua.data?.length ?? 0) > 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-muted-foreground text-[13px]">
              {ketQua.data?.length} đoạn được đưa vào lời nhắc, xếp theo điểm sau khi xếp hạng lại.
            </p>
            {ketQua.data?.map((kq, i) => (
              <TheKetQua key={kq.chunk.id} kq={kq} thuTu={i + 1} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/** Sơ đồ đường ống, vẽ bằng chữ — ba bước đúng thứ tự ADR-0006. */
function DuongOng() {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px]">
        <Buoc nhan="Làn vector" phu="cosine trên vector nhúng" />
        <ArrowRight className="text-muted-foreground size-3.5" />
        <Buoc nhan="Hợp nhất RRF" phu="k = 60" nhanManh />
        <ArrowRight className="text-muted-foreground size-3.5" />
        <Buoc nhan="Xếp hạng lại" phu="10 ứng viên đầu" />
        <ArrowRight className="text-muted-foreground size-3.5" />
        <Buoc nhan="Đưa vào lời nhắc" phu="top-K" />
        <span className="text-muted-foreground basis-full text-xs">
          Làn từ khoá chạy song song với làn vector và cùng đi vào bước hợp nhất.
        </span>
      </CardContent>
    </Card>
  )
}

function Buoc({ nhan, phu, nhanManh }: { nhan: string; phu: string; nhanManh?: boolean }) {
  return (
    <div className="flex flex-col">
      <span className={nhanManh ? 'text-primary font-medium' : 'font-medium'}>{nhan}</span>
      <span className="text-muted-foreground text-xs tabular-nums">{phu}</span>
    </div>
  )
}

function TheKetQua({ kq, thuTu }: { kq: KetQuaTruyHoi; thuTu: number }) {
  const chiMotLan = (kq.vectorRank == null) !== (kq.keywordRank == null)

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex min-w-0 items-start gap-2.5">
            <span className="bg-primary/10 text-primary flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold tabular-nums">
              {thuTu}
            </span>
            <div className="flex min-w-0 flex-col">
              <Link
                to={`/tri-thuc/tai-lieu/${kq.documentId}`}
                className="hover:text-primary truncate text-[13px] font-medium transition-colors"
              >
                {kq.documentTitle}
              </Link>
              <span className="text-muted-foreground truncate text-xs">
                {kq.chunk.sectionPath ?? 'Không có đường mục'} · đoạn {kq.chunk.ordinal}
              </span>
            </div>
          </div>
          <StatusChip sacThai="info" BieuTuong={Sparkles}>
            Điểm {kq.score.toFixed(3)}
          </StatusChip>
        </div>

        <p className="text-muted-foreground text-[13px] leading-relaxed">{kq.chunk.content}</p>

        <div className="flex flex-wrap items-center gap-2 border-t pt-3">
          <HangLan nhan="Làn vector" hang={kq.vectorRank} />
          <HangLan nhan="Làn từ khoá" hang={kq.keywordRank} />
          <span className="text-muted-foreground ml-auto text-xs tabular-nums">
            {kq.chunk.tokenCount ?? '—'} token · {kq.chunk.embeddingModel ?? '—'}
          </span>
        </div>

        {chiMotLan && (
          <p className="text-muted-foreground text-xs">
            Đoạn này chỉ nổi lên ở một làn. Chạy một mình, làn còn lại đã bỏ sót nó —
            đây chính là trường hợp hợp nhất RRF sinh ra để xử lý.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Thứ hạng ở một làn. Vắng mặt hiển thị bằng chữ, **không** bằng ô trống hay số 0: "không có
 * trong 20 kết quả đầu" và "hạng 0" là hai điều khác hẳn nhau.
 */
function HangLan({ nhan, hang }: { nhan: string; hang: number | null | undefined }) {
  return (
    <span className="flex items-center gap-1.5 text-xs">
      <span className="text-muted-foreground">{nhan}</span>
      {hang == null ? (
        <StatusChip>Không lọt vào</StatusChip>
      ) : (
        <StatusChip sacThai="neutral" BieuTuong={Hash}>
          <span className="tabular-nums">{hang}</span>
        </StatusChip>
      )}
    </span>
  )
}
