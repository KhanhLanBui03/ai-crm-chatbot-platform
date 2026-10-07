import { Clock, Code2, ShieldCheck, TrendingUp } from 'lucide-react'

/**
 * Bốn điểm nổi bật đều KIỂM CHỨNG ĐƯỢC trên hệ thống đang chạy — không dùng số đo chưa đo (trước đây là
 * "0.4s", "10x", "100%"; mục tiêu thật của dự án là p95 < 4 giây).
 */
const stats = [
  {
    icon: Code2,
    value: '1 thẻ script',
    label: 'Nhúng khung chat',
    description: 'Chỉ chạy trên tên miền doanh nghiệp đã khai báo',
  },
  {
    icon: Clock,
    value: 'AI → Người',
    label: 'Chuyển giao khi cần',
    description: 'Không đủ căn cứ thì không trả lời bừa',
  },
  {
    icon: TrendingUp,
    value: 'Lead → Deal',
    label: 'Từ hội thoại tới doanh thu',
    description: 'Phễu Kanban kéo thả, nhắc việc chăm sóc',
  },
  {
    icon: ShieldCheck,
    value: 'RLS',
    label: 'Tách dữ liệu từng doanh nghiệp',
    description: 'Ngay ở tầng CSDL PostgreSQL',
  },
]

export function StatsBar() {
  return (
    <section className="py-12 border-y border-border/60 bg-muted/20 backdrop-blur-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8">
          {stats.map((item, idx) => {
            const Icon = item.icon
            return (
              <div
                key={idx}
                className="flex flex-col items-center text-center p-4 rounded-xl transition-all duration-300 hover:bg-card hover:shadow-md hover:scale-[1.02] border border-transparent hover:border-border/60"
              >
                <div className="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3">
                  <Icon className="size-5" />
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
                  {item.value}
                </div>
                <div className="text-sm font-semibold text-foreground mt-1">{item.label}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{item.description}</div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
