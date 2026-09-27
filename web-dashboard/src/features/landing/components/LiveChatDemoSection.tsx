import { useState } from 'react'
import { Bot, Send, Sparkles, User } from 'lucide-react'

import { Button } from '@/components/ui/button'

const sampleQuestions = [
  'Nền tảng này hỗ trợ nhúng widget vào website nào?',
  'Công nghệ RAG hoạt động như thế nào?',
  'Dữ liệu của doanh nghiệp tôi có được bảo mật không?',
  'Tôi có thể dùng thử miễn phí trong bao lâu?',
]

interface Message {
  sender: 'user' | 'ai'
  text: string
  source?: string
  confidence?: string
}

export function LiveChatDemoSection() {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'ai',
      text: 'Xin chào! Tôi là Trợ lý AI của CRM Platform. Tôi có thể giải đáp mọi thắc mắc về tính năng, bảng giá hoặc cách tích hợp hệ thống cho doanh nghiệp bạn. Bạn muốn tìm hiểu gì hôm nay?',
    },
  ])
  const [inputVal, setInputVal] = useState('')
  const [isTyping, setIsTyping] = useState(false)

  function handleSend(questionText?: string) {
    const textToSend = questionText || inputVal.trim()
    if (!textToSend || isTyping) return

    const newMsgs: Message[] = [...messages, { sender: 'user', text: textToSend }]
    setMessages(newMsgs)
    setInputVal('')
    setIsTyping(true)

    // Simulate smart AI response with RAG citation
    setTimeout(() => {
      let replyText =
        'Dạ cảm ơn câu hỏi của bạn! Nền tảng AI-CRM hỗ trợ tích hợp livechat đa kênh chỉ với 1 dòng mã script, phân tích dữ liệu RAG độ chính xác cao và quản lý phễu khách hàng tự động.'
      let sourceName = 'Tài liệu Tổng quan Sản phẩm v2.0'
      const lower = textToSend.toLowerCase()

      if (lower.includes('nhúng') || lower.includes('website') || lower.includes('widget')) {
        replyText =
          'Bạn có thể nhúng widget vào mọi nền tảng: WordPress, Next.js, React, Vue, Shopify hay các trang HTML tĩnh chỉ bằng cách sao chép 1 dòng mã script trong mục Cài đặt Widget.'
        sourceName = 'Hướng dẫn Cài đặt Livechat Widget (Trang 2)'
      } else if (lower.includes('rag') || lower.includes('tài liệu') || lower.includes('học')) {
        replyText =
          'Hệ thống RAG tự động băm nhỏ tài liệu (chunking), sinh vector embeddings và lưu vào PostgreSQL pgvector. Khi khách hỏi, AI tìm kiếm ngữ nghĩa chính xác trong tài liệu công ty bạn và trả lời kèm trích dẫn nguồn.'
        sourceName = 'Kiến trúc Kỹ thuật RAG Engine v2.0'
      } else if (lower.includes('bảo mật') || lower.includes('dữ liệu') || lower.includes('an toàn')) {
        replyText =
          'Dữ liệu mỗi doanh nghiệp được cô lập 100% nhờ chính sách Row-Level Security (RLS) của PostgreSQL. Đồng thời hệ thống tuân thủ Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân.'
        sourceName = 'Chính sách Bảo mật & Tuân thủ NĐ 13/2023'
      } else if (lower.includes('miễn phí') || lower.includes('dùng thử') || lower.includes('giá')) {
        replyText =
          'Bạn được trải nghiệm dùng thử miễn phí 14 ngày không giới hạn tính năng và không cần nhập thẻ tín dụng. Sau đó có thể chọn gói Starter (0đ), Pro (499k/tháng) hoặc Enterprise.'
        sourceName = 'Bảng giá & Chính sách Dùng thử'
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: replyText,
          source: sourceName,
          confidence: '99.4%',
        },
      ])
      setIsTyping(false)
    }, 600)
  }

  return (
    <section id="demo-livechat" className="py-24 bg-muted/20 border-y border-border/60 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <Sparkles className="size-3.5" />
            <span>Trải Nghiệm Trực Tiếp</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Thử nghiệm Chat với <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-primary to-indigo-600 bg-clip-text text-transparent">
              Trợ Lý AI Doanh Nghiệp
            </span>
          </h2>
          <p className="mt-3 text-base text-muted-foreground">
            Bấm chọn câu hỏi mẫu bên dưới hoặc nhập câu hỏi bất kỳ để cảm nhận tốc độ và độ chuẩn xác của AI RAG.
          </p>
        </div>

        {/* Live Chat Box Simulation */}
        <div className="max-w-3xl mx-auto bg-card border border-border rounded-2xl shadow-xl overflow-hidden flex flex-col h-[520px]">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3.5 bg-muted/50 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="size-9 rounded-xl bg-primary text-primary-foreground flex items-center justify-center font-bold shadow-xs">
                <Bot className="size-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-foreground">AI Support Agent (RAG Demo)</h4>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                  <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Đang hoạt động • Phản hồi trong 0.4s
                </p>
              </div>
            </div>
            <span className="text-[11px] font-mono text-muted-foreground bg-muted px-2.5 py-1 rounded-md border border-border">
              pgvector RAG
            </span>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5 flex flex-col gap-3.5 space-y-1">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-2.5 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.sender === 'ai' && (
                  <div className="size-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="size-4" />
                  </div>
                )}
                <div
                  className={`p-3 rounded-2xl text-sm leading-relaxed max-w-[85%] ${
                    m.sender === 'user'
                      ? 'bg-primary text-primary-foreground rounded-tr-xs shadow-xs'
                      : 'bg-muted/70 text-foreground rounded-tl-xs border border-border/60'
                  }`}
                >
                  <p>{m.text}</p>
                  {m.source && (
                    <div className="mt-2 pt-2 border-t border-border/60 flex items-center justify-between text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Sparkles className="size-3 text-primary" />
                        Trích dẫn: <strong className="text-foreground">{m.source}</strong>
                      </span>
                      {m.confidence && (
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                          {m.confidence}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                {m.sender === 'user' && (
                  <div className="size-7 rounded-lg bg-primary text-primary-foreground flex items-center justify-center shrink-0 mt-0.5">
                    <User className="size-4" />
                  </div>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground pl-9">
                <span className="size-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                <span className="size-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                <span className="size-1.5 rounded-full bg-primary animate-bounce" />
                <span>AI đang tra cứu tài liệu...</span>
              </div>
            )}
          </div>

          {/* Quick suggestions pills */}
          <div className="px-4 py-2 bg-muted/30 border-t border-border/60 flex items-center gap-2 overflow-x-auto text-xs no-scrollbar">
            <span className="text-muted-foreground shrink-0 font-medium">Gợi ý:</span>
            {sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(q)}
                disabled={isTyping}
                className="shrink-0 px-2.5 py-1 rounded-full bg-background border border-border hover:border-primary/40 text-muted-foreground hover:text-foreground transition-all cursor-pointer text-xs"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="p-3 bg-background border-t border-border flex items-center gap-2"
          >
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="Nhập câu hỏi của bạn cho Trợ lý AI..."
              className="flex-1 bg-muted/40 border border-input rounded-xl px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
            <Button
              type="submit"
              size="default"
              disabled={!inputVal.trim() || isTyping}
              className="rounded-xl px-4"
            >
              <Send className="size-4" />
              <span className="hidden sm:inline ml-1.5">Gửi</span>
            </Button>
          </form>
        </div>
      </div>
    </section>
  )
}
