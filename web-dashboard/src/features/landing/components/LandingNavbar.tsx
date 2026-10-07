import { useEffect, useState } from 'react'
import { ArrowRight, Bot, Menu, Sparkles, X } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useAppSelector } from '@/app/store/hooks'
import { Button } from '@/components/ui/button'
import { cn } from '@/utils/cn'

export function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const daDangNhap = useAppSelector((s) => Boolean(s.auth.accessToken))
  const nguoiDung = useAppSelector((s) => s.auth.nguoiDung)

  const laAdmin =
    nguoiDung?.roleCode === 'PLATFORM_ADMIN' || nguoiDung?.scope === 'PLATFORM'
  const duongDanDashboard = laAdmin ? '/admin/tong-quan' : '/hop-thu'

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={cn(
        'fixed top-0 inset-x-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-background/85 backdrop-blur-md border-b border-border/60 shadow-sm py-3'
          : 'bg-transparent py-5',
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="size-10 rounded-xl bg-primary flex items-center justify-center text-primary-foreground shadow-sm group-hover:scale-105 transition-transform">
              <Bot className="size-5.5" />
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold text-base tracking-tight text-foreground flex items-center gap-1.5">
                CRM AI Platform
                <span className="text-[10px] font-semibold tracking-wide uppercase px-1.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                  RAG
                </span>
              </span>
              <span className="text-[11px] text-muted-foreground font-medium hidden sm:inline-block">
                Nền tảng Tự động hóa CRM & Chatbot AI
              </span>
            </div>
          </Link>

          {/* Navigation Links (Desktop) */}
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-muted-foreground">
            <a
              href="#tinh-nang"
              className="px-3.5 py-1.5 rounded-lg hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              Tính năng
            </a>
            <a
              href="#cach-hoat-dong"
              className="px-3.5 py-1.5 rounded-lg hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              Cách hoạt động
            </a>
            <a
              href="#ai-rag"
              className="px-3.5 py-1.5 rounded-lg hover:text-foreground hover:bg-muted/50 transition-colors flex items-center gap-1"
            >
              <Sparkles className="size-3.5 text-primary" />
              Giải pháp AI
            </a>
            <a
              href="#demo-livechat"
              className="px-3.5 py-1.5 rounded-lg hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              Trải nghiệm Chat
            </a>
            <a
              href="#bang-gia"
              className="px-3.5 py-1.5 rounded-lg hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              Bảng giá
            </a>
            <a
              href="#faq"
              className="px-3.5 py-1.5 rounded-lg hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              FAQ
            </a>
          </nav>

          {/* Action Buttons */}
          <div className="hidden sm:flex items-center gap-3">
            {daDangNhap ? (
              <Button asChild size="default" className="shadow-sm shadow-primary/20">
                <Link to={duongDanDashboard} className="flex items-center gap-1.5">
                  Vào Bảng điều khiển
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm" className="font-medium text-muted-foreground hover:text-foreground">
                  <Link to="/dang-nhap">Đăng nhập</Link>
                </Button>
                <Button
                  asChild
                  size="sm"
                  className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-md shadow-primary/25 rounded-lg px-4"
                >
                  <Link to="/dang-ky" className="flex items-center gap-1.5">
                    Dùng thử miễn phí
                    <ArrowRight className="size-3.5" />
                  </Link>
                </Button>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex sm:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted focus:outline-none"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="size-6" /> : <Menu className="size-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="sm:hidden px-4 pt-2 pb-6 bg-background/95 backdrop-blur-xl border-b border-border shadow-xl animate-in slide-in-from-top-2 duration-200">
          <div className="flex flex-col gap-2 pt-2 pb-4 border-b border-border/50 text-sm font-medium">
            <a
              href="#tinh-nang"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg hover:bg-muted text-foreground"
            >
              Tính năng nổi bật
            </a>
            <a
              href="#cach-hoat-dong"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg hover:bg-muted text-foreground"
            >
              Cách hoạt động
            </a>
            <a
              href="#ai-rag"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg hover:bg-muted text-foreground flex items-center gap-2"
            >
              <Sparkles className="size-4 text-primary" />
              Giải pháp AI RAG
            </a>
            <a
              href="#demo-livechat"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg hover:bg-muted text-foreground"
            >
              Trải nghiệm Chat trực tiếp
            </a>
            <a
              href="#bang-gia"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg hover:bg-muted text-foreground"
            >
              Bảng giá dịch vụ
            </a>
            <a
              href="#faq"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg hover:bg-muted text-foreground"
            >
              Câu hỏi thường gặp (FAQ)
            </a>
          </div>

          <div className="flex flex-col gap-2.5 pt-4">
            {daDangNhap ? (
              <Button asChild className="w-full justify-center">
                <Link to={duongDanDashboard}>Vào Bảng điều khiển</Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="outline" className="w-full justify-center">
                  <Link to="/dang-nhap">Đăng nhập</Link>
                </Button>
                <Button asChild className="w-full justify-center bg-primary">
                  <Link to="/dang-ky">Đăng ký dùng thử miễn phí</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
