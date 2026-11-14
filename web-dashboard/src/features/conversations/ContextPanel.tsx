import { format } from 'date-fns'
import { Ban, Check, Clock, FileText, Loader2, RefreshCw, Target, Wrench } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip, type SacThai } from '@/components/ui/status-chip'
import { chuCaiDau } from '@/utils/ten'
import type {
  KetQuaKiemDuyet,
  NguCanhHoiThoai,
  NhanhXuLyAi,
  TomTatHoiThoai,
} from '@/types/schema'
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

/** UC026 bước 1 — bốn sự kiện kích hoạt. Nhân viên đọc bản `CLOSING` (tổng kết) khác bản giữa chừng. */
const NHAN_KICH_HOAT: Record<TomTatHoiThoai['trigger'], string> = {
  HANDOFF: 'Sinh khi chuyển giao',
  CLOSING: 'Sinh khi kết thúc',
  TURN_THRESHOLD: 'Sinh giữa chừng',
  MANUAL: 'Nhân viên bấm tóm tắt lại',
}

const NHAN_CHAN: Record<KetQuaKiemDuyet, { nhan: string; sacThai: SacThai }> = {
  ALLOWED: { nhan: 'Cho phép', sacThai: 'success' },
  BLOCKED: { nhan: 'Bị chặn', sacThai: 'destructive' },
  NEEDS_APPROVAL: { nhan: 'Chờ duyệt', sacThai: 'warning' },
}

/**
 * Cột ngữ cảnh — phần cho nhân viên KIỂM ĐƯỢC câu trả lời của tác tử AI.
 * Đọc từ `sales.lead_scores`, `ai.ai_interactions` và `integration.tool_call_logs`.
 *
 * Khối "Tóm tắt" (UC026 bước 7) đứng ngay dưới hồ sơ khách: đó là thứ nhân viên tiếp nhận cần đọc
 * đầu tiên thay cho việc cuộn lại cả lịch sử.
 */
export function ContextPanel({
  nguCanh,
  dangTai,
  onTaoLead,
  onTomTatLai,
  dangTomTat,
  choTomTat,
}: {
  nguCanh: NguCanhHoiThoai | undefined
  dangTai: boolean
  /** UC032 1a — tạo lead cho khách của hội thoại này. */
  onTaoLead?: () => void
  /** UC026 trigger `MANUAL` — nút "Tóm tắt lại". */
  onTomTatLai?: () => void
  dangTomTat?: boolean
  /** Hội thoại vừa đóng, worker đang sinh bản `CLOSING` — hiện trạng thái chờ thay vì "Chưa có". */
  choTomTat?: boolean
}) {
  const dieuHuong = useNavigate()
  if (dangTai || !nguCanh) {
    return (
      <div className="hidden xl:flex w-80 shrink-0 flex-col gap-4 border-l p-4">
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
    <div className="hidden xl:flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l p-4">
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
        <Button
          variant="outline"
          size="sm"
          className="flex-1"
          onClick={() => dieuHuong(`/khach-hang/${contact.id}`)}
        >
          Mở hồ sơ
        </Button>
        {onTaoLead && (
          <Button variant="outline" size="sm" className="flex-1" onClick={onTaoLead}>
            <Target />
            Tạo lead
          </Button>
        )}
      </div>

      {contact.tags && contact.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {contact.tags.map((the) => (
            <StatusChip key={the.id}>{the.name}</StatusChip>
          ))}
        </div>
      )}

      <Separator />

      <KhoiTomTat
        tomTat={nguCanh.summary ?? null}
        onTomTatLai={onTomTatLai}
        dangTomTat={dangTomTat}
        choTomTat={choTomTat}
      />

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

/**
 * UC026 bước 7 — bốn phần có tên, kèm loại kích hoạt, thời điểm sinh và phiên bản mô hình (hậu điều
 * kiện: "lưu cùng bản tóm tắt"). `isStale` hiện thành chỉ báo thay vì giấu: đọc tóm tắt cũ mà tưởng là
 * mới thì tệ hơn không có tóm tắt.
 */
function KhoiTomTat({
  tomTat,
  onTomTatLai,
  dangTomTat,
  choTomTat,
}: {
  tomTat: TomTatHoiThoai | null
  onTomTatLai?: () => void
  dangTomTat?: boolean
  choTomTat?: boolean
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center gap-2">
        <span className="flex-1 text-[13px] font-medium">Tóm tắt hội thoại</span>
        {onTomTatLai && (
          <Button variant="ghost" size="sm" onClick={onTomTatLai} disabled={dangTomTat}>
            {dangTomTat ? <Loader2 className="animate-spin" /> : <RefreshCw />}
            {dangTomTat ? 'Đang tóm tắt…' : 'Tóm tắt lại'}
          </Button>
        )}
      </div>

      {tomTat ? (
        <>
          {tomTat.isStale && (
            <StatusChip sacThai="warning" BieuTuong={Clock}>
              Có tin mới sau bản tóm tắt này
            </StatusChip>
          )}
          <PhanTomTat nhan="Nhu cầu chính" noiDung={tomTat.mainNeed} />
          <PhanTomTat nhan="Thông tin khách đã cung cấp" noiDung={tomTat.providedInfo} />
          <PhanTomTat nhan="Vấn đề chưa giải quyết" noiDung={tomTat.unresolvedIssues} />
          <PhanTomTat nhan="Bước tiếp theo đề xuất" noiDung={tomTat.nextSteps} />
          <span className="text-muted-foreground text-xs">
            {NHAN_KICH_HOAT[tomTat.trigger]} ·{' '}
            <span className="tabular-nums">
              {format(new Date(tomTat.generatedAt), 'HH:mm dd/MM/yyyy')}
            </span>
            {tomTat.modelVersion && (
              <>
                {' · '}
                <span className="font-mono">{tomTat.modelVersion}</span>
              </>
            )}
          </span>
        </>
      ) : choTomTat ? (
        <span className="text-muted-foreground flex items-center gap-1.5 text-xs">
          <Loader2 className="size-3.5 animate-spin" />
          Đang tóm tắt hội thoại vừa kết thúc…
        </span>
      ) : (
        <span className="text-muted-foreground text-xs">
          Chưa có bản tóm tắt. Bản tóm tắt tự sinh khi hội thoại kết thúc.
        </span>
      )}
    </div>
  )
}

function PhanTomTat({ nhan, noiDung }: { nhan: string; noiDung?: string | null }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-muted-foreground text-xs">{nhan}</span>
      <span className="text-[13px] whitespace-pre-line">{noiDung || '—'}</span>
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
