import { format } from 'date-fns'
import { Bot, FileText, LifeBuoy, TriangleAlert, Zap } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useDanhSachLuotXuLyQuery, type BoLocLuotXuLy } from '@/api/ai-agent'
import { useAppSelector } from '@/app/store/hooks'
import { DanhSachDanhGia, NutDanhGia } from '@/components/ai/DanhGiaDialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Pagination } from '@/components/ui/pagination'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import {
  NHAN_LY_DO_TU_CHOI,
  NHAN_NHANH_XU_LY,
  doTre,
  phanTram,
  tienVnd,
} from '@/features/ai-agent/nhan'
import { cn } from '@/utils/cn'
import type { LuotXuLyAi } from '@/types/schema'

/** Bốn chặng của một lượt xử lý, cùng thứ tự và cùng màu ở mọi chỗ hiển thị độ trễ. */
const CHANG = [
  { khoa: 'retrieve', nhan: 'Truy hồi', mau: 'var(--chart-1)' },
  { khoa: 'rerank', nhan: 'Xếp hạng lại', mau: 'var(--chart-2)' },
  { khoa: 'generate', nhan: 'Sinh câu trả lời', mau: 'var(--chart-3)' },
  { khoa: 'tool', nhan: 'Gọi công cụ', mau: 'var(--chart-4)' },
] as const

/**
 * Mốc tô màu độ bám nguồn — CHỈ để đọc nhanh, không phải cổng huỷ. Cổng huỷ thật ở ai-service
 * (`RAG_NGUONG_BAM_NGUON`) đang TẮT (0) theo ADR-0029: điểm là phép đo từ vựng, chấm oan câu diễn đạt
 * lại. Câu bị huỷ thật thì có `discardedAnswer`; câu điểm thấp mà không có trường đó là câu khách ĐÃ
 * nhận. Bản trước ghi "ngưỡng 0.7" và tô đỏ — đọc như thể câu đã bị huỷ (sửa ở GD2).
 */
const MOC_BAM_NGUON_TOT = 0.7

/**
 * SCR036 — giám sát lượt xử lý của tác tử AI. Màn chữ ký.
 *
 * Ba thứ màn này phải nói rõ, nếu không người xem hiểu ngược:
 *
 * 1. **`discardedAnswer` là câu chưa từng gửi đi.** Nó bị huỷ vì dưới ngưỡng bám nguồn. Hiển thị
 *    nó như một tin nhắn bình thường là làm người trực tưởng khách đã đọc câu đó rồi.
 * 2. **`cached` nghĩa là không tốn lượt gọi mô hình.** Chi phí 0 đồng ở đây không phải lỗi số liệu.
 * 3. **Độ trễ tách theo chặng.** Một lượt 5,6 giây có thể do máy chủ MCP treo chứ không phải mô
 *    hình chậm — gộp thành một con số thì không sửa được gì.
 *
 * GD2: nút "Chưa ổn" mở `DanhGiaDialog` (bắt chọn 1/4 lý do, nhận xét, câu trả lời đúng) thay cho
 * `WRONG_INFO` gắn cứng; lọc "Bị chê" là danh sách của UC027 bước 8; mỗi lượt hiện đủ đánh giá của
 * khách và của từng nhân viên.
 */
