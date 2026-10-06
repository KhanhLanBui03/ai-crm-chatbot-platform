import { useState } from 'react'
import { ChevronDown, HelpCircle } from 'lucide-react'

const faqs = [
  {
    q: 'Làm thế nào để nạp tài liệu cho AI học (công nghệ RAG)?',
    a: 'Bạn chỉ cần vào mục "Kho tri thức" trong Dashboard và tải lên các tệp PDF, Word (DOCX) hoặc tài liệu văn bản về sản phẩm/chính sách. Hệ thống tự động phân tích (chunking), tạo vector embeddings và đưa vào cơ sở dữ liệu pgvector. Ngay lập tức AI có thể trả lời khách hàng theo đúng nội dung trong tài liệu.',
  },
  {
    q: 'Nhúng khung chat Livechat vào website mất bao lâu?',
    a: 'Chỉ mất chưa đầy 1 phút! Tại mục "Cài đặt Widget", bạn sao chép 1 dòng mã script HTML và dán vào phần thẻ <head> hoặc trước thẻ </body> trên website của bạn (hỗ trợ cả WordPress, Shopify, Next.js, React, Vue, HTML tĩnh). Khung chat sẽ xuất hiện ngay lập tức.',
  },
  {
    q: 'Dữ liệu của công ty tôi có bị lộ sang các doanh nghiệp khác không?',
    a: 'Tuyệt đối không! Kiến trúc đa khách thuê (Multi-tenant) của chúng tôi áp dụng cơ chế phân quyền cấp dòng PostgreSQL Row-Level Security (RLS). Mọi câu truy vấn dữ liệu từ API đều được gắn ngữ cảnh tenant_id nghiêm ngặt, đảm bảo dữ liệu mỗi công ty được cô lập 100%.',
  },
  {
    q: 'Hệ thống có tuân thủ quy định bảo vệ dữ liệu cá nhân (Nghị định 13/2023) không?',
    a: 'Có! Hệ thống được thiết kế tuân thủ nghiêm ngặt Nghị định 13/2023/NĐ-CP: toàn bộ thao tác truy xuất dữ liệu đều được ghi nhật ký kiểm toán bất biến (Audit Log) và có sẵn quy trình xử lý quyền yêu cầu xóa dữ liệu cá nhân (Right to be Forgotten).',
  },
  {
    q: 'Trợ lý AI có thể tự động tra cứu đơn hàng hoặc đặt lịch hẹn không?',
    a: 'Có! Thông qua giao thức chuẩn Model Context Protocol (MCP) và cơ chế Tool Calling, bạn có thể cấp quyền cho AI gọi các API nội bộ để tra cứu trạng thái đơn hàng, kiểm tra lịch trống và tự động tạo lịch hẹn/cơ hội kinh doanh vào CRM.',
  },
  {
    q: 'Chính sách dùng thử miễn phí như thế nào?',
    a: 'Khi đăng ký tài khoản mới, bạn được tặng ngay 14 ngày dùng thử miễn phí toàn bộ tính năng cao cấp không giới hạn và không yêu cầu thẻ tín dụng. Sau thời gian dùng thử, bạn có thể tiếp tục sử dụng gói Starter miễn phí hoặc nâng cấp lên gói Pro.',
  },
]

export function FaqSection() {
  const [openIdx, setOpenIdx] = useState<number | null>(0)

  return (
    <section id="faq" className="py-24 relative">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <HelpCircle className="size-3.5" />
            <span>Giải Đáp Thắc Mắc</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Câu Hỏi Thường Gặp
          </h2>
          <p className="mt-3 text-base text-muted-foreground">
            Mọi thông tin bạn cần biết về nền tảng CRM & Chatbot AI thế hệ mới.
          </p>
        </div>

        {/* Accordion list */}
        <div className="space-y-3.5">
          {faqs.map((faq, idx) => {
            const isOpen = openIdx === idx
            return (
              <div
                key={idx}
                className="rounded-2xl border border-border bg-card overflow-hidden transition-all duration-200"
              >
                <button
                  type="button"
                  onClick={() => setOpenIdx(isOpen ? null : idx)}
                  className="w-full px-6 py-4.5 text-left flex items-center justify-between gap-4 font-semibold text-sm sm:text-base text-foreground hover:text-primary transition-colors cursor-pointer"
                >
                  <span>{faq.q}</span>
                  <ChevronDown
                    className={`size-4.5 text-muted-foreground shrink-0 transition-transform duration-200 ${
                      isOpen ? 'rotate-180 text-primary' : ''
                    }`}
                  />
                </button>
                {isOpen && (
                  <div className="px-6 pb-5 pt-1 text-sm text-muted-foreground leading-relaxed border-t border-border/50 animate-in fade-in-50 duration-200">
                    {faq.a}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
