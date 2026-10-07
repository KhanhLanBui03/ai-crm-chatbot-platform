import { useEffect } from 'react'

import { AiSolutionSection } from './components/AiSolutionSection'
import { ComparisonSection } from './components/ComparisonSection'
import { FaqSection } from './components/FaqSection'
import { FeatureBentoGrid } from './components/FeatureBentoGrid'
import { HowItWorksSection } from './components/HowItWorksSection'
import { HeroSection } from './components/HeroSection'
import { LandingFooter } from './components/LandingFooter'
import { LandingNavbar } from './components/LandingNavbar'
import { LiveChatDemoSection } from './components/LiveChatDemoSection'
import { PricingSection } from './components/PricingSection'
import { StatsBar } from './components/StatsBar'

export function LandingPage() {
  // Intersection Observer for delicate scroll animations
  // Nội dung HIỆN SẴN; chỉ khi có JavaScript và người xem không bật "giảm chuyển động" mới ẩn những phần
  // còn ở dưới màn hình để hiện dần khi cuộn tới. Trước đây mọi phần đều ẩn sẵn (opacity-0) — máy tìm
  // kiếm, bản in và ảnh chụp cả trang chỉ thấy một khoảng trắng.
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('opacity-100', 'translate-y-0')
            entry.target.classList.remove('opacity-0', 'translate-y-6')
          }
        })
      },
      {
        threshold: 0.1,
        rootMargin: '0px 0px -40px 0px',
      },
    )

    const sections = document.querySelectorAll('.animate-on-scroll')
    sections.forEach((s) => {
      if (s.getBoundingClientRect().top > window.innerHeight) {
        s.classList.add('opacity-0', 'translate-y-6')
        observer.observe(s)
      }
    })

    // In trang (Ctrl+P) thì hiện hết — bản in không cuộn nên không có gì kích hoạt hiệu ứng
    const hienHet = () =>
      document.querySelectorAll('.animate-on-scroll').forEach((s) => s.classList.remove('opacity-0', 'translate-y-6'))
    window.addEventListener('beforeprint', hienHet)

    return () => {
      observer.disconnect()
      window.removeEventListener('beforeprint', hienHet)
    }
  }, [])

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 selection:text-primary overflow-x-hidden font-sans">
      {/* 1. Header & Navigation */}
      <LandingNavbar />

      {/* 2. Main Content */}
      <main className="flex flex-col">
        {/* Hero Section */}
        <div className="animate-on-scroll transition-all duration-700">
          <HeroSection />
        </div>

        {/* Stats Counter Bar */}
        <div className="animate-on-scroll transition-all duration-700">
          <StatsBar />
        </div>

        {/* Bento Grid Core Features */}
        <div className="animate-on-scroll transition-all duration-700">
          <FeatureBentoGrid />
        </div>

        {/* Luồng thật: tin nhắn → AI/người → lead → deal → nhắc việc, ảnh chụp thật */}
        <div className="animate-on-scroll transition-all duration-700">
          <HowItWorksSection />
        </div>

        {/* AI Solutions & RAG Pipeline */}
        <div className="animate-on-scroll transition-all duration-700">
          <AiSolutionSection />
        </div>

        {/* Live Chat & RAG Simulation */}
        <div className="animate-on-scroll transition-all duration-700">
          <LiveChatDemoSection />
        </div>

        {/* Comparison Section: Traditional vs AI Platform */}
        <div className="animate-on-scroll transition-all duration-700">
          <ComparisonSection />
        </div>

        {/* Transparent Pricing Plans */}
        <div className="animate-on-scroll transition-all duration-700">
          <PricingSection />
        </div>

        {/* Frequently Asked Questions */}
        <div className="animate-on-scroll transition-all duration-700">
          <FaqSection />
        </div>
      </main>

      {/* 3. Footer with Final CTA */}
      <LandingFooter />
    </div>
  )
}
