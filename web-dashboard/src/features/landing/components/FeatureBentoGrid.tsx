import { Activity, Cpu, Globe, ShieldCheck, Sparkles, TrendingUp, Workflow, Zap } from 'lucide-react'

const features = [
  {
    icon: Sparkles,
    badge: 'Công nghệ Lõi',
    title: 'AI RAG Engine & Kho Tri Thức Thông Minh',
    description:
      'Tự động phân tích tài liệu PDF, DOCX, TXT nội bộ thành các vector embeddings trong PostgreSQL pgvector. AI trả lời chính xác dựa trên dữ liệu thật của công ty, có kèm trích dẫn nguồn rõ ràng và không bịa đặt.',
    tag: 'Độ chính xác 99.2%',
    className: 'lg:col-span-7',
    gradient: 'from-primary/10 via-primary/5 to-transparent',
  },
  {
    icon: Globe,
    badge: '1 Dòng Script',
    title: 'Livechat Widget Nhúng Mọi Website',
    description:
      'Tùy biến thương hiệu (màu sắc, logo, avatar, lời chào). Nhúng nhanh chóng vào WordPress, Next.js, Shopify, HTML chỉ với 1 đoạn mã script duy nhất.',
    tag: 'Tương thích 100%',
    className: 'lg:col-span-5',
    gradient: 'from-blue-500/10 via-indigo-500/5 to-transparent',
  },
  {
    icon: TrendingUp,
    badge: 'CRM & Bán Hàng',
    title: 'Phễu Cơ Hội Kinh Doanh Kanban Trực Quan',
    description:
      'Tự động trích xuất thông tin khách hàng từ cuộc hội thoại chat. Quản lý toàn bộ vòng đời khách hàng từ lúc mới quan tâm đến khi chốt hợp đồng thành công.',
    tag: 'Tự động bắt Lead',
    className: 'lg:col-span-5',
    gradient: 'from-emerald-500/10 via-teal-500/5 to-transparent',
  },
  {
    icon: Workflow,
    badge: 'Model Context Protocol',
    title: 'Tác Tử AI Tự Động Hóa Với Giao Thức MCP',
    description:
      'Tích hợp chuẩn giao thức MCP (Model Context Protocol). Trợ lý AI có thể tự động gọi công cụ tra cứu cơ sở dữ liệu, kiểm tra tồn kho, đặt lịch hẹn và kích hoạt luồng nghiệp vụ.',
    tag: 'Hành động tự động',
    className: 'lg:col-span-7',
    gradient: 'from-primary/10 via-blue-500/5 to-transparent',
  },
  {
    icon: Activity,
    badge: 'Giám sát chi phí',
    title: 'Phân Tích Hội Thoại & Chi Phí Token AI',
    description:
      'Bảng điều khiển trực quan theo dõi số lượng tin nhắn, tỷ lệ tự động giải quyết của Bot, mức độ hài lòng khách hàng (CSAT) và kiểm soát ngân sách token AI theo từng ngày.',
    tag: 'Kiểm soát thời gian thực',
    className: 'lg:col-span-6',
    gradient: 'from-amber-500/10 via-orange-500/5 to-transparent',
  },
  {
    icon: ShieldCheck,
    badge: 'Pháp lý & Bảo mật',
    title: 'Bảo Mật Multi-Tenant & Nghị Định 13/2023',
    description:
      'Dữ liệu mỗi doanh nghiệp được cô lập tuyệt đối nhờ PostgreSQL RLS (Row-Level Security). Đầy đủ chức năng Nhật ký kiểm toán (Audit Trail) và Quyền yêu cầu xóa dữ liệu cá nhân theo luật định.',
    tag: 'Tuân thủ NĐ 13/2023',
    className: 'lg:col-span-6',
    gradient: 'from-slate-500/10 via-primary/5 to-transparent',
  },
]

export function FeatureBentoGrid() {
  return (
    <section id="tinh-nang" className="py-24 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <Cpu className="size-3.5" />
            <span>Tính Năng Toàn Diện</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Tất cả những gì Doanh nghiệp cần để <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-primary to-indigo-600 bg-clip-text text-transparent">
              Tự Động Hóa Chăm Sóc Khách Hàng
            </span>
          </h2>
          <p className="mt-4 text-base text-muted-foreground leading-relaxed">
            Kết hợp sức mạnh giữa mô hình ngôn ngữ lớn (LLM), kho tri thức RAG và hệ thống quản trị CRM tinh gọn trong một nền tảng duy nhất.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {features.map((f, idx) => {
            const Icon = f.icon
            return (
              <div
                key={idx}
                className={`relative group rounded-2xl border border-border/80 bg-card p-7 sm:p-8 flex flex-col justify-between overflow-hidden shadow-xs hover:shadow-xl transition-all duration-300 hover:scale-[1.01] hover:border-primary/40 ${f.className}`}
              >
                {/* Background Ambient Gradient */}
                <div
                  className={`absolute inset-0 bg-gradient-to-br ${f.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none`}
                />

                <div>
                  <div className="flex items-center justify-between gap-2 mb-4">
                    <div className="size-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center group-hover:scale-110 transition-transform shadow-xs">
                      <Icon className="size-6" />
                    </div>
                    <span className="text-[11px] font-semibold text-primary px-2.5 py-1 rounded-full bg-primary/10 border border-primary/20">
                      {f.badge}
                    </span>
                  </div>

                  <h3 className="text-lg sm:text-xl font-bold text-foreground group-hover:text-primary transition-colors">
                    {f.title}
                  </h3>
                  <p className="mt-2.5 text-sm text-muted-foreground leading-relaxed">
                    {f.description}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-border/60 flex items-center justify-between text-xs font-medium text-foreground">
                  <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                    <Zap className="size-3.5" />
                    {f.tag}
                  </span>
                  <span className="text-primary font-semibold group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                    Khám phá thêm →
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
