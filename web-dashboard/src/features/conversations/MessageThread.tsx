import { format } from 'date-fns'
import { Bot, Check, Paperclip, Sparkles, UserPlus } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { Textarea } from '@/components/ui/textarea'
import { NHAN_KENH } from '@/features/conversations/nhan'
import { chuCaiDau } from '@/utils/ten'
import type { HoiThoaiChiTiet, TinNhan } from '@/types/schema'
import { cn } from '@/utils/cn'

export function MessageThread({
  chiTiet,
  tenKhachHang,
  dangTai,
  dangGo = false,
  onNhanXuLy,
  onDanhDauXong,
  onChuyenGiao,
  dangThaoTac = false,
}: {
  chiTiet: HoiThoaiChiTiet | undefined
  tenKhachHang: string
  dangTai: boolean
  /** Khách đang gõ — khung `AGENT_TYPING` của giao ước thời gian thực. */
  dangGo?: boolean
  /** SCR021 — nhận về mình, kết thúc, chuyển giao giữa tác tử AI và người. */
  onNhanXuLy?: () => void
  onDanhDauXong?: () => void
  onChuyenGiao?: (huong: 'BOT_TO_AGENT' | 'AGENT_TO_BOT') => void
  dangThaoTac?: boolean
}) {
  const khungCuon = useRef<HTMLDivElement>(null)
  const soTin = chiTiet?.messages.length ?? 0

  useEffect(() => {
    const el = khungCuon.current
    if (!el) return
    // Chỉ tự cuộn khi người dùng đang ở gần đáy. Đang đọc lại đoạn hội thoại cũ mà bị giật
    // xuống đáy vì khách vừa nhắn là khó chịu hơn nhiều so với việc bỏ lỡ một tin.
    const conCachDay = el.scrollHeight - el.scrollTop - el.clientHeight
    if (conCachDay < 160) el.scrollTop = el.scrollHeight
  }, [soTin, dangGo])

  if (dangTai || !chiTiet) {
    return (
      <div className="flex min-w-0 flex-1 flex-col gap-3 p-4">
        <Skeleton className="h-10 w-2/3 self-start rounded-xl" />
        <Skeleton className="h-16 w-3/4 self-end rounded-xl" />
        <Skeleton className="h-10 w-1/2 self-start rounded-xl" />
      </div>
    )
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center gap-2.5 border-b p-3">
        <div className="bg-secondary text-secondary-foreground flex size-8 shrink-0 items-center justify-center rounded-full text-[13px] font-medium">
          {chuCaiDau(tenKhachHang)}
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-medium">{tenKhachHang}</span>
          <span className="text-muted-foreground text-xs">
            {NHAN_KENH[chiTiet.channelType]} · {chiTiet.messageCount} tin nhắn
            {chiTiet.assignedUserName ? ` · ${chiTiet.assignedUserName} phụ trách` : ''}
          </span>
        </div>
        {/* Nút hiện theo trạng thái thật, không phải lúc nào cũng đủ ba nút: hội thoại tác tử
            đang giữ thì "Đánh dấu xong" là vô nghĩa, còn hội thoại đã có người thì "Nhận xử lý"
            chỉ tổ giành việc của đồng nghiệp. */}
        {chiTiet.autoReplyEnabled ? (
          <Button
            variant="outline"
            size="sm"
            disabled={dangThaoTac}
            onClick={() => onChuyenGiao?.('BOT_TO_AGENT')}
          >
            <UserPlus />
            Chuyển cho người
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            disabled={dangThaoTac}
            onClick={() => onChuyenGiao?.('AGENT_TO_BOT')}
          >
            <Bot />
            Trả lại cho AI
          </Button>
        )}

        {!chiTiet.assignedUserName && (
          <Button variant="outline" size="sm" disabled={dangThaoTac} onClick={onNhanXuLy}>
            <UserPlus />
            Nhận xử lý
          </Button>
        )}

        {chiTiet.status !== 'RESOLVED' && chiTiet.status !== 'CLOSED' && (
          <Button variant="outline" size="sm" disabled={dangThaoTac} onClick={onDanhDauXong}>
            <Check />
            Đánh dấu xong
          </Button>
        )}
      </div>

      <div ref={khungCuon} className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4">
        {chiTiet.messages.map((tn) => (
          <BongTinNhan key={tn.id} tinNhan={tn} />
        ))}
        {dangGo && <DangGo ten={tenKhachHang} />}
      </div>

      <div className="flex shrink-0 flex-col gap-2 border-t p-3">
        <div className="flex gap-1.5">
          <Button variant="outline" size="sm" className="border-dashed">
            <Sparkles />
            Dùng gợi ý của AI
          </Button>
          <Button variant="outline" size="sm" className="border-dashed">
            / Mẫu câu trả lời
          </Button>
        </div>
        <Textarea
          rows={3}
          placeholder="Soạn câu trả lời…"
          className="resize-none"
          aria-label="Soạn câu trả lời"
        />
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="text-muted-foreground">
            <Paperclip />
            Đính kèm
          </Button>
          <span className="flex-1" />
          <span className="text-muted-foreground text-xs">⌘↵ để gửi</span>
          <Button size="sm">Gửi</Button>
        </div>
      </div>
    </div>
  )
}

/** Ba chấm nảy, đặt đúng chỗ bong bóng tiếp theo sẽ hiện ra để dòng chảy không giật. */
function DangGo({ ten }: { ten: string }) {
  return (
    <div className="flex justify-start" role="status" aria-live="polite">
      <span className="sr-only">{ten} đang gõ</span>
      <div className="bg-muted flex items-center gap-1 rounded-xl px-3 py-2.5" aria-hidden>
        {[0, 150, 300].map((tre) => (
          <span
            key={tre}
            className="bg-muted-foreground/60 size-1.5 animate-bounce rounded-full"
            style={{ animationDelay: `${tre}ms` }}
          />
        ))}
      </div>
    </div>
  )
}

function BongTinNhan({ tinNhan }: { tinNhan: TinNhan }) {
  // Ghi chú hệ thống canh giữa, không phải bong bóng của bất kỳ ai
  if (tinNhan.senderType === 'SYSTEM') {
    return (
      <div className="flex justify-center">
        <div className="border-border text-muted-foreground max-w-[82%] rounded-xl border px-3 py-2 text-[13px] leading-relaxed">
          {tinNhan.content}
        </div>
      </div>
    )
  }

  const cuaKhach = tinNhan.senderType === 'CUSTOMER'
  const cuaBot = tinNhan.senderType === 'BOT'

  return (
    <div className={cn('flex', cuaKhach ? 'justify-start' : 'justify-end')}>
      <div className={cn('flex max-w-[82%] flex-col gap-1', cuaKhach ? 'items-start' : 'items-end')}>
        {!cuaKhach && (
          <StatusChip sacThai={cuaBot ? 'info' : 'neutral'} className="h-[18px] text-[11px]">
            {cuaBot ? 'Tác tử AI' : (tinNhan.senderName ?? 'Nhân viên')}
          </StatusChip>
        )}
        <div
          className={cn(
            'rounded-xl px-3 py-2 text-sm leading-relaxed whitespace-pre-line',
            cuaKhach && 'bg-muted',
            cuaBot && 'bg-card ring-foreground/10 ring-1',
            !cuaKhach && !cuaBot && 'bg-primary text-primary-foreground',
          )}
        >
          {tinNhan.content}
        </div>
        <span className="text-muted-foreground text-xs tabular-nums">
          {format(new Date(tinNhan.createdAt), 'HH:mm')}
        </span>
      </div>
    </div>
  )
}
