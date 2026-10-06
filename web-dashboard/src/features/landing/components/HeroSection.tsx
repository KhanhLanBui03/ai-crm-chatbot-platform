import { ArrowRight, Bot, CheckCircle2, ChevronRight, MessageSquare, Sparkles, TrendingUp, Users, Zap } from 'lucide-react'
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
            <span>Ra mắt Hệ sinh thái AI Multi-Agent & RAG Hub cho Doanh nghiệp</span>
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
            Tích hợp trợ lý AI học sâu tài liệu nội bộ qua <strong>RAG</strong>, tự động tư vấn khách hàng trong <strong>0.4s</strong>, nhúng Livechat chỉ với 1 dòng script và quản lý cơ hội kinh doanh (Deals) trên phễu Kanban thời gian thực.
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
              Triển khai trong 5 phút
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5 text-success" />
              Bảo mật đa khách thuê (RLS Safe)
            </span>
          </div>
        </div>

        {/* Hero Interactive UI Preview Mockup */}
        <div className="mt-14 relative mx-auto max-w-5xl rounded-2xl border border-border/80 bg-card/60 p-2 sm:p-3 shadow-2xl backdrop-blur-xl">
          {/* Glass header bar */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-border/60 bg-muted/40 rounded-xl mb-3">
            <div className="flex items-center gap-2">
              <div className="size-3 rounded-full bg-red-500/80" />
              <div className="size-3 rounded-full bg-amber-500/80" />
              <div className="size-3 rounded-full bg-emerald-500/80" />
              <span className="text-xs font-mono text-muted-foreground ml-2 hidden sm:inline-block">
                crm-platform.app / dashboard / live-ai
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                <span className="size-1.5 rounded-full bg-emerald-500 animate-ping" />
                AI Agent Active
              </span>
            </div>
          </div>

          {/* Split Mockup Content: Left Kanban Deals + Right Live AI Chat */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 p-1 sm:p-2">
            {/* Left CRM Mini Board (7 cols) */}
            <div className="lg:col-span-7 bg-background/90 border border-border rounded-xl p-4 flex flex-col gap-3 shadow-sm">
              <div className="flex items-center justify-between pb-2 border-b border-border/60">
                <div className="flex items-center gap-2">
                  <TrendingUp className="size-4 text-primary" />
                  <span className="text-sm font-bold text-foreground">Phễu Bán Hàng & Cơ Hội (Kanban)</span>
                </div>
                <span className="text-xs font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded-md">
                  Tổng 1.250.000.000 đ
                </span>
              </div>

              {/* Kanban columns preview */}
              <div className="grid grid-cols-3 gap-2 text-xs">
                {/* Col 1 */}
                <div className="bg-muted/40 rounded-lg p-2.5 flex flex-col gap-2">
                  <div className="flex items-center justify-between font-semibold text-[11px] text-muted-foreground">
                    <span>Mới tiếp cận</span>
                    <span className="bg-muted px-1.5 py-0.2 rounded font-mono">3</span>
                  </div>
                  <div className="bg-card p-2 rounded-md border border-border/70 shadow-xs">
                    <p className="font-semibold text-foreground text-xs truncate">Công ty Tech Corp</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">25.000.000 đ</p>
                    <div className="flex items-center gap-1 mt-1 text-[10px] text-primary">
                      <Bot className="size-3" />
                      <span>AI vừa phân loại Lead</span>
                    </div>
                  </div>
                </div>

                {/* Col 2 */}
                <div className="bg-muted/40 rounded-lg p-2.5 flex flex-col gap-2">
                  <div className="flex items-center justify-between font-semibold text-[11px] text-muted-foreground">
                    <span>Đang tư vấn</span>
                    <span className="bg-muted px-1.5 py-0.2 rounded font-mono">2</span>
                  </div>
                  <div className="bg-card p-2 rounded-md border border-primary/30 shadow-xs bg-primary/5">
                    <p className="font-semibold text-foreground text-xs truncate">Bất động sản An Gia</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">180.000.000 đ</p>
                    <div className="flex items-center gap-1 mt-1 text-[10px] text-emerald-600 dark:text-emerald-400">
                      <Zap className="size-3" />
                      <span>Sẵn sàng chốt hợp đồng</span>
                    </div>
                  </div>
                </div>

                {/* Col 3 */}
                <div className="bg-muted/40 rounded-lg p-2.5 flex flex-col gap-2">
                  <div className="flex items-center justify-between font-semibold text-[11px] text-muted-foreground">
                    <span>Thành công</span>
                    <span className="bg-emerald-500/10 text-emerald-600 px-1.5 py-0.2 rounded font-mono font-bold">
                      12
                    </span>
                  </div>
                  <div className="bg-card p-2 rounded-md border border-emerald-500/30 shadow-xs">
                    <p className="font-semibold text-foreground text-xs truncate">Tập đoàn Alpha</p>
                    <p className="text-[11px] text-success font-semibold mt-0.5">450.000.000 đ</p>
                    <p className="text-[10px] text-muted-foreground mt-1">Hoàn tất thanh toán</p>
                  </div>
                </div>
              </div>

              {/* Quick stats footer inside left mockup */}
              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-border/50 text-[11px]">
                <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
                  <Users className="size-4 text-primary" />
                  <div>
                    <p className="font-bold text-foreground">1.420 Khách hàng</p>
                    <p className="text-muted-foreground text-[10px]">+18% tháng này</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
                  <Zap className="size-4 text-amber-500" />
                  <div>
                    <p className="font-bold text-foreground">94.8% CSAT Score</p>
                    <p className="text-muted-foreground text-[10px]">Đánh giá 5 sao</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Live AI Chat Widget Mockup (5 cols) */}
            <div className="lg:col-span-5 bg-card border border-border rounded-xl p-3.5 flex flex-col justify-between shadow-sm">
              <div className="flex items-center justify-between pb-2.5 border-b border-border">
                <div className="flex items-center gap-2">
                  <div className="size-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
                    <Bot className="size-4.5" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-foreground">Trợ lý AI Doanh nghiệp</p>
                    <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">● Sẵn sàng tư vấn (RAG 99.2%)</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">
                  0.38s
                </span>
              </div>

              {/* Chat conversation stream */}
              <div className="flex flex-col gap-2.5 py-3 text-xs">
                {/* User msg */}
                <div className="self-end bg-primary text-primary-foreground p-2.5 rounded-2xl rounded-tr-xs max-w-[85%]">
                  Chào bot, công ty có hỗ trợ tích hợp livechat vào web WordPress và Next.js không?
                </div>

                {/* AI msg with RAG citations */}
                <div className="self-start bg-muted/60 text-foreground p-2.5 rounded-2xl rounded-tl-xs max-w-[95%] border border-border/60">
                  <p className="leading-relaxed">
                    Dạ hoàn toàn có ạ! Bạn chỉ cần sao chép <strong>1 dòng mã script</strong> từ mục Cài đặt Widget để nhúng vào WordPress, Next.js hay bất kỳ nền tảng web nào.
                  </p>
                  <div className="mt-2 pt-2 border-t border-border/50 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <Sparkles className="size-3 text-primary" />
                    <span>Nguồn trích dẫn: <strong>Tài liệu Hướng dẫn Tích hợp Widget.pdf (Trang 3)</strong></span>
                  </div>
                </div>
              </div>

              {/* Simulated input bar */}
              <div className="flex items-center gap-1.5 p-1.5 bg-muted/40 border border-border rounded-lg text-xs text-muted-foreground">
                <span className="flex-1 px-2 text-muted-foreground/70">Nhập tin nhắn để hỏi AI...</span>
                <div className="size-6 rounded-md bg-primary text-primary-foreground flex items-center justify-center">
                  <ArrowRight className="size-3" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
