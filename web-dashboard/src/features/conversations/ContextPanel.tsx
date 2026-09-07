import { Ban, Check, Clock, FileText, Wrench } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip, type SacThai } from '@/components/ui/status-chip'
import { chuCaiDau } from '@/utils/ten'
import type { KetQuaKiemDuyet, NguCanhHoiThoai, NhanhXuLyAi } from '@/types/schema'
import { cn } from '@/utils/cn'

const NHAN_DINH_TUYEN: Record<NhanhXuLyAi, string> = {
  SMALL_TALK: 'Trò chuyện',
  RAG: 'Truy hồi tri thức',
  TOOL_CALL: 'Gọi công cụ',
  CLARIFY: 'Hỏi lại',
  HANDOFF: 'Chuyển giao',
  SUMMARY: 'Tóm tắt',
  EXTRACTION: 'Trích xuất',
}

const NHAN_CHAN: Record<KetQuaKiemDuyet, { nhan: string; sacThai: SacThai }> = {
  ALLOWED: { nhan: 'Cho phép', sacThai: 'success' },
  BLOCKED: { nhan: 'Bị chặn', sacThai: 'destructive' },
  NEEDS_APPROVAL: { nhan: 'Chờ duyệt', sacThai: 'warning' },
}

/**
 * Cột ngữ cảnh — phần cho nhân viên KIỂM ĐƯỢC câu trả lời của tác tử AI.
 * Đọc từ `sales.lead_scores`, `ai.ai_interactions` và `integration.tool_call_logs`.
 */
