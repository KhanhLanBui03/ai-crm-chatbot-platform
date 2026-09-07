import { format, subDays } from 'date-fns'
import { useMemo, useState } from 'react'

import { useHieuQuaAiQuery } from '@/api/ai-agent'
import { KpiDashboard, type TheKpi } from '@/components/layout/KpiDashboard'
import { Card, CardContent } from '@/components/ui/card'
import { StatusChip } from '@/components/ui/status-chip'
import {
  NHAN_LY_DO_CHUYEN_GIAO,
  NHAN_NHANH_XU_LY,
  doTre,
  phanTram,
  tienVnd,
} from '@/features/ai-agent/nhan'
import type { HieuQuaAi } from '@/types/schema'

const CHANG = [
  { khoa: 'retrieve', nhan: 'Truy hồi', mau: 'var(--chart-1)' },
  { khoa: 'rerank', nhan: 'Xếp hạng lại', mau: 'var(--chart-2)' },
  { khoa: 'generate', nhan: 'Sinh câu trả lời', mau: 'var(--chart-3)' },
  { khoa: 'tool', nhan: 'Gọi công cụ', mau: 'var(--chart-4)' },
] as const

const so = (v: number) => new Intl.NumberFormat('vi-VN').format(v)

function moc(khoang: string): { tuNgay?: string; denNgay?: string } {
  const hom = new Date()
  const soNgay = khoang === '7d' ? 7 : khoang === '90d' ? 90 : 30
  if (khoang === 'ky-nay') return {}
  return {
    tuNgay: format(subDays(hom, soNgay), 'yyyy-MM-dd'),
    denNgay: format(hom, 'yyyy-MM-dd'),
  }
}

/**
 * SCR051 — hiệu quả và chi phí của tác tử AI. Màn chữ ký, mượn khung M5.
 *
 * Khung chỉ số dùng lại mẫu M5 để giống SCR048; phần thân thì không mẫu nào phủ được, vì nó tồn
 * tại để nói một điều mà bảng số thường che mất: **không phải mọi lần chuyển giao đều là tác tử
 * làm dở**. Khách chủ động xin gặp người, hay công cụ ghi cần người duyệt, là hệ thống chạy đúng
 * thiết kế. Gộp tất cả vào một tỉ lệ "chuyển giao" rồi đọc lên trước hội đồng là tự hạ điểm mình
 * bằng một con số sai nghĩa.
 *
 * `positiveFeedbackRate` kèm `feedbackCount` chứ không đứng một mình: 100% trên 3 lượt đánh giá và
 * 86% trên 1.204 lượt là hai khẳng định khác hẳn nhau về độ tin cậy.
 */
export function AiPerformancePage() {
  const [khoang, datKhoang] = useState('30d')
  const truyVan = useHieuQuaAiQuery(moc(khoang))
  const d = truyVan.data

  const kpi = useMemo<TheKpi[]>(() => {
    if (!d) return []
    return [
      {
        nhan: 'Lượt xử lý',
        giaTri: so(d.totalInteractions ?? 0),
        phuChu: `${phanTram(d.cachedRate)} dùng đệm ngữ nghĩa, không tốn lượt gọi mô hình`,
      },
      {
        nhan: 'Phản hồi tích cực',
        giaTri: phanTram(d.positiveFeedbackRate),
        phuChu: `trên ${so(d.feedbackCount ?? 0)} lượt đánh giá của nhân viên và khách`,
      },
      {
        nhan: 'Tỉ lệ từ chối',
        giaTri: phanTram(d.refusalRate),
        phuChu: 'Từ chối đúng lúc tốt hơn trả lời bịa — đọc kèm khoảng trống tri thức',
        tangLaTot: false,
      },
      {
        nhan: 'Chi phí mô hình',
        giaTri: tienVnd(d.costVnd),
        phuChu: `${doTre(d.avgLatencyMs)} trung bình mỗi lượt`,
        tangLaTot: false,
      },
    ]
  }, [d])

  return (
    <KpiDashboard
      tieuDe="Hiệu quả và chi phí của tác tử AI"
      moTa="Số liệu tổng hợp trên hội thoại thật, không phải trên bộ kiểm thử."
      capNhatLuc={d ? format(new Date(d.updatedAt), 'HH:mm dd/MM/yyyy') : undefined}
      kpi={kpi}
      khoangThoiGian={{ giaTri: khoang, onDoi: datKhoang }}
      dangTai={truyVan.isLoading}
    >
      {d && (
        <div className="grid gap-3 lg:grid-cols-2">
          <PhanBoNhanh d={d} />
          <LyDoChuyenGiao d={d} />
          <DoTreTheoChang d={d} />
          <ChatLuongCanCu d={d} />
        </div>
      )}
    </KpiDashboard>
  )
}

