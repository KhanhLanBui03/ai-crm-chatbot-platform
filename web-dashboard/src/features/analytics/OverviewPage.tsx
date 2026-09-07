import { format } from 'date-fns'
import { vi } from 'date-fns/locale'
import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { toast } from 'sonner'

import {
  useHoiThoaiTheoNgayQuery,
  useTongQuanQuery,
  useYeuCauXuatBaoCaoMutation,
} from '@/api/analytics'
import { KpiDashboard, type TheKpi } from '@/components/layout/KpiDashboard'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const so = (v: number) => new Intl.NumberFormat('vi-VN').format(v)
const tien = (v: number) => new Intl.NumberFormat('vi-VN').format(Math.round(v)) + ' ₫'

function giay(v: number | null | undefined): string {
  if (v == null) return '—'
  if (v < 60) return `${v} giây`
  if (v < 3600) return `${Math.round(v / 60)} phút`
  return `${(v / 3600).toFixed(1)} giờ`
}

const NGAY_THEO_KHOANG: Record<string, number> = { '7d': 7, '30d': 30, '90d': 90, 'ky-nay': 21 }

/**
 * SCR048 **và** SCR006 — cùng một bảng điều khiển, hai người đọc khác nhau.
 *
 * Hai màn dùng chung endpoint `/analytics/overview` vì chúng đọc **cùng một bộ số**; thứ khác
 * nhau là câu hỏi người xem mang tới. Người quản trị doanh nghiệp (SCR006) mở màn này để biết
 * *hôm nay có gì phải xử lý*, nên "đang chờ nhân viên" phải nằm ở ô đầu. Người phân tích
 * (SCR048) mở để đánh giá *tác tử AI làm được đến đâu*, nên tỉ lệ tự xử lý đứng đầu.
 *
 * Tách thành hai component là nhân đôi tám ô chỉ số và một biểu đồ để đổi đúng thứ tự và vài
 * dòng chữ — nên chỉ đổi khung dẫn, giữ chung phần còn lại.
 *
 * `botResolvedRate` ghi rõ **mẫu số**: "72%" không có nghĩa nếu không biết 72% của bao nhiêu.
 *
 * Biểu đồ chỉ có **một trục y**. Muốn so số hội thoại với thời gian phản hồi thì tách thành hai
 * biểu đồ — hai trục y chồng lên nhau là cách nhanh nhất để vẽ ra một tương quan không có thật.
 */
