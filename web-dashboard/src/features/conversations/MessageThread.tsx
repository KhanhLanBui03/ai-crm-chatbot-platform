import { ArrowLeft, Bot, Check, Lock, Send, UserPlus } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'

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
  onQuayLai,
  dangThaoTac = false,
  onGui,
  dangGui = false,
  nguoiKhacGiu = null,
  thaoTacPhanCong,
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
  onQuayLai?: () => void
  dangThaoTac?: boolean
  /** UC013 — gửi tin. Trả `true` khi máy chủ nhận để xoá ô soạn; lỗi thì giữ nguyên chữ đã gõ. */
  onGui?: (noiDung: string) => Promise<boolean>
  dangGui?: boolean
  /** Tên người đang giữ hội thoại khi đó KHÔNG phải mình (và mình không phải quản trị viên). */
  nguoiKhacGiu?: string | null
  /** UC015 — "Giao cho…" (quản trị) và "Trả về hàng chờ" (người giữ / quản trị), do trang ghép vào. */
  thaoTacPhanCong?: React.ReactNode
}) {
  const khungCuon = useRef<HTMLDivElement>(null)
  const [nhap, datNhap] = useState('')
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

  const daDong = chiTiet.status === 'RESOLVED' || chiTiet.status === 'CLOSED'

  async function gui() {
    const noiDung = nhap.trim()
    if (!noiDung || dangGui || !onGui) return
    if (await onGui(noiDung)) datNhap('')
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col h-full">
      <div className="flex shrink-0 items-center gap-2 sm:gap-2.5 border-b p-3">
        {onQuayLai && (
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden size-8 -ml-1 shrink-0"
            onClick={onQuayLai}
            aria-label="Quay lại danh sách"
          >
            <ArrowLeft className="size-4" />
          </Button>
        )}
        <div className="bg-secondary text-secondary-foreground flex size-8 shrink-0 items-center justify-center rounded-full text-[13px] font-medium">
          {chuCaiDau(tenKhachHang)}
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-medium">{tenKhachHang}</span>
          <span className="text-muted-foreground text-xs truncate">
            {NHAN_KENH[chiTiet.channelType]} · {chiTiet.messageCount} tin nhắn
            {chiTiet.assignedUserName ? ` · ${chiTiet.assignedUserName} phụ trách` : ''}
          </span>
        </div>
        {/* Nút hiện theo trạng thái thật, không phải lúc nào cũng đủ ba nút: hội thoại tác tử
            đang giữ thì "Đánh dấu xong" là vô nghĩa, còn hội thoại đã có người thì "Nhận xử lý"
            chỉ tổ giành việc của đồng nghiệp. */}
        {daDong || nguoiKhacGiu ? null : chiTiet.autoReplyEnabled ? (
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

        {!daDong && thaoTacPhanCong}

        {!chiTiet.assignedUserName && !daDong && (
          <Button variant="outline" size="sm" disabled={dangThaoTac} onClick={onNhanXuLy}>
            <UserPlus />
            Nhận xử lý
          </Button>
        )}

        {!daDong && !nguoiKhacGiu && (
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

      {/* Gợi ý từ kho tri thức (cần RAG), mẫu câu và đính kèm chưa có — ẩn hẳn thay vì để nút bấm
          không làm gì (đã chốt giảm độ sâu UC013 3.1, b4). */}
      {daDong || nguoiKhacGiu ? (
        <div className="text-muted-foreground flex shrink-0 items-center gap-2 border-t p-3 text-[13px]">
          <Lock className="size-4" />
          {daDong
            ? 'Hội thoại đã đóng. Khách nhắn lại sẽ mở một hội thoại mới.'
            : `${nguoiKhacGiu} đang phụ trách hội thoại này — bạn chỉ xem được. Quản trị viên có thể giao lại.`}
        </div>
      ) : (
        <div className="flex shrink-0 flex-col gap-2 border-t p-3">
          <Textarea
            rows={3}
            placeholder={
              chiTiet.assignedUserName
                ? 'Soạn câu trả lời…'
                : 'Soạn câu trả lời… (gửi tin là bạn nhận hội thoại này, tác tử AI ngừng trả lời)'
            }
            className="resize-none"
            aria-label="Soạn câu trả lời"
            maxLength={4000}
            value={nhap}
            onChange={(e) => datNhap(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && !e.nativeEvent.isComposing) {
                e.preventDefault()
                void gui()
              }
            }}
          />
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-xs tabular-nums">
              {nhap.length.toLocaleString('vi-VN')}/4.000
            </span>
            <span className="flex-1" />
            <span className="text-muted-foreground text-xs">Ctrl/⌘ + Enter để gửi</span>
            <Button size="sm" disabled={!nhap.trim() || dangGui} onClick={() => void gui()}>
              <Send />
              {dangGui ? 'Đang gửi…' : 'Gửi'}
            </Button>
          </div>
        </div>
      )}
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
        {cuaBot && (tinNhan.citations?.length ?? 0) > 0 && (
          <span className="text-muted-foreground text-xs">
            Nguồn: {[...new Set(tinNhan.citations?.map((c) => c.documentTitle))].join(', ')}
          </span>
        )}
        <span className="text-muted-foreground text-xs tabular-nums">
          {format(new Date(tinNhan.createdAt), 'HH:mm')}
        </span>
      </div>
    </div>
  )
}