export function AiInteractionsPage() {
  const [boLoc, datBoLoc] = useState<BoLocLuotXuLy>({ trang: 0 })
  const truyVan = useDanhSachLuotXuLyQuery(boLoc)
  const muc = truyVan.data?.items ?? []

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 flex-col gap-0.5 px-4 pt-4 pb-3">
        <h1 className="text-xl font-semibold tracking-tight">Giám sát lượt xử lý của tác tử AI</h1>
        <p className="text-muted-foreground text-[13px]">
          Mỗi lượt là một lần tác tử đọc tin của khách và quyết định làm gì — kèm căn cứ, chi phí và
          chặng gây chậm.
        </p>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-4 pb-3">
        <Select
          value={boLoc.nhanh ?? 'tat-ca'}
          onValueChange={(v) =>
            datBoLoc((cu) => ({
              ...cu,
              trang: 0,
              nhanh: v === 'tat-ca' ? undefined : (v as BoLocLuotXuLy['nhanh']),
            }))
          }
        >
          <SelectTrigger size="sm" className="w-auto min-w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tat-ca">Nhánh xử lý: tất cả</SelectItem>
            {Object.entries(NHAN_NHANH_XU_LY).map(([giaTri, v]) => (
              <SelectItem key={giaTri} value={giaTri}>
                {v.nhan}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={boLoc.daTuChoi === undefined ? 'tat-ca' : String(boLoc.daTuChoi)}
          onValueChange={(v) =>
            datBoLoc((cu) => ({
              ...cu,
              trang: 0,
              daTuChoi: v === 'tat-ca' ? undefined : v === 'true',
            }))
          }
        >
          <SelectTrigger size="sm" className="w-auto min-w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tat-ca">Kết quả: tất cả</SelectItem>
            <SelectItem value="true">Chỉ lượt từ chối</SelectItem>
            <SelectItem value="false">Chỉ lượt trả lời được</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={boLoc.danhGia ?? 'tat-ca'}
          onValueChange={(v) =>
            datBoLoc((cu) => ({
              ...cu,
              trang: 0,
              danhGia: v === 'tat-ca' ? undefined : (v as BoLocLuotXuLy['danhGia']),
            }))
          }
        >
          <SelectTrigger size="sm" className="w-auto min-w-40" aria-label="Lọc theo đánh giá">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tat-ca">Đánh giá: tất cả</SelectItem>
            <SelectItem value="NEGATIVE">Bị chê</SelectItem>
            <SelectItem value="POSITIVE">Được khen</SelectItem>
          </SelectContent>
        </Select>

        {(boLoc.nhanh || boLoc.daTuChoi !== undefined || boLoc.danhGia) && (
          <Button variant="ghost" size="sm" onClick={() => datBoLoc({ trang: 0 })}>
            Gỡ bộ lọc
          </Button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="flex flex-col gap-2.5 p-4">
          {truyVan.isLoading &&
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full rounded-lg" />
            ))}

          {!truyVan.isLoading && muc.length === 0 && (
            <EmptyState
              BieuTuong={Bot}
              tieuDe="Chưa có lượt xử lý nào"
              moTa="Lượt xử lý được ghi lại mỗi khi tác tử AI đọc một tin nhắn của khách."
            />
          )}

          {muc.map((l) => (
            <TheLuotXuLy key={l.id} luot={l} />
          ))}
        </div>
      </div>

      {truyVan.data && (
        <Pagination
          trang={truyVan.data.page}
          tongSoTrang={truyVan.data.totalPages}
          tongSoMuc={truyVan.data.totalItems}
          coTrang={truyVan.data.size}
          onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
        />
      )}
    </div>
  )
}

function TheLuotXuLy({ luot }: { luot: LuotXuLyAi }) {
  const toi = useAppSelector((s) => s.auth.nguoiDung?.id)
  const nhanh = NHAN_NHANH_XU_LY[luot.route]
  const danhGia = luot.feedbacks ?? (luot.feedback ? [luot.feedback] : [])
  const cuaToi =
    danhGia.find((d) => d.ratedByType === 'AGENT' && d.ratedByUserId === toi) ?? null
  const tongChang = CHANG.reduce((t, c) => t + (luot.latencyBreakdown?.[c.khoa] ?? 0), 0)

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex min-w-0 flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip sacThai={nhanh.sacThai}>{nhanh.nhan}</StatusChip>
              {luot.intentLabel && (
                <span className="font-mono text-xs">
                  {luot.intentLabel}
                  {luot.intentConfidence != null && (
                    <span className="text-muted-foreground">
                      {' '}
                      ({phanTram(luot.intentConfidence, 0)})
                    </span>
                  )}
                </span>
              )}
              {luot.cached && (
                <StatusChip sacThai="info" BieuTuong={Zap}>
                  Dùng đệm ngữ nghĩa
                </StatusChip>
              )}
              {luot.refused && <StatusChip sacThai="warning">Đã từ chối</StatusChip>}
              {luot.degraded && (
                <StatusChip sacThai="warning" BieuTuong={LifeBuoy}>
                  Trả lời tạm
                </StatusChip>
              )}
              {luot.handoff && <StatusChip sacThai="info">Đề nghị chuyển nhân viên</StatusChip>}
              {luot.errorCode && (
                <StatusChip sacThai="destructive">{luot.errorCode}</StatusChip>
              )}
            </div>
            <span className="text-muted-foreground text-xs tabular-nums">
              {format(new Date(luot.createdAt), 'HH:mm:ss dd/MM/yyyy')} ·{' '}
              {luot.modelName ?? 'không rõ mô hình'}
              {luot.modelVersion && ` ${luot.modelVersion}`} ·{' '}
              {(luot.promptTokens + luot.completionTokens).toLocaleString('vi-VN')} token ·{' '}
              {luot.cached ? 'không tốn lượt gọi mô hình' : tienVnd(luot.costVnd)}
            </span>
          </div>

          <Link
            to={`/hop-thu?c=${luot.conversationId}`}
            className="text-muted-foreground hover:text-foreground shrink-0 text-xs underline-offset-2 transition-colors hover:underline"
          >
            Mở hội thoại
          </Link>
        </div>

        {(luot.userQuery || luot.answerText) && (
          <div className="flex flex-col gap-1 text-[13px] leading-relaxed">
            {luot.userQuery && (
              <p>
                <span className="text-muted-foreground">Khách hỏi: </span>
                {luot.userQuery}
              </p>
            )}
            {luot.answerText && (
              <p className="line-clamp-4">
                <span className="text-muted-foreground">Tác tử trả lời: </span>
                {luot.answerText}
              </p>
            )}
          </div>
        )}

        {tongChang > 0 && <ThanhDoTre luot={luot} tong={tongChang} />}

        {luot.retrievalTopScore != null && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-muted-foreground">Điểm truy hồi cao nhất</span>
            <span className="font-medium tabular-nums">{luot.retrievalTopScore.toFixed(2)}</span>
            <span className="text-muted-foreground">
              — độ liên quan của đoạn với câu hỏi, đo trước khi sinh
            </span>
          </div>
        )}

        {luot.groundednessScore != null && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Độ bám nguồn</span>
            <StatusChip
              sacThai={luot.groundednessScore >= MOC_BAM_NGUON_TOT ? 'success' : 'warning'}
            >
              {luot.groundednessScore.toFixed(2)}
            </StatusChip>
            <span className="text-muted-foreground">
              theo dõi, không huỷ câu trả lời — cổng huỷ đang tắt (ADR-0029)
            </span>
          </div>
        )}

        {luot.refusalReason && (
          <div className="bg-warning/10 text-warning rounded-md px-2.5 py-1.5 text-xs">
            Từ chối trả lời: {NHAN_LY_DO_TU_CHOI[luot.refusalReason]}
          </div>
        )}

        {luot.discardedAnswer && (
          <div className="border-destructive/40 bg-destructive/6 flex flex-col gap-1 rounded-md border px-2.5 py-2">
            <span className="text-destructive flex items-center gap-1.5 text-xs font-medium">
              <TriangleAlert className="size-3.5" />
              Câu trả lời bị huỷ — khách chưa từng nhận được câu này
            </span>
            <p className="text-muted-foreground text-xs leading-relaxed">{luot.discardedAnswer}</p>
          </div>
        )}

        {(luot.citations?.length ?? 0) > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-muted-foreground text-xs">Căn cứ đã trích dẫn</span>
            {luot.citations?.map((t) => (
              <Link
                key={t.chunkId}
                to={`/tri-thuc/tai-lieu/${t.documentId}`}
                className="hover:bg-muted/50 flex min-w-0 items-start gap-2 rounded-md px-2 py-1.5 transition-colors"
              >
                <FileText className="text-muted-foreground mt-0.5 size-3.5 shrink-0" />
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-xs font-medium">{t.documentTitle}</span>
                  {t.snippet && (
                    <span className="text-muted-foreground line-clamp-2 text-xs">{t.snippet}</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}

        {(luot.toolCalls?.length ?? 0) > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted-foreground text-xs">Công cụ đã gọi</span>
            {luot.toolCalls?.map((g) => (
              <span key={g.id} className="flex items-center gap-1.5">
                <span className="font-mono text-xs">{g.toolName}</span>
                <StatusChip
                  sacThai={
                    g.guardResult === 'ALLOWED'
                      ? 'success'
                      : g.guardResult === 'BLOCKED'
                        ? 'destructive'
                        : 'warning'
                  }
                >
                  {g.guardResult === 'ALLOWED'
                    ? 'Cho phép'
                    : g.guardResult === 'BLOCKED'
                      ? 'Bị chặn'
                      : 'Chờ duyệt'}
                </StatusChip>
              </span>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-2 border-t pt-2.5">
          <DanhSachDanhGia danhGia={danhGia} />
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted-foreground text-xs">
              {cuaToi ? 'Bạn đã đánh giá — bấm lại để sửa:' : 'Câu trả lời này ổn không?'}
            </span>
            <NutDanhGia luotId={luot.id} cauTraLoi={luot.answerText} cuaToi={cuaToi} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Độ trễ tách theo chặng.
 *
 * Có nhãn chữ kèm màu, không chỉ có màu: ba màu chuỗi dữ liệu của bộ token nằm dưới 3:1 trên nền
 * trắng, nên màu một mình không đủ để phân biệt (`docs/design/tokens.md`).
 */
function ThanhDoTre({ luot, tong }: { luot: LuotXuLyAi; tong: number }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-muted-foreground">Độ trễ theo chặng</span>
        <span className="font-medium tabular-nums">{doTre(luot.latencyMs ?? tong)}</span>
      </div>
      <div className="bg-muted flex h-1.5 w-full overflow-hidden rounded-full">
        {CHANG.map((c) => {
          const v = luot.latencyBreakdown?.[c.khoa] ?? 0
          if (v === 0) return null
          return (
            <span
              key={c.khoa}
              style={{ width: `${(v / tong) * 100}%`, backgroundColor: c.mau }}
              className={cn('h-full')}
            />
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        {CHANG.map((c) => {
          const v = luot.latencyBreakdown?.[c.khoa] ?? 0
          if (v === 0) return null
          return (
            <span key={c.khoa} className="text-muted-foreground flex items-center gap-1 text-xs">
              <span className="size-2 rounded-full" style={{ backgroundColor: c.mau }} />
              {c.nhan} <span className="tabular-nums">{doTre(v)}</span>
            </span>
          )
        })}
      </div>
    </div>
  )
}