export function ContextPanel({
  nguCanh,
  dangTai,
}: {
  nguCanh: NguCanhHoiThoai | undefined
  dangTai: boolean
}) {
  if (dangTai || !nguCanh) {
    return (
      <div className="flex w-80 shrink-0 flex-col gap-4 border-l p-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  const { contact, leadScore, lastAiInteraction: ai } = nguCanh
  const diem = leadScore?.score ?? null
  const yeuTo = leadScore?.topFactors ?? []
  const tenKhach = contact.fullName ?? 'Khách chưa để lại tên'
  const mauDiem =
    diem === null ? 'text-muted-foreground' : diem >= 70 ? 'text-success' : 'text-muted-foreground'

  // Giao ước để gần như mọi trường của lượt xử lý AI là tuỳ chọn — hội thoại vừa mở thì chưa có
  // lượt nào, và một lượt `SMALL_TALK` không có độ bám nguồn lẫn trích dẫn.
  const bamNguon = ai?.groundednessScore ?? null
  const trichDan = ai?.citations ?? []
  const goiCongCu = ai?.toolCalls ?? []
  const doTre =
    ai?.latencyMs == null
      ? '—'
      : `${(ai.latencyMs / 1000).toLocaleString('vi-VN', {
          minimumFractionDigits: 1,
          maximumFractionDigits: 1,
        })} giây`

  return (
    <div className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l p-4">
      <div className="flex items-center gap-2.5">
        <div className="bg-secondary text-secondary-foreground flex size-10 shrink-0 items-center justify-center rounded-full text-[15px] font-medium">
          {chuCaiDau(tenKhach)}
        </div>
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-medium">{tenKhach}</span>
          <span className="text-muted-foreground truncate text-xs tabular-nums">
            {[contact.phone, contact.email].filter(Boolean).join(' · ')}
          </span>
        </div>
      </div>

      <div className="flex gap-1.5">
        <Button variant="outline" size="sm" className="flex-1">
          Mở hồ sơ
        </Button>
        <Button variant="outline" size="sm" className="flex-1">
          Ghi chú
        </Button>
      </div>

      {contact.tags && contact.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {contact.tags.map((the) => (
            <StatusChip key={the.id}>{the.name}</StatusChip>
          ))}
        </div>
      )}

      <Separator />

      <div className="flex flex-col gap-2.5">
        <div className="flex items-baseline gap-2">
          <span className="flex-1 text-[13px] font-medium">Điểm tiềm năng</span>
          <span className={cn('text-xl font-semibold tabular-nums', mauDiem)}>{diem ?? '—'}</span>
        </div>
        <Progress value={diem ?? 0} className="h-1.5" />
        {/* Ba yếu tố đóng góp nhiều nhất — thứ trả lời "vì sao khách này được 92 điểm?" */}
        {yeuTo.map((y) => (
          <div key={y.name} className="flex items-baseline gap-2 text-xs">
            <span className="text-muted-foreground flex-1">{y.name}</span>
            <span
              className={cn(
                'font-medium tabular-nums',
                y.contribution > 0 ? 'text-success' : 'text-muted-foreground',
              )}
            >
              {y.contribution > 0 ? `+${y.contribution}` : `−${Math.abs(y.contribution)}`}
            </span>
          </div>
        ))}
      </div>

      {ai && (
        <>
          <Separator />
          <div className="flex flex-col gap-2.5">
            <span className="text-[13px] font-medium">Lượt xử lý gần nhất của AI</span>

            <HangThongSo nhan="Ý định" giaTri={ai.intentLabel ?? '—'} />
            <HangThongSo
              nhan="Độ tin cậy"
              giaTri={ai.intentConfidence === null || ai.intentConfidence === undefined ? '—' : dinhDangSo(ai.intentConfidence)}
              so
            />
            <HangThongSo nhan="Định tuyến" giaTri={NHAN_DINH_TUYEN[ai.route]} />
            <HangThongSo
              nhan="Độ bám nguồn"
              giaTri={bamNguon === null ? '—' : dinhDangSo(bamNguon)}
              so
              // Dưới ngưỡng 0,60 là lý do tác tử AI từ chối trả lời — phải nhìn ra ngay
              mau={
                bamNguon === null ? undefined : bamNguon < 0.6 ? 'text-destructive' : 'text-success'
              }
            />
            <HangThongSo
              nhan="Chi phí · độ trễ"
              giaTri={`${ai.costVnd.toLocaleString('vi-VN')} ₫ · ${doTre}`}
              so
            />

            {ai.refused && (
              <StatusChip sacThai="warning" BieuTuong={Clock}>
                Đã từ chối trả lời
              </StatusChip>
            )}

            {trichDan.length > 0 && (
              <>
                <span className="text-muted-foreground mt-0.5 text-xs">
                  Đoạn tri thức đã truy hồi ({trichDan.length})
                </span>
                {trichDan.map((td) => (
                  <div key={td.chunkId} className="bg-muted flex gap-1.5 rounded-md p-2">
                    <FileText className="text-muted-foreground mt-0.5 size-3.5 shrink-0" />
                    <div className="flex min-w-0 flex-col gap-0.5">
                      <span className="truncate text-xs font-medium">{td.documentTitle}</span>
                      <span className="text-muted-foreground text-xs">{td.sectionPath ?? '—'}</span>
                    </div>
                  </div>
                ))}
              </>
            )}

            {goiCongCu.length > 0 && (
              <>
                <span className="text-muted-foreground mt-0.5 text-xs">
                  Công cụ đã gọi ({goiCongCu.length})
                </span>
                {goiCongCu.map((cc) => {
                  const chan = NHAN_CHAN[cc.guardResult]
                  return (
                    <div key={cc.id} className="bg-muted flex items-center gap-1.5 rounded-md p-2">
                      <Wrench className="text-muted-foreground size-3.5 shrink-0" />
                      <span className="flex-1 truncate text-xs font-medium">{cc.toolName}</span>
                      <StatusChip
                        sacThai={chan.sacThai}
                        BieuTuong={cc.guardResult === 'ALLOWED' ? Check : Ban}
                      >
                        {chan.nhan}
                      </StatusChip>
                    </div>
                  )
                })}
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function dinhDangSo(v: number) {
  return v.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function HangThongSo({
  nhan,
  giaTri,
  so,
  mau,
}: {
  nhan: string
  giaTri: string
  so?: boolean
  mau?: string
}) {
  return (
    <div className="flex items-baseline gap-2 text-xs">
      <span className="text-muted-foreground flex-1">{nhan}</span>
      <span className={cn('font-medium', so && 'tabular-nums', mau)}>{giaTri}</span>
    </div>
  )
}
