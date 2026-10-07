import { Activity, Cpu, Globe, ShieldCheck, Sparkles, TrendingUp, Workflow, Zap } from 'lucide-react'

/** Sáu tính năng ĐÃ CHẠY THẬT. Gọi công cụ MCP, phân tích chi phí token… đã cắt khỏi phạm vi nên không quảng cáo. */
const features = [
  {
    icon: Sparkles,
    badge: 'Công nghệ lõi',
    title: 'Trợ lý AI trả lời theo tài liệu của bạn (RAG)',
    description:
      'Tải lên PDF, DOCX, TXT, Markdown hoặc HTML. Hệ thống chia đoạn, vector hoá và tìm kết hợp ngữ nghĩa với từ khoá. AI trả lời kèm trích dẫn nguồn; không tìm thấy căn cứ thì nói chưa có thông tin và mời gặp nhân viên.',
    tag: 'Kèm trích dẫn nguồn',
    className: 'lg:col-span-7',
    gradient: 'from-primary/10 via-primary/5 to-transparent',
  },
  {
    icon: Globe,
    badge: '1 thẻ script',
    title: 'Khung chat nhúng website',
    description:
      'Tuỳ màu, vị trí, lời chào và tên hiển thị — đổi là áp dụng ngay, không phải dán lại mã. Chỉ chạy trên tên miền đã khai báo. Khách tự để lại tên, số điện thoại kèm đồng ý lưu dữ liệu.',
    tag: 'Chặn tên miền lạ',
    className: 'lg:col-span-5',
    gradient: 'from-blue-500/10 via-indigo-500/5 to-transparent',
  },
  {
    icon: TrendingUp,
    badge: 'CRM & bán hàng',
    title: 'Lead và phễu Deal kéo thả',
    description:
      'Tạo lead từ hội thoại chỉ một lần bấm, chuyển thành deal và kéo qua các giai đoạn. Thua bắt buộc ghi lý do, lịch sử lưu thời gian deal nằm ở từng chặng.',
    tag: 'Kanban kéo thả',
    className: 'lg:col-span-5',
    gradient: 'from-emerald-500/10 via-teal-500/5 to-transparent',
  },
  {
    icon: Workflow,
    badge: 'AI → Nhân viên',
    title: 'Hộp thư hợp nhất & chuyển giao người thật',
    description:
      'AI chuyển hội thoại cho nhân viên khi khách yêu cầu hoặc khi không chắc câu trả lời. Hệ thống tự giao cho người đang trực, cảnh báo quản trị khi khách chờ quá 5 phút.',
    tag: 'Không để khách chờ',
    className: 'lg:col-span-7',
    gradient: 'from-primary/10 via-blue-500/5 to-transparent',
  },
  {
    icon: Activity,
    badge: 'Chăm sóc khách',
    title: 'Hoạt động & nhắc việc',
    description:
      'Ghi cuộc gọi, buổi gặp, báo giá kèm kết quả; đặt giờ nhắc gọi lại. Việc quá hạn nổi bật trong "Việc của tôi" và số đỏ trên menu.',
    tag: 'Không bỏ sót khách',
    className: 'lg:col-span-6',
    gradient: 'from-amber-500/10 via-orange-500/5 to-transparent',
  },
  {
    icon: ShieldCheck,
    badge: 'Bảo mật',
    title: 'Tách dữ liệu & định hướng Nghị định 13/2023',
    description:
      'Dữ liệu mỗi doanh nghiệp tách ở tầng CSDL bằng PostgreSQL Row-Level Security. Thao tác quan trọng ghi nhật ký kiểm toán (không chép dữ liệu cá nhân vào nhật ký); ghi nhận đồng ý của khách trước khi lưu thông tin.',
    tag: 'Nhật ký kiểm toán',
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
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
