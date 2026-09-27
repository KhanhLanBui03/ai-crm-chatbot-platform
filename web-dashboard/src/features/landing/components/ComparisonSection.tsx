import { Check, X, Zap } from 'lucide-react'

const comparisons = [
  {
    criteria: 'Thời gian phản hồi khách hàng',
    traditional: '15 - 30 phút (hoặc hôm sau nếu ngoài giờ)',
    aiPlatform: '0.4 giây — Tức thì 24/7/365',
    highlight: true,
  },
  {
    criteria: 'Khả năng phục vụ đồng thời',
    traditional: 'Chỉ 2 - 3 khách / nhân viên tại một thời điểm',
    aiPlatform: 'Không giới hạn hàng ngàn khách cùng lúc',
    highlight: true,
  },
  {
    criteria: 'Độ chuẩn xác thông tin sản phẩm',
    traditional: 'Dễ nhầm lẫn, phụ thuộc trí nhớ nhân sự mới',
    aiPlatform: 'Chuẩn xác 99.2% theo tài liệu RAG chính thức',
    highlight: false,
  },
  {
    criteria: 'Thu thập & Phân loại Khách hàng tiềm năng',
    traditional: 'Nhập tay vào Excel, dễ bỏ sót khách nóng',
    aiPlatform: 'Tự động trích xuất thông tin & đưa vào phễu CRM',
    highlight: true,
  },
  {
    criteria: 'Chi phí vận hành ca đêm & ngày lễ',
    traditional: 'Tốn kém chi phí nhân sự trực ca 24/7',
    aiPlatform: 'Tiết kiệm tới 80% ngân sách vận hành CSKH',
    highlight: true,
  },
]

export function ComparisonSection() {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <Zap className="size-3.5" />
            <span>So Sánh Hiệu Quả</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Tại sao Doanh nghiệp chọn <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-primary to-indigo-600 bg-clip-text text-transparent">
              CRM AI Platform?
            </span>
          </h2>
          <p className="mt-4 text-base text-muted-foreground">
            Bứt phá hiệu suất tư vấn và doanh thu so với mô hình chăm sóc khách hàng thủ công truyền thống.
          </p>
        </div>

        {/* Comparison Table */}
        <div className="max-w-4xl mx-auto rounded-2xl border border-border bg-card shadow-lg overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-12 bg-muted/50 p-4 font-bold text-sm border-b border-border text-foreground">
            <div className="md:col-span-4 text-muted-foreground">Tiêu chí so sánh</div>
            <div className="md:col-span-4 text-muted-foreground hidden md:block">CSKH Thủ Công Truyền Thống</div>
            <div className="md:col-span-4 text-primary flex items-center gap-1.5 hidden md:flex">
              <Zap className="size-4" />
              CRM AI Platform (Tự động 24/7)
            </div>
          </div>

          <div className="divide-y divide-border">
            {comparisons.map((item, idx) => (
              <div
                key={idx}
                className="grid grid-cols-1 md:grid-cols-12 p-4 sm:p-5 gap-3 items-center hover:bg-muted/20 transition-colors"
              >
                {/* Criteria */}
                <div className="md:col-span-4 font-semibold text-sm text-foreground">
                  {item.criteria}
                </div>

                {/* Traditional */}
                <div className="md:col-span-4 flex items-start gap-2 text-xs sm:text-sm text-muted-foreground">
                  <X className="size-4 text-destructive shrink-0 mt-0.5" />
                  <span>{item.traditional}</span>
                </div>

                {/* AI Platform */}
                <div className="md:col-span-4 flex items-start gap-2 text-xs sm:text-sm font-semibold text-foreground bg-primary/5 p-2 rounded-lg border border-primary/20">
                  <Check className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  <span className="text-primary">{item.aiPlatform}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