export function OverviewPage({
  nguoiDoc = 'phan-tich',
}: {
  nguoiDoc?: 'phan-tich' | 'quan-tri'
} = {}) {
  const [khoang, datKhoang] = useState('30d')
  const soNgay = NGAY_THEO_KHOANG[khoang] ?? 30
  const laQuanTri = nguoiDoc === 'quan-tri'

  const tongQuan = useTongQuanQuery({})
  const theoNgay = useHoiThoaiTheoNgayQuery({})
  const [xuatBaoCao] = useYeuCauXuatBaoCaoMutation()

  const t = tongQuan.data

  /** Gộp ba kênh của cùng một ngày lại — biểu đồ này nói về tổng, không về từng kênh. */
  const duLieuBieuDo = useMemo(() => {
    const theoNgayMap = new Map<string, { ngay: string; batDau: number; bot: number; nguoi: number }>()
    for (const d of theoNgay.data ?? []) {
      const cu = theoNgayMap.get(d.statDate) ?? { ngay: d.statDate, batDau: 0, bot: 0, nguoi: 0 }
      cu.batDau += d.conversationsStarted
      cu.bot += d.botResolved
      cu.nguoi += d.conversationsResolved - d.botResolved
      theoNgayMap.set(d.statDate, cu)
    }
    return [...theoNgayMap.values()]
      .sort((a, b) => a.ngay.localeCompare(b.ngay))
      .slice(-soNgay)
      .map((d) => ({ ...d, nhan: format(new Date(d.ngay), 'dd/MM') }))
  }, [theoNgay.data, soNgay])

  const oTuXuLy: TheKpi = {
    nhan: 'Tác tử AI tự xử lý xong',
    giaTri: t ? `${Math.round(t.botResolvedRate * 100)}%` : '—',
    phuChu: t
      ? `${so(Math.round(t.conversationsResolved * t.botResolvedRate))} / ${so(t.conversationsResolved)} hội thoại đã đóng`
      : undefined,
    thayDoi: 4.2,
  }

  /**
   * Ô riêng của người quản trị: con số **cần hành động ngay**, không phải số thống kê.
   * Nó vô nghĩa với người phân tích xu hướng nên không hiện ở SCR048.
   */
  const oChoXuLy: TheKpi = {
    nhan: 'Hội thoại đang chờ nhân viên',
    giaTri: so(t?.pendingConversations ?? 0),
    phuChu: 'Khách đang chờ ở đầu bên kia — mở hộp thư để tiếp nhận',
    tangLaTot: false,
  }

  const kpi: TheKpi[] = t
    ? [
        ...(laQuanTri ? [oChoXuLy, oTuXuLy] : [oTuXuLy]),
        {
          nhan: 'Hội thoại mới',
          giaTri: so(t.conversationsStarted),
          phuChu: laQuanTri
            ? 'Trong khoảng thời gian đã chọn'
            : `${so(t.pendingConversations ?? 0)} đang chờ nhân viên`,
          thayDoi: 8.1,
        },
        {
          nhan: 'Thời gian phản hồi đầu',
          giaTri: giay(t.avgFirstResponseSeconds),
          phuChu: 'Chỉ tính phản hồi của con người',
          thayDoi: -12.4,
          // Thời gian phản hồi giảm mới là tốt — ô này không dùng được quy ước "tăng là tốt"
          tangLaTot: false,
        },
        {
          nhan: 'Số lần chuyển cho người',
          giaTri: so(t.handoffs ?? 0),
          phuChu: `${(((t.handoffs ?? 0) / Math.max(t.conversationsStarted, 1)) * 100).toFixed(1)}% tổng hội thoại`,
          thayDoi: -3.6,
          tangLaTot: false,
        },
        {
          nhan: 'Cơ hội tiềm năng tạo mới',
          giaTri: so(t.leadsCreated ?? 0),
          phuChu: 'Gồm cả tác tử tạo tự động và nhập tay',
          thayDoi: 15.3,
        },
        {
          nhan: 'Cơ hội đã thắng',
          giaTri: so(t.dealsWon ?? 0),
          phuChu: tien(t.dealValueTotal ?? 0),
          thayDoi: 22.0,
        },
        {
          nhan: 'Tin nhắn đã xử lý',
          giaTri: so((t.messagesIn ?? 0) + (t.messagesOut ?? 0)),
          phuChu: `${so(t.messagesIn ?? 0)} vào · ${so(t.messagesOut ?? 0)} ra`,
        },
        {
          nhan: 'Chi phí AI',
          giaTri: tien(t.costVnd ?? 0),
          phuChu: 'Tính theo token thực dùng, tách khỏi phí thuê bao',
          thayDoi: 6.8,
          tangLaTot: false,
        },
      ]
    : []

  return (
    <KpiDashboard
      tieuDe={laQuanTri ? 'Bảng điều khiển quản trị' : 'Tổng quan'}
      moTa={
        laQuanTri
          ? 'Việc cần xử lý hôm nay và sức khoẻ chung của doanh nghiệp bạn trên hệ thống.'
          : 'Sức khoẻ của cả hệ thống chăm sóc khách hàng trong khoảng thời gian đã chọn.'
      }
      kpi={kpi}
      dangTai={tongQuan.isLoading}
      capNhatLuc={
        t ? format(new Date(t.updatedAt), 'HH:mm dd/MM/yyyy', { locale: vi }) : undefined
      }
      khoangThoiGian={{ giaTri: khoang, onDoi: datKhoang }}
      onXuatBaoCao={async () => {
        await xuatBaoCao({ reportType: 'OVERVIEW', format: 'XLSX' }).unwrap()
        toast.success('Đã xếp hàng xuất báo cáo. Xem tiến độ ở Phân tích → Tệp báo cáo.')
      }}
    >
      <Card>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-0.5">
            <span className="text-[15px] font-medium">Hội thoại theo ngày</span>
            <span className="text-muted-foreground text-xs">
              Tách phần tác tử tự đóng và phần phải chuyển cho người — khoảng cách giữa hai đường
              chính là khối lượng việc còn lại của nhân viên.
            </span>
          </div>

          {theoNgay.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={duLieuBieuDo} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis
                    dataKey="nhan"
                    tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                    tickLine={false}
                    axisLine={false}
                    minTickGap={24}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--popover)',
                      border: '1px solid var(--border)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line
                    type="monotone"
                    dataKey="batDau"
                    name="Hội thoại mới"
                    stroke="var(--chart-1)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="bot"
                    name="Tác tử tự đóng"
                    stroke="var(--chart-3)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="nguoi"
                    name="Người xử lý"
                    stroke="var(--chart-2)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>
    </KpiDashboard>
  )
}
