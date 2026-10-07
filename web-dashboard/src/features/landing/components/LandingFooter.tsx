import { ArrowRight, Bot, ShieldCheck, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

export function LandingFooter() {
  return (
    <footer className="relative bg-muted/40 border-t border-border/80 pt-16 pb-12 overflow-hidden">
      {/* Final Call To Action Banner */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
        <div className="relative rounded-3xl p-8 sm:p-12 bg-zinc-950 text-zinc-50 border border-zinc-800/80 shadow-2xl overflow-hidden text-center flex flex-col items-center">
          {/* Subtle grid and ambient backdrop */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none" />
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 size-96 rounded-full bg-primary/20 blur-3xl pointer-events-none" />

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-zinc-800/90 text-zinc-300 text-xs font-semibold mb-4 border border-zinc-700/60 backdrop-blur-md relative z-10">
            <Sparkles className="size-3.5 text-primary" />
            <span>Bắt đầu miễn phí hôm nay</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight max-w-2xl leading-tight text-white relative z-10">
            Sẵn sàng Bứt phá Doanh số với Trợ lý AI Thông minh?
          </h2>

          <p className="mt-4 text-base sm:text-lg text-zinc-400 max-w-xl relative z-10">
            Thiết lập trong 5 phút. Tự động chăm sóc khách hàng 24/7 và gia tăng gấp đôi tỷ lệ chuyển đổi cơ hội kinh doanh.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center gap-4 relative z-10">
            <Button
              asChild
              size="lg"
              className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-8 py-6 text-base rounded-xl shadow-lg shadow-primary/25 group"
            >
              <Link to="/dang-ky" className="flex items-center gap-2">
                Tạo tài khoản Doanh nghiệp ngay
                <ArrowRight className="size-4.5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="lg"
              className="border-zinc-700 text-zinc-200 bg-zinc-900/80 hover:bg-zinc-800 hover:text-white font-medium px-6 py-6 text-base rounded-xl backdrop-blur-sm"
            >
              <Link to="/dang-nhap">Đăng nhập tài khoản</Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Main Footer Links */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-12 border-b border-border/60">
          {/* Col 1: Brand Info */}
          <div className="md:col-span-2 flex flex-col gap-3">
            <Link to="/" className="flex items-center gap-2.5">
              <div className="size-9 rounded-xl bg-gradient-to-tr from-primary to-indigo-500 flex items-center justify-center text-primary-foreground shadow-xs">
                <Bot className="size-5" />
              </div>
              <span className="font-extrabold text-base tracking-tight text-foreground">
                CRM AI Platform
              </span>
            </Link>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed max-w-sm mt-1">
              Nền tảng Tự động hóa Chăm sóc Khách hàng & Quản lý Bán hàng đa khách thuê (Multi-Tenant SaaS) ứng dụng trợ lý AI trả lời theo tài liệu (RAG).
            </p>
            <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
              <ShieldCheck className="size-4 text-emerald-600 dark:text-emerald-400" />
              <span>Bảo vệ dữ liệu theo Nghị định 13/2023/NĐ-CP</span>
            </div>
          </div>

          {/* Col 2: Navigation */}
          <div className="flex flex-col gap-2.5 text-xs sm:text-sm">
            <span className="font-bold text-foreground uppercase tracking-wider text-xs">
              Sản Phẩm & Tính Năng
            </span>
            <a href="#tinh-nang" className="text-muted-foreground hover:text-foreground transition-colors">
              Hệ thống RAG Tri thức
            </a>
            <a href="#tinh-nang" className="text-muted-foreground hover:text-foreground transition-colors">
              Livechat Widget Nhúng Web
            </a>
            <a href="#tinh-nang" className="text-muted-foreground hover:text-foreground transition-colors">
              Phễu Cơ hội Bán hàng (CRM)
            </a>
            <a href="#demo-livechat" className="text-muted-foreground hover:text-foreground transition-colors">
              Trải nghiệm Chatbot Live
            </a>
          </div>

          {/* Col 3: Portal Links */}
          <div className="flex flex-col gap-2.5 text-xs sm:text-sm">
            <span className="font-bold text-foreground uppercase tracking-wider text-xs">
              Truy Cập Nhanh
            </span>
            <Link to="/dang-nhap" className="text-muted-foreground hover:text-foreground transition-colors">
              Đăng nhập Doanh nghiệp
            </Link>
            <Link to="/dang-ky" className="text-muted-foreground hover:text-foreground transition-colors">
              Đăng ký dùng thử 14 ngày
            </Link>
            <Link to="/quen-mat-khau" className="text-muted-foreground hover:text-foreground transition-colors">
              Quên mật khẩu
            </Link>
            <a href="#bang-gia" className="text-muted-foreground hover:text-foreground transition-colors">
              Bảng giá dịch vụ
            </a>
          </div>
        </div>

        {/* Bottom copyright */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <p>© 2026 AI-CRM Chatbot Platform. Khóa Luận Tốt Nghiệp Đại Học.</p>
          <div className="flex items-center gap-6">
            <span>Bảo mật RLS</span>
            <span>Microservices Architecture</span>
            <span>PostgreSQL pgvector</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
