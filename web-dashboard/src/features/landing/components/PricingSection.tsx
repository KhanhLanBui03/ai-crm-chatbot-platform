import { useState } from 'react'
import { ArrowRight, Check, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

const plans = [
  {
    name: 'Starter',
    badge: 'Miễn phí Trọn đời',
    priceMonth: '0 đ',
    priceYear: '0 đ',
    period: '/tháng',
    description: 'Dành cho các doanh nghiệp mới bắt đầu muốn thử nghiệm sức mạnh của AI Chatbot.',
    highlight: false,
    ctaText: 'Bắt đầu Miễn phí',
    ctaVariant: 'outline' as const,
    features: [
      '100 cuộc hội thoại AI mỗi tháng',
      '1 Trợ lý AI & 5 tài liệu RAG Knowledge',
      'Livechat Widget nhúng website tiêu chuẩn',
      '1 Tài khoản quản trị CRM',
      'Bảo mật Multi-tenant RLS',
      'Hỗ trợ qua cộng đồng & tài liệu',
    ],
  },
  {
    name: 'Professional',
    badge: 'Được Khuyên Dùng',
    priceMonth: '499.000 đ',
    priceYear: '399.000 đ',
    period: '/tháng',
    description: 'Giải pháp hoàn chỉnh cho doanh nghiệp tăng trưởng bứt phá doanh số và tự động hóa CSKH.',
    highlight: true,
    ctaText: 'Dùng thử 14 ngày Miễn phí',
    ctaVariant: 'default' as const,
    features: [
      '2.500 cuộc hội thoại AI mỗi tháng',
      'Không giới hạn tải tài liệu RAG (PDF, DOCX)',
      'Livechat Widget tùy biến màu sắc & Logo riêng',
      '5 Tài khoản nhân viên CRM & Phễu Deals Kanban',
      'Hỗ trợ Tác tử AI gọi công cụ (MCP Tool Calling)',
      'Báo cáo phân tích chi phí Token & Chỉ số CSAT',
      'Nhật ký kiểm toán Audit Log tuân thủ NĐ 13',
      'Hỗ trợ ưu tiên qua Email & Ticket 24/7',
    ],
  },
  {
    name: 'Enterprise',
    badge: 'Quy mô Lớn',
    priceMonth: '1.990.000 đ',
    priceYear: '1.590.000 đ',
    period: '/tháng',
    description: 'Dành cho tập đoàn và chuỗi kinh doanh yêu cầu hiệu năng cao, tùy chỉnh sâu và SLA cam kết.',
    highlight: false,
    ctaText: 'Liên hệ Tư vấn',
    ctaVariant: 'outline' as const,
    features: [
      'Không giới hạn cuộc hội thoại AI & Tài liệu',
      'Tùy biến LLM Fine-tuning theo ngành riêng',
      'Không giới hạn tài khoản nhân viên & Chi nhánh',
      'Toàn quyền tích hợp API & Webhook cao cấp',
      'Cam kết chất lượng dịch vụ SLA 99.9%',
      'Cơ chế sao lưu & Phục hồi dữ liệu chuyên biệt',
      'Quản lý chuyên trách (Dedicated Account Manager)',
    ],
  },
]

export function PricingSection() {
  const [isYearly, setIsYearly] = useState(false)

  return (
    <section id="bang-gia" className="py-24 bg-muted/20 border-y border-border/60 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <Sparkles className="size-3.5" />
            <span>Chi Phí Minh Bạch</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Bảng Giá Linh Hoạt <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-primary to-indigo-600 bg-clip-text text-transparent">
              Phù Hợp Mọi Quy Mô Doanh Nghiệp
            </span>
          </h2>
          <p className="mt-3 text-base text-muted-foreground">
            Bắt đầu miễn phí hôm nay. Nâng cấp hoặc hủy gói bất cứ lúc nào không ràng buộc.
          </p>

          {/* Monthly / Yearly Toggle */}
          <div className="mt-8 flex items-center gap-3 p-1.5 rounded-xl bg-card border border-border shadow-xs">
            <button
              type="button"
              onClick={() => setIsYearly(false)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                !isYearly ? 'bg-primary text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Thanh toán Hàng tháng
            </button>
            <button
              type="button"
              onClick={() => setIsYearly(true)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                isYearly ? 'bg-primary text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <span>Thanh toán Hàng năm</span>
              <span className="text-[10px] bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-bold px-1.5 py-0.2 rounded-full">
                -20%
              </span>
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto items-stretch">
          {plans.map((p, idx) => (
            <div
              key={idx}
              className={`relative rounded-2xl p-7 sm:p-8 flex flex-col justify-between transition-all duration-300 ${
                p.highlight
                  ? 'bg-card border-2 border-primary shadow-xl shadow-primary/10 scale-100 md:-translate-y-2'
                  : 'bg-card border border-border shadow-sm hover:shadow-lg'
              }`}
            >
              {p.highlight && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-xs font-bold px-3.5 py-1 rounded-full shadow-md uppercase tracking-wider">
                  Phổ Biến Nhất
                </div>
              )}

              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-foreground">{p.name}</h3>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                    {p.badge}
                  </span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground min-h-[36px]">{p.description}</p>

                {/* Price Display */}
                <div className="mt-6 flex items-baseline gap-1">
                  <span className="text-3xl sm:text-4xl font-extrabold text-foreground font-mono">
                    {isYearly ? p.priceYear : p.priceMonth}
                  </span>
                  <span className="text-xs text-muted-foreground font-medium">{p.period}</span>
                </div>

                {/* Features List */}
                <div className="mt-6 pt-6 border-t border-border/60">
                  <p className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
                    Bao gồm các tính năng:
                  </p>
                  <ul className="space-y-2.5 text-xs text-muted-foreground">
                    {p.features.map((feat, fIdx) => (
                      <li key={fIdx} className="flex items-start gap-2">
                        <Check className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                        <span className="text-foreground/90">{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Button */}
              <div className="mt-8 pt-4">
                <Button
                  asChild
                  variant={p.ctaVariant}
                  size="lg"
                  className={`w-full rounded-xl font-semibold ${
                    p.highlight ? 'bg-primary hover:bg-primary/90 text-primary-foreground shadow-md shadow-primary/20' : ''
                  }`}
                >
                  <Link to="/dang-ky" className="flex items-center justify-center gap-1.5">
                    {p.ctaText}
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
