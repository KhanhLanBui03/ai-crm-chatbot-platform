import { useEffect } from 'react'

import { AiSolutionSection } from './components/AiSolutionSection'
import { ComparisonSection } from './components/ComparisonSection'
import { FaqSection } from './components/FaqSection'
import { FeatureBentoGrid } from './components/FeatureBentoGrid'
import { HeroSection } from './components/HeroSection'
import { LandingFooter } from './components/LandingFooter'
import { LandingNavbar } from './components/LandingNavbar'
import { LiveChatDemoSection } from './components/LiveChatDemoSection'
import { PricingSection } from './components/PricingSection'
import { StatsBar } from './components/StatsBar'

export function LandingPage() {
  // Intersection Observer for delicate scroll animations
  useEffect(() => {
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
    sections.forEach((s) => observer.observe(s))

    return () => observer.disconnect()
  }, [])

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 selection:text-primary overflow-x-hidden font-sans">
      {/* 1. Header & Navigation */}
      <LandingNavbar />

      {/* 2. Main Content */}
      <main className="flex flex-col">
        {/* Hero Section */}
        <div className="animate-on-scroll transition-all duration-700 opacity-100 translate-y-0">
          <HeroSection />
        </div>

        {/* Stats Counter Bar */}
        <div className="animate-on-scroll transition-all duration-700 opacity-0 translate-y-6">
          <StatsBar />
        </div>

        {/* Bento Grid Core Features */}
        <div className="animate-on-scroll transition-all duration-700 opacity-0 translate-y-6">
          <FeatureBentoGrid />
        </div>

        {/* AI Solutions & RAG Pipeline */}
        <div className="animate-on-scroll transition-all duration-700 opacity-0 translate-y-6">
          <AiSolutionSection />
        </div>

        {/* Live Chat & RAG Simulation */}
        <div className="animate-on-scroll transition-all duration-700 opacity-0 translate-y-6">
          <LiveChatDemoSection />
        </div>

        {/* Comparison Section: Traditional vs AI Platform */}
        <div className="animate-on-scroll transition-all duration-700 opacity-0 translate-y-6">
          <ComparisonSection />
        </div>

        {/* Transparent Pricing Plans */}
        <div className="animate-on-scroll transition-all duration-700 opacity-0 translate-y-6">
          <PricingSection />
        </div>

        {/* Frequently Asked Questions */}
        <div className="animate-on-scroll transition-all duration-700 opacity-0 translate-y-6">
          <FaqSection />
        </div>
      </main>

      {/* 3. Footer with Final CTA */}
      <LandingFooter />
    </div>
  )
}
