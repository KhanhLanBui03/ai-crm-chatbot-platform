import { TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { usePheuChuyenDoiQuery, useYeuCauXuatBaoCaoMutation } from '@/api/analytics'
import { KpiDashboard, type TheKpi } from '@/components/layout/KpiDashboard'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/utils/cn'

const so = (v: number) => new Intl.NumberFormat('vi-VN').format(v)
const tien = (v: number) => new Intl.NumberFormat('vi-VN').format(Math.round(v)) + ' ₫'

/**
 * SCR050 — phễu chuyển đổi. Mẫu M5.
 *
 * Mỗi bậc hiện **hai** tỉ lệ: so với bậc ngay trước (chỗ rơi rớt nằm ở đâu) và so với tổng đầu
 * vào (bậc này còn lại bao nhiêu phần của ban đầu). Chỉ một trong hai thì không trả lời được câu
 * hỏi "khâu nào đang làm mất khách".
 *
 * Cảnh báo về `scoringEnabled` không phải trang trí: những ngày chưa bật chấm điểm thì bậc "cơ
 * hội tiềm năng" được sinh bằng luật khác hẳn, và gộp chung vào một con số là so hai thứ khác
 * loại với nhau.
 */
export function FunnelPage() {
  const [khoang, datKhoang] = useState('30d')
  const [nguon, datNguon] = useState<string | undefined>()
  const truyVan = usePheuChuyenDoiQuery({ nguonLead: nguon })
  const [xuatBaoCao] = useYeuCauXuatBaoCaoMutation()

  const { bac, coNgayChuaChamDiem, tongDauVao, tongGiaTri } = useMemo(() => {
    const ds = truyVan.data ?? []
    const cong = ds.reduce(
      (t, b) => ({
        hoiThoai: t.hoiThoai + b.conversationsTotal,
        coTinHieu: t.coTinHieu + b.conversationsWithSignal,
        lead: t.lead + b.leadsCreated,
        deal: t.deal + b.dealsCreated,
        thang: t.thang + b.dealsWon,
        giaTri: t.giaTri + (b.dealValueTotal ?? 0),
      }),
      { hoiThoai: 0, coTinHieu: 0, lead: 0, deal: 0, thang: 0, giaTri: 0 },
    )
    return {
      tongDauVao: cong.hoiThoai,
      tongGiaTri: cong.giaTri,
      coNgayChuaChamDiem: ds.some((b) => !b.scoringEnabled),
      bac: [
        { nhan: 'Hội thoại', giaTri: cong.hoiThoai, moTa: 'Mọi hội thoại trong khoảng thời gian' },
        { nhan: 'Có tín hiệu mua', giaTri: cong.coTinHieu, moTa: 'Tác tử nhận ra ý định mua' },
        { nhan: 'Cơ hội tiềm năng', giaTri: cong.lead, moTa: 'Đủ điểm để tạo lead' },
        { nhan: 'Cơ hội bán hàng', giaTri: cong.deal, moTa: 'Đã chuyển thành deal' },
        { nhan: 'Đã thắng', giaTri: cong.thang, moTa: tien(cong.giaTri) },
      ],
    }
  }, [truyVan.data])

  const kpi: TheKpi[] = [
    {
      nhan: 'Tỉ lệ hội thoại → cơ hội',
      giaTri: tongDauVao > 0 ? `${((bac[2].giaTri / tongDauVao) * 100).toFixed(1)}%` : '—',
      phuChu: `${so(bac[2].giaTri)} / ${so(tongDauVao)} hội thoại`,
    },
    {
      nhan: 'Tỉ lệ cơ hội → thắng',
      giaTri: bac[2].giaTri > 0 ? `${((bac[4].giaTri / bac[2].giaTri) * 100).toFixed(1)}%` : '—',
      phuChu: `${so(bac[4].giaTri)} / ${so(bac[2].giaTri)} cơ hội`,
    },
    {
      nhan: 'Cơ hội đã thắng',
      giaTri: so(bac[4].giaTri),
      phuChu: bac[4].moTa,
    },
    {
      nhan: 'Giá trị trung bình mỗi đơn',
      giaTri: bac[4].giaTri > 0 ? tien(tongGiaTri / bac[4].giaTri) : '—',
      phuChu: 'Tổng giá trị chia số đơn thắng',
    },
  ]

  return (
    <KpiDashboard
      tieuDe="Phễu chuyển đổi"
      moTa="Từ hội thoại tới đơn thắng — mỗi bậc cho biết mất khách ở khâu nào."
      kpi={kpi}
      dangTai={truyVan.isLoading}
      khoangThoiGian={{ giaTri: khoang, onDoi: datKhoang }}
      onXuatBaoCao={async () => {
        await xuatBaoCao({ reportType: 'FUNNEL', format: 'CSV' }).unwrap()
        toast.success('Đã xếp hàng xuất báo cáo.')
      }}
    >
      <div className="flex flex-wrap gap-1.5">
        {[
          { giaTri: undefined, nhan: 'Mọi nguồn' },
          { giaTri: 'AI_AUTO', nhan: 'Tác tử AI tạo' },
          { giaTri: 'MANUAL', nhan: 'Nhập tay' },
        ].map((n) => (
          <button
            key={n.nhan}
            type="button"
            onClick={() => datNguon(n.giaTri)}
            className={cn(
              'h-8 rounded-lg border px-3 text-[13px] transition-colors',
              nguon === n.giaTri ? 'ring-primary bg-primary/5 ring-1' : 'hover:bg-muted/60',
            )}
          >
            {n.nhan}
          </button>
        ))}
      </div>

      {coNgayChuaChamDiem && (
        <Alert>
          <TriangleAlert />
          <AlertDescription>
            Khoảng thời gian này có những ngày <strong>chưa bật chấm điểm tiềm năng</strong>. Bậc
            &quot;cơ hội tiềm năng&quot; của các ngày đó sinh bằng luật khác, nên đừng so trực tiếp
            với các ngày sau.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="flex flex-col gap-2">
          {truyVan.isLoading ? (
            <>
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </>
          ) : (
            bac.map((b, i) => (
              <BacPheuDong
                key={b.nhan}
                nhan={b.nhan}
                moTa={b.moTa}
                giaTri={b.giaTri}
                soVoiTruoc={i === 0 ? null : bac[i - 1].giaTri}
                soVoiDau={bac[0].giaTri}
              />
            ))
          )}
        </CardContent>
      </Card>
    </KpiDashboard>
  )
}

function BacPheuDong({
  nhan,
  moTa,
  giaTri,
  soVoiTruoc,
  soVoiDau,
}: {
  nhan: string
  moTa: string
  giaTri: number
  soVoiTruoc: number | null
  soVoiDau: number
}) {
  const rong = soVoiDau > 0 ? Math.max((giaTri / soVoiDau) * 100, 3) : 0
  const tyLeTruoc = soVoiTruoc && soVoiTruoc > 0 ? (giaTri / soVoiTruoc) * 100 : null
  // Rơi quá nửa ở một bậc là chỗ đáng xem trước tiên
  const rotManh = tyLeTruoc != null && tyLeTruoc < 50

  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="text-[13px] font-medium">{nhan}</span>
        <span className="text-lg font-semibold tabular-nums">{so(giaTri)}</span>
        {tyLeTruoc != null && (
          <span
            className={cn(
              'text-xs tabular-nums',
              rotManh ? 'text-destructive font-medium' : 'text-muted-foreground',
            )}
          >
            {tyLeTruoc.toFixed(1)}% của bậc trước
          </span>
        )}
        <span className="text-muted-foreground text-xs tabular-nums">
          · {soVoiDau > 0 ? ((giaTri / soVoiDau) * 100).toFixed(1) : '0'}% của đầu vào
        </span>
        <span className="text-muted-foreground flex-1 text-right text-xs">{moTa}</span>
      </div>
      <div className="bg-muted h-7 w-full overflow-hidden rounded-md">
        <div
          className={cn('h-full rounded-md', rotManh ? 'bg-destructive/70' : 'bg-chart-1')}
          style={{ width: `${rong}%` }}
        />
      </div>
    </div>
  )
}