/** Phân bố nhánh xử lý — thanh ngang có nhãn trực tiếp, không cần chú giải màu. */
function PhanBoNhanh({ d }: { d: HieuQuaAi }) {
  const tong = d.routeDistribution.reduce((t, r) => t + r.count, 0) || 1
  const ds = [...d.routeDistribution].sort((a, b) => b.count - a.count)

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 className="text-[15px] font-medium">Tác tử làm gì với tin của khách</h2>
          <p className="text-muted-foreground text-xs">
            Mỗi nhánh có chi phí khác hẳn nhau — nhánh chào hỏi gần như không tốn gì.
          </p>
        </div>
        <div className="flex flex-col gap-2.5">
          {ds.map((r) => (
            <div key={r.route} className="flex flex-col gap-1">
              <div className="flex items-baseline justify-between text-xs">
                <span className="font-medium">{NHAN_NHANH_XU_LY[r.route].nhan}</span>
                <span className="text-muted-foreground tabular-nums">
                  {so(r.count)} lượt · {tienVnd(r.costVnd ?? 0)}
                </span>
              </div>
              <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
                <span
                  className="bg-primary block h-full rounded-full"
                  style={{ width: `${(r.count / tong) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Lý do chuyển giao, tách làm hai nhóm theo `countsAgainstAiQuality`.
 *
 * Tách ở đây chứ không để người đọc tự phân loại: cột đó có trong giao ước chính vì phép cộng
 * gộp là phép cộng sai.
 */
function LyDoChuyenGiao({ d }: { d: HieuQuaAi }) {
  const truVao = d.handoffReasons.filter((h) => h.countsAgainstAiQuality)
  const khongTru = d.handoffReasons.filter((h) => !h.countsAgainstAiQuality)
  const tong = d.handoffReasons.reduce((t, h) => t + h.count, 0)
  const soTruVao = truVao.reduce((t, h) => t + h.count, 0)

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 className="text-[15px] font-medium">Vì sao chuyển cho nhân viên</h2>
          <p className="text-muted-foreground text-xs">
            {so(tong)} lần chuyển giao, trong đó{' '}
            <strong className="text-foreground">{so(soTruVao)}</strong> lần là do tác tử không xử lý
            được — phần còn lại là hệ thống chạy đúng thiết kế.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-muted-foreground text-xs">Tính vào chất lượng tác tử</span>
          {truVao.map((h) => (
            <div key={h.reason} className="flex items-baseline justify-between text-xs">
              <span>{NHAN_LY_DO_CHUYEN_GIAO[h.reason]}</span>
              <span className="text-destructive font-medium tabular-nums">{so(h.count)}</span>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-2 border-t pt-2.5">
          <span className="text-muted-foreground text-xs">Không phải lỗi của tác tử</span>
          {khongTru.map((h) => (
            <div key={h.reason} className="flex items-baseline justify-between text-xs">
              <span>{NHAN_LY_DO_CHUYEN_GIAO[h.reason]}</span>
              <span className="text-muted-foreground font-medium tabular-nums">{so(h.count)}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function DoTreTheoChang({ d }: { d: HieuQuaAi }) {
  const tong = CHANG.reduce((t, c) => t + (d.latencyBreakdown[c.khoa] ?? 0), 0) || 1

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 className="text-[15px] font-medium">Thời gian đi đâu mất</h2>
          <p className="text-muted-foreground text-xs">
            Trung bình từng chặng. Chặng nào phình lên thì tối ưu ở đó, không phải đổi mô hình.
          </p>
        </div>
        <div className="bg-muted flex h-2 w-full overflow-hidden rounded-full">
          {CHANG.map((c) => {
            const v = d.latencyBreakdown[c.khoa] ?? 0
            if (v === 0) return null
            return (
              <span
                key={c.khoa}
                className="h-full"
                style={{ width: `${(v / tong) * 100}%`, backgroundColor: c.mau }}
              />
            )
          })}
        </div>
        <div className="flex flex-col gap-1.5">
          {CHANG.map((c) => {
            const v = d.latencyBreakdown[c.khoa] ?? 0
            return (
              <div key={c.khoa} className="flex items-center gap-2 text-xs">
                <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: c.mau }} />
                <span className="flex-1">{c.nhan}</span>
                <span className="font-medium tabular-nums">{doTre(v)}</span>
                <span className="text-muted-foreground w-12 text-right tabular-nums">
                  {((v / tong) * 100).toFixed(0)}%
                </span>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

function ChatLuongCanCu({ d }: { d: HieuQuaAi }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 className="text-[15px] font-medium">Chất lượng căn cứ và phiên bản mô hình</h2>
          <p className="text-muted-foreground text-xs">
            Độ bám nguồn trung bình quyết định bao nhiêu câu trả lời bị huỷ trước khi tới khách.
          </p>
        </div>

        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold tabular-nums">
            {d.avgGroundedness?.toFixed(2) ?? '—'}
          </span>
          <span className="text-muted-foreground text-xs">độ bám nguồn trung bình</span>
        </div>
        <div className="bg-muted relative h-1.5 w-full overflow-hidden rounded-full">
          <span
            className="bg-success block h-full rounded-full"
            style={{ width: `${(d.avgGroundedness ?? 0) * 100}%` }}
          />
          {/* Vạch ngưỡng 0,7: dưới mức này câu trả lời bị huỷ, không gửi cho khách */}
          <span className="bg-foreground/60 absolute top-0 h-full w-px" style={{ left: '70%' }} />
        </div>
        <span className="text-muted-foreground text-xs">
          Vạch dọc là ngưỡng 0,70 — dưới ngưỡng thì câu trả lời bị huỷ chứ không gửi đi.
        </span>

        <div className="flex flex-wrap items-center gap-2 border-t pt-2.5">
          <span className="text-muted-foreground text-xs">Phiên bản mô hình trong kỳ</span>
          {(d.modelVersions ?? []).map((v) => (
            <StatusChip key={v}>{v}</StatusChip>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
