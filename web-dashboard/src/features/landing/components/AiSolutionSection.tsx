import { ArrowRight, Bot, Database, FileText, Layers, Network, ShieldCheck, Sparkles, Zap } from 'lucide-react'

const ragSteps = [
  {
    step: '01',
    icon: FileText,
    title: 'Nạp & Phân Tách Dữ Liệu',
    description:
      'Doanh nghiệp tải lên tệp PDF, DOCX, TXT, Markdown hoặc HTML. Hệ thống làm sạch và chia nhỏ thành các đoạn tri thức (chunks).',
  },
  {
    step: '02',
    icon: Database,
    title: 'Vector Embeddings & pgvector',
    description:
      'Mỗi đoạn được chuyển thành vector ngữ nghĩa, lưu trong PostgreSQL pgvector — mọi truy vấn đều lọc theo đúng doanh nghiệp.',
  },
  {
    step: '03',
    icon: Network,
    title: 'Tìm Kết Hợp Ngữ Nghĩa & Từ Khoá',
    description:
      'Câu hỏi của khách được tìm đồng thời theo nghĩa (vector) và theo từ khoá, gộp hai kết quả để lấy các đoạn liên quan nhất.',
  },
  {
    step: '04',
    icon: Bot,
    title: 'Sinh Phản Hồi & Trích Dẫn Nguồn',
    description:
      'Mô hình ngôn ngữ lớn (LLM) viết câu trả lời từ các đoạn tìm được, kèm trích dẫn nguồn. Không đủ căn cứ thì từ chối và mời gặp nhân viên.',
  },
]

const aiCapabilities = [
  {
    icon: Sparkles,
    title: 'Không đủ căn cứ thì không trả lời bừa',
    description: 'AI trả lời dựa trên kho tri thức đã nạp và ghi rõ nguồn; câu hỏi ngoài tài liệu thì nói chưa có thông tin thay vì đoán.',
  },
  {
    icon: Layers,
    title: 'Hiểu ý định trước khi gọi LLM',
    description: 'Một mô hình phân loại nhỏ chạy trên CPU đoán ý định khách trước; câu chào hỏi trả lời bằng mẫu, không tốn chi phí LLM.',
  },
  {
    icon: Zap,
    title: 'Hạn mức hội thoại rõ ràng',
    description: 'Mỗi gói có hạn mức hội thoại AI; hết hạn mức thì hội thoại tự chuyển cho nhân viên, khách không bị bỏ lơ.',
  },
  {
    icon: ShieldCheck,
    title: 'Chuyển giao Nhân viên (Human Handoff)',
    description: 'Khách bấm "Gặp nhân viên" hoặc AI không chắc câu trả lời — hội thoại vào Hộp thư, tự giao cho người đang trực.',
  },
]

export function AiSolutionSection() {
  return (
    <section id="ai-rag" className="py-24 bg-muted/20 border-y border-border/60 relative overflow-hidden">
      {/* Ambient background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-primary/10 blur-[140px] rounded-full pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <Sparkles className="size-3.5" />
            <span>Công Nghệ AI Tiên Tiến</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Trợ Lý AI Ba Tầng <br className="hidden sm:inline" />
            <span className="text-primary">Luật → Mô Hình Nhỏ → LLM</span>
          </h2>
          <p className="mt-4 text-base text-muted-foreground leading-relaxed">
            Việc gì làm được bằng luật thì không gọi mô hình; việc gì mô hình nhỏ làm được thì không gọi LLM. Chỉ câu hỏi cần tra tài liệu mới tới LLM — nhanh hơn và rẻ hơn mà vẫn trả lời theo tài liệu của bạn.
          </p>
        </div>

        {/* 4-Step RAG Workflow Pipeline */}
        <div className="mb-20">
          <h3 className="text-center text-xs font-bold text-muted-foreground uppercase tracking-widest mb-8">
            Quy trình Xử lý Tri thức RAG Khép kín
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative">
            {ragSteps.map((item, idx) => {
              const Icon = item.icon
              return (
                <div
                  key={idx}
                  className="relative rounded-2xl border border-border/80 bg-card p-6 flex flex-col justify-between shadow-xs hover:shadow-lg transition-all duration-300 hover:border-primary/40 group"
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="size-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold group-hover:scale-105 transition-transform">
                        <Icon className="size-5.5" />
                      </div>
                      <span className="text-2xl font-extrabold font-mono text-muted-foreground/40 group-hover:text-primary transition-colors">
                        {item.step}
                      </span>
                    </div>
                    <h4 className="text-base font-bold text-foreground mb-2 group-hover:text-primary transition-colors">
                      {item.title}
                    </h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {item.description}
                    </p>
                  </div>

                  {idx < ragSteps.length - 1 && (
                    <div className="hidden lg:block absolute -right-3 top-1/2 -translate-y-1/2 z-10 text-muted-foreground/40">
                      <ArrowRight className="size-5" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Advanced Capabilities 2x2 Grid */}
        <div className="rounded-3xl border border-border bg-card p-8 sm:p-12 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-8 mb-8 border-b border-border/70">
            <div>
              <h3 className="text-xl sm:text-2xl font-bold text-foreground">
                Đặc Quyền Vượt Trội Của Trợ Lý AI
              </h3>
              <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                Được tinh chỉnh chuyên biệt cho nghiệp vụ Bán hàng và Chăm sóc Khách hàng đa ngành nghề.
              </p>
            </div>
            <span className="shrink-0 inline-flex items-center gap-1 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Sẵn sàng triển khai
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {aiCapabilities.map((cap, idx) => {
              const Icon = cap.icon
              return (
                <div key={idx} className="flex items-start gap-4">
                  <div className="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-1">
                    <Icon className="size-5" />
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-foreground mb-1">{cap.title}</h4>
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                      {cap.description}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
