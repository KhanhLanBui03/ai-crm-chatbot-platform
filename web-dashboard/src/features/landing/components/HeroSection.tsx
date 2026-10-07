import { ArrowRight, CheckCircle2, ChevronRight, MessageSquare, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

export function HeroSection() {
  return (
    <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden">
      {/* Background Glows & Grids */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] sm:w-[900px] h-[350px] bg-primary/10 blur-[130px] rounded-full pointer-events-none -z-10" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
          {/* Top Announcement Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-border bg-muted/50 text-foreground text-xs font-semibold backdrop-blur-md shadow-xs mb-6 hover:bg-muted transition-colors cursor-default">
            <Sparkles className="size-3.5 text-primary" />
            <span>CRM + Trợ lý AI trả lời theo tài liệu của chính doanh nghiệp</span>
            <ChevronRight className="size-3.5 text-muted-foreground" />
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground leading-[1.15]">
            Nền tảng CRM & AI Chatbot <br className="hidden sm:inline" />
            <span className="text-primary">
              Tự Động Hóa 24/7
            </span>{' '}
            cho Doanh nghiệp
          </h1>

          {/* Subtitle */}
          <p className="mt-6 text-base sm:text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-3xl">
            Trợ lý AI đọc tài liệu của doanh nghiệp (<strong>RAG</strong>) để tư vấn khách 24/7, không trả lời được thì
            chuyển ngay cho nhân viên. Nhúng khung chat bằng <strong>1 thẻ script</strong>, biến hội thoại thành lead và
            theo dõi cơ hội bán hàng trên phễu Kanban.
          </p>

          {/* Action CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row items-center gap-3.5 w-full sm:w-auto">
            <Button
              asChild
              size="lg"
              className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-7 py-6 text-base rounded-xl shadow-lg shadow-primary/25 group"
            >
              <Link to="/dang-ky" className="flex items-center justify-center gap-2">
                Dùng thử miễn phí 14 ngày
                <ArrowRight className="size-4.5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>

            <Button
              asChild
              variant="outline"
              size="lg"
              className="w-full sm:w-auto px-6 py-6 text-base rounded-xl border-border bg-background/50 hover:bg-muted font-medium backdrop-blur-sm"
            >
              <a href="#demo-livechat" className="flex items-center justify-center gap-2">
                <MessageSquare className="size-4 text-primary" />
                Trải nghiệm Chatbot trực tiếp
              </a>
            </Button>
          </div>

          {/* Trust points */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-muted-foreground font-medium">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5 text-success" />
              Không cần thẻ tín dụng
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5 text-success" />
              Nhúng bằng 1 thẻ script
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5 text-success" />
              Bảo mật đa khách thuê (RLS Safe)
            </span>
          </div>
        </div>

        {/* Ảnh CHỤP THẬT từ lần chạy hệ thống (docs/report/scr020-*) — không phải bản vẽ mô phỏng: thầy cô
            thấy đúng màn hình sẽ được demo, và không có con số nào chưa đo. */}
        <figure className="mt-14 relative mx-auto max-w-5xl rounded-2xl border border-border/80 bg-card/60 p-2 sm:p-3 shadow-2xl">
          <div className="flex items-center gap-2 px-3 py-2 border-b border-border/60 bg-muted/40 rounded-t-xl">
            <div className="size-3 rounded-full bg-red-500/80" />
            <div className="size-3 rounded-full bg-amber-500/80" />
            <div className="size-3 rounded-full bg-emerald-500/80" />
            <span className="text-xs font-mono text-muted-foreground ml-2 hidden sm:inline-block">Hộp thư</span>
          </div>
          <img
            src="/landing/hop-thu-ai-va-nhan-vien.png"
            alt="Hộp thư: trợ lý AI trả lời khách, khách xin gặp người, nhân viên tiếp nhận và trả lời ngay trong cùng hội thoại"
            width={1280}
            height={720}
            className="w-full rounded-b-xl"
          />
          <figcaption className="mt-2 text-center text-xs text-muted-foreground">
            Ảnh chụp từ hệ thống đang chạy: AI tiếp khách, khách xin gặp người, nhân viên nhận và trả lời trong cùng hội thoại.
          </figcaption>
        </figure>
      </div>
    </section>
  )
}
