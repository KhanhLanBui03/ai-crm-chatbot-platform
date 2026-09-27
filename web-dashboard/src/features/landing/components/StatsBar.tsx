import { Clock, Code2, ShieldCheck, TrendingUp } from 'lucide-react'

const stats = [
  {
    icon: Clock,
    value: '0.4s',
    label: 'Tốc độ phản hồi AI',
    description: 'Tư vấn tức thì 24/7 không độ trễ',
  },
  {
    icon: TrendingUp,
    value: '10x',
    label: 'Tăng trưởng Lead',
    description: 'Tự động thu thập & phân loại cơ hội',
  },
  {
    icon: Code2,
    value: '1 Dòng mã',
    label: 'Nhúng Widget Dễ Dàng',
    description: 'Tương thích mọi nền tảng Web & CMS',
  },
  {
    icon: ShieldCheck,
    value: '100%',
    label: 'Bảo mật Multi-Tenant',
    description: 'PostgreSQL RLS & NĐ 13/2023/NĐ-CP',
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
                <div className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground font-mono">
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
