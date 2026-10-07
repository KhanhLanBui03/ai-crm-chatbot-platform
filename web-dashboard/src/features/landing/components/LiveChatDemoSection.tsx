import { Bot, Headset, MessageCircle, MessageSquareText, UserRoundCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

/**
 * "Trải nghiệm Chat" bằng WIDGET THẬT — trước đây là kịch bản giả (`setTimeout` + câu trả lời viết sẵn)
 * gắn nhãn "pgvector RAG · 0.4s": gõ câu lạ là lộ.
 *
 * Nhúng đúng `widget.js` mà doanh nghiệp nhúng lên website, với khoá widget của một doanh nghiệp demo:
 *   VITE_DEMO_WIDGET_KEY   khoá công khai `wk_...` (Cài đặt → Web Widget) — trống thì ẩn khung chat
 *   VITE_WIDGET_SCRIPT_URL nơi phục vụ widget.js (mặc định http://localhost:5174/widget.js)
 *   VITE_WIDGET_API_URL    gateway công khai (mặc định http://localhost:8080)
 * Tên miền của trang chủ phải có trong "Tên miền cho phép" của widget đó, nếu không widget tự ẩn (403).
 * Tin nhắn ở đây là tin THẬT — vào Hộp thư của doanh nghiệp demo.
 */
const KHOA = import.meta.env.VITE_DEMO_WIDGET_KEY as string | undefined
const SCRIPT = (import.meta.env.VITE_WIDGET_SCRIPT_URL as string | undefined) || 'http://localhost:5174/widget.js'
const API = (import.meta.env.VITE_WIDGET_API_URL as string | undefined) || 'http://localhost:8080'

const BUOC = [
  { icon: MessageSquareText, tieuDe: 'Hỏi như một khách hàng', moTa: 'Ví dụ: "Gói Tăng trưởng giá bao nhiêu?"' },
  { icon: Bot, tieuDe: 'AI trả lời theo tài liệu', moTa: 'Kèm nguồn trích dẫn. Không có căn cứ thì AI nói chưa có thông tin.' },
  { icon: Headset, tieuDe: 'Bấm "Gặp nhân viên"', moTa: 'Hội thoại vào Hộp thư; nhân viên trả lời ngay trong khung chat này.' },
  { icon: UserRoundCheck, tieuDe: 'Để lại thông tin', moTa: 'Tên, số điện thoại kèm ô đồng ý lưu dữ liệu — hồ sơ khách tự cập nhật.' },
]

/** Bong bóng chat nằm trong Shadow DOM (mode "open") của widget — bấm hộ để mở khung chat. */
function moKhungChat(): boolean {
  const bong = document.getElementById('crm-ai-widget')?.shadowRoot?.querySelector<HTMLButtonElement>('.bong')
  bong?.click()
  return !!bong
}

export function LiveChatDemoSection() {
  const [sanSang, datSanSang] = useState(false)

  useEffect(() => {
    if (!KHOA) return
    const the = document.createElement('script')
    the.src = SCRIPT
    the.async = true
    the.dataset.widgetKey = KHOA
    the.dataset.apiUrl = API
    the.onload = () => datSanSang(true)
    document.body.appendChild(the)
    // Rời trang chủ (vào dashboard) thì gỡ widget — khung chat khách không được nằm trong trang quản trị
    return () => {
      the.remove()
      document.getElementById('crm-ai-widget')?.remove()
    }
  }, [])

  return (
    <section id="demo-livechat" className="py-24 bg-muted/20 border-y border-border/60">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <MessageCircle className="size-3.5" />
            <span>Trải Nghiệm Trực Tiếp</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Chat Với <span className="text-primary">Hệ Thống Thật</span>
          </h2>
          <p className="mt-3 text-base text-muted-foreground">
            Khung chat ở góc phải màn hình chính là widget doanh nghiệp nhúng lên website — không phải bản mô phỏng.
            Tin bạn gửi đi vào Hộp thư của một doanh nghiệp demo.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {BUOC.map((b, i) => (
            <div key={b.tieuDe} className="rounded-2xl border bg-card p-5">
              <div className="flex items-center gap-2">
                <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <b.icon className="size-4" />
                </span>
                <span className="text-xs font-semibold text-muted-foreground">Bước {i + 1}</span>
              </div>
              <h3 className="mt-3 text-sm font-bold text-foreground">{b.tieuDe}</h3>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{b.moTa}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col items-center gap-3">
          {KHOA ? (
            <>
              <Button size="lg" className="rounded-xl" disabled={!sanSang} onClick={() => moKhungChat()}>
                <MessageCircle />
                {sanSang ? 'Mở khung chat' : 'Đang tải khung chat…'}
              </Button>
              <p className="text-xs text-muted-foreground">Hoặc bấm bong bóng chat ở góc dưới bên phải.</p>
            </>
          ) : (
            <p className="max-w-md text-center text-sm text-muted-foreground">
              Khung chat demo chưa được bật trên trang này.{' '}
              <Link to="/dang-ky" className="font-medium text-primary underline underline-offset-2">
                Đăng ký dùng thử
              </Link>{' '}
              để nhúng widget lên website của bạn.
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
