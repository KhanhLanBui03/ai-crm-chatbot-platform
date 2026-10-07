import { useState } from 'react'
import { ChevronDown, HelpCircle } from 'lucide-react'

const faqs = [
  {
    q: 'Làm thế nào để nạp tài liệu cho AI học (RAG)?',
    a: 'Vào Tri thức → Tài liệu trên bảng điều khiển và tải lên tệp PDF, DOCX, TXT, Markdown hoặc HTML về sản phẩm, chính sách. Hệ thống chia đoạn, vector hoá rồi mới dùng để trả lời — theo dõi ở mục Tiến độ nạp; xử lý xong thì AI bắt đầu trích dẫn tài liệu đó.',
  },
  {
    q: 'Nhúng khung chat vào website như thế nào?',
    a: 'Tại Cài đặt → Web Widget, khai báo tên miền website của bạn, bấm "Sinh mã nhúng" rồi dán một thẻ <script> ngay trước thẻ </body>. Website nào cho chèn thẻ script đều dùng được. Widget chỉ hiện trên tên miền đã khai báo — người khác chép mã sang site của họ thì không chạy.',
  },
  {
    q: 'AI không trả lời được thì sao?',
    a: 'AI không đoán bừa: câu hỏi ngoài tài liệu thì nói chưa có thông tin và mời gặp nhân viên. Khách bấm "Gặp nhân viên" (hoặc AI tự chuyển khi không chắc) thì hội thoại vào Hộp thư, giao cho người đang trực; khách có thể để lại số điện thoại để được gọi lại.',
  },
  {
    q: 'Dữ liệu của công ty tôi có bị lẫn sang doanh nghiệp khác không?',
    a: 'Không. Dữ liệu mỗi doanh nghiệp được tách ngay ở tầng cơ sở dữ liệu bằng PostgreSQL Row-Level Security: mỗi truy vấn chỉ thấy dòng của đúng doanh nghiệp đang đăng nhập, kể cả kho tri thức của AI.',
  },
  {
    q: 'Hệ thống xử lý dữ liệu cá nhân theo Nghị định 13/2023 ra sao?',
    a: 'Khách để lại thông tin phải tích ô đồng ý trước; hồ sơ ghi nhận thời điểm và nguồn đồng ý. Thao tác quan trọng được ghi nhật ký kiểm toán, và nhật ký không chép tên hay số điện thoại của khách. Quy trình yêu cầu xoá dữ liệu cá nhân đang được hoàn thiện.',
  },
  {
    q: 'Chính sách dùng thử như thế nào?',
    a: 'Đăng ký là được 14 ngày dùng thử miễn phí, không cần thẻ thanh toán, theo hạn mức của gói Dùng thử. Hết hạn thì chọn một gói trả phí trong phần Cài đặt để tiếp tục.',
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
