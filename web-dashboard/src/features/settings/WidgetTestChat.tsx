import { Bot, RotateCcw, Send, UserRound } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { laLoiTruyVan } from '@/api/baseQuery'
import { type KetQuaThuChatbot, useThuChatbotWidgetMutation } from '@/api/channels'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { StatusChip } from '@/components/ui/status-chip'
import { Textarea } from '@/components/ui/textarea'

interface LuotThu {
  vai: 'user' | 'assistant'
  noiDung: string
  ketQua?: KetQuaThuChatbot
}

/**
 * Khung THỬ chatbot ngay trên trang cấu hình (UC009 bước 4) — như khung test của Copilot Studio:
 * hỏi thử trước khi dán mã lên website. Gọi AI thật nhưng máy chủ **không lưu** gì: không hội
 * thoại, không hồ sơ khách, không tính hạn mức. Lịch sử thử chỉ sống trong state của trang.
 */
export function WidgetTestChat() {
  const [luot, datLuot] = useState<LuotThu[]>([])
  const [nhap, datNhap] = useState('')
  const [hoi, ketQua] = useThuChatbotWidgetMutation()
  const cuoi = useRef<HTMLDivElement>(null)

  useEffect(() => {
    cuoi.current?.scrollIntoView({ block: 'nearest' })
  }, [luot, ketQua.isLoading])

  async function gui() {
    const cau = nhap.trim()
    if (!cau || ketQua.isLoading) return
    const lichSu = luot.map((l) => ({ role: l.vai, content: l.noiDung }))
    datLuot((cu) => [...cu, { vai: 'user', noiDung: cau }])
    datNhap('')
    try {
      const kq = await hoi({ message: cau, history: lichSu }).unwrap()
      datLuot((cu) => [...cu, { vai: 'assistant', noiDung: kq.answer, ketQua: kq }])
    } catch {
      /* lỗi hiện qua ketQua.error bên dưới */
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="bg-muted/30 flex h-72 flex-col gap-2 overflow-y-auto rounded-lg border p-3">
        {luot.length === 0 && (
          <p className="text-muted-foreground m-auto max-w-xs text-center text-[13px]">
            Hỏi thử như một khách hàng, ví dụ "Gói Pro giá bao nhiêu?". Câu trả lời dùng đúng kho tri
            thức của doanh nghiệp bạn.
          </p>
        )}
        {luot.map((l, i) => (
          <div key={i} className={l.vai === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div className="flex max-w-[85%] flex-col gap-1">
              <span className="text-muted-foreground flex items-center gap-1 text-xs">
                {l.vai === 'user' ? <UserRound className="size-3" /> : <Bot className="size-3" />}
                {l.vai === 'user' ? 'Bạn (vai khách)' : 'Trợ lý AI'}
              </span>
              <div
                className={
                  l.vai === 'user'
                    ? 'bg-primary text-primary-foreground rounded-lg px-3 py-2 text-[13px] whitespace-pre-line'
                    : 'bg-background rounded-lg border px-3 py-2 text-[13px] whitespace-pre-line'
                }
              >
                {l.noiDung || <span className="text-muted-foreground italic">(không có câu trả lời)</span>}
              </div>
              {l.ketQua && (
                <div className="flex flex-wrap items-center gap-1.5">
                  {l.ketQua.handoff && (
                    <StatusChip sacThai="warning">Trên site thật: chuyển cho nhân viên</StatusChip>
                  )}
                  {l.ketQua.refused && <StatusChip sacThai="neutral">Từ chối vì thiếu căn cứ</StatusChip>}
                  {[...new Set(l.ketQua.citations.map((c) => c.title).filter(Boolean))].map((t) => (
                    <StatusChip key={t} sacThai="info">
                      Nguồn: {t}
                    </StatusChip>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {ketQua.isLoading && <p className="text-muted-foreground text-xs italic">Đang trả lời…</p>}
        <div ref={cuoi} />
      </div>

      {ketQua.isError && (
        <Alert variant="destructive">
          <AlertDescription>
            {laLoiTruyVan(ketQua.error) ? ketQua.error.message : 'Không gọi được trợ lý AI.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="flex items-end gap-1.5">
        <Textarea
          rows={2}
          className="resize-none"
          maxLength={1000}
          placeholder="Nhập câu hỏi thử…"
          aria-label="Câu hỏi thử"
          value={nhap}
          onChange={(e) => datNhap(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              void gui()
            }
          }}
        />
        <div className="flex flex-col gap-1.5">
          <Button size="sm" onClick={() => void gui()} disabled={!nhap.trim() || ketQua.isLoading}>
            <Send />
            Gửi
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={luot.length === 0}
            onClick={() => {
              datLuot([])
              ketQua.reset()
            }}
          >
            <RotateCcw />
            Làm mới
          </Button>
        </div>
      </div>
    </div>
  )
}
