import { format } from 'date-fns'
import { Ban, ShieldCheck, ShieldQuestion, Terminal } from 'lucide-react'
import { useState } from 'react'

import { useDanhSachGoiCongCuQuery, type BoLocGoiCongCu } from '@/api/ai-agent'
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
import { ApproveToolCallDialog } from '@/features/ai-agent/ApproveToolCallDialog'
import {
  NHAN_KET_QUA_GOI,
  NHAN_KET_QUA_KIEM_DUYET,
  NHAN_LY_DO_CHAN,
  NHAN_TRANG_THAI_DUYET,
  doTre,
} from '@/features/ai-agent/nhan'
import { cn } from '@/utils/cn'
import type { NhatKyGoiCongCu } from '@/types/schema'

/**
 * SCR035 — nhật ký gọi công cụ. Màn chữ ký.
 *
 * Không dựng trên mẫu M1 vì bảng sai với dữ liệu này: giá trị của một dòng nằm ở **tham số của
 * lời gọi**, mà tham số là JSON dài ngắn khác nhau — nhét vào một ô bảng thì hoặc cắt cụt hoặc
 * phá vỡ chiều cao dòng. Mỗi lời gọi vì vậy là một thẻ.
 *
 * Lời gọi **chờ duyệt** nổi lên trên cùng thay vì nằm lẫn theo thứ tự thời gian: tác tử AI đang
 * dừng lại chờ, và mỗi phút không ai bấm là một phút khách ngồi nhìn màn hình im lặng.
 */
export function ToolCallLogPage() {
  const [boLoc, datBoLoc] = useState<BoLocGoiCongCu>({ trang: 0 })
  const [dangDuyet, datDangDuyet] = useState<NhatKyGoiCongCu | null>(null)

  const truyVan = useDanhSachGoiCongCuQuery(boLoc)
  const choDuyet = useDanhSachGoiCongCuQuery({ trangThaiDuyet: 'PENDING' })
  const soChoDuyet = choDuyet.data?.totalItems ?? 0

  const muc = truyVan.data?.items ?? []

  return (
    <>
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex shrink-0 flex-col gap-3 px-4 pt-4 pb-3">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight">Nhật ký gọi công cụ</h1>
            <p className="text-muted-foreground text-[13px]">
              Mọi lời gọi công cụ của tác tử AI, kể cả những lời gọi bị chặn trước khi ra khỏi tiến
              trình. Đây là bằng chứng kiểm toán của bề mặt T4.
            </p>
          </div>

          {soChoDuyet > 0 && (
            <Card className="border-warning/40 bg-warning/6">
              <CardContent className="flex flex-wrap items-center gap-3">
                <ShieldQuestion className="text-warning size-5 shrink-0" />
                <div className="flex min-w-0 flex-1 flex-col">
                  <span className="text-[13px] font-medium">
                    {soChoDuyet} lời gọi đang chờ người duyệt
                  </span>
                  <span className="text-muted-foreground text-xs">
                    Tác tử AI dừng lại cho tới khi có quyết định — khách đang chờ ở đầu bên kia.
                  </span>
                </div>
                <Button
                  size="sm"
                  variant={boLoc.trangThaiDuyet === 'PENDING' ? 'outline' : 'default'}
                  onClick={() =>
                    datBoLoc((cu) => ({
                      ...cu,
                      trang: 0,
                      trangThaiDuyet: cu.trangThaiDuyet === 'PENDING' ? undefined : 'PENDING',
                    }))
                  }
                >
                  {boLoc.trangThaiDuyet === 'PENDING' ? 'Bỏ lọc' : 'Chỉ xem việc chờ duyệt'}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-4 pb-3">
          <Select
            value={boLoc.ketQuaKiemDuyet ?? 'tat-ca'}
            onValueChange={(v) =>
              datBoLoc((cu) => ({
                ...cu,
                trang: 0,
                ketQuaKiemDuyet: v === 'tat-ca' ? undefined : (v as BoLocGoiCongCu['ketQuaKiemDuyet']),
              }))
            }
          >
            <SelectTrigger size="sm" className="w-auto min-w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tat-ca">Kiểm duyệt: tất cả</SelectItem>
              {Object.entries(NHAN_KET_QUA_KIEM_DUYET).map(([giaTri, v]) => (
                <SelectItem key={giaTri} value={giaTri}>
                  {v.nhan}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={boLoc.trangThaiDuyet ?? 'tat-ca'}
            onValueChange={(v) =>
              datBoLoc((cu) => ({
                ...cu,
                trang: 0,
                trangThaiDuyet: v === 'tat-ca' ? undefined : (v as BoLocGoiCongCu['trangThaiDuyet']),
              }))
            }
          >
            <SelectTrigger size="sm" className="w-auto min-w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tat-ca">Phê duyệt: tất cả</SelectItem>
              {Object.entries(NHAN_TRANG_THAI_DUYET).map(([giaTri, v]) => (
                <SelectItem key={giaTri} value={giaTri}>
                  {v.nhan}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {(boLoc.ketQuaKiemDuyet || boLoc.trangThaiDuyet) && (
            <Button variant="ghost" size="sm" onClick={() => datBoLoc({ trang: 0 })}>
              Gỡ bộ lọc
            </Button>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="flex flex-col gap-2.5 p-4">
            {truyVan.isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-28 w-full rounded-lg" />
              ))}

            {!truyVan.isLoading && muc.length === 0 && (
              <EmptyState
                BieuTuong={Terminal}
                tieuDe="Chưa có lời gọi công cụ nào"
                moTa="Tác tử AI chỉ gọi công cụ khi câu hỏi cần dữ liệu nghiệp vụ theo thời gian thực."
              />
            )}

            {muc.map((g) => (
              <TheLoiGoi key={g.id} loiGoi={g} onDuyet={() => datDangDuyet(g)} />
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

      <ApproveToolCallDialog loiGoi={dangDuyet} onDong={() => datDangDuyet(null)} />
    </>
  )
}

function TheLoiGoi({ loiGoi, onDuyet }: { loiGoi: NhatKyGoiCongCu; onDuyet: () => void }) {
  const kd = NHAN_KET_QUA_KIEM_DUYET[loiGoi.guardResult]
  const choDuyet = loiGoi.approvalStatus === 'PENDING'
  const thamSo = Object.entries(loiGoi.arguments ?? {})

  return (
    <Card className={cn(choDuyet && 'border-warning/50')}>
      <CardContent className="flex flex-col gap-2.5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex min-w-0 flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[13px] font-medium">{loiGoi.toolName}</span>
              <StatusChip
                sacThai={kd.sacThai}
                BieuTuong={loiGoi.guardResult === 'BLOCKED' ? Ban : ShieldCheck}
              >
                {kd.nhan}
              </StatusChip>
              {loiGoi.approvalStatus && (
                <StatusChip sacThai={NHAN_TRANG_THAI_DUYET[loiGoi.approvalStatus].sacThai}>
                  {NHAN_TRANG_THAI_DUYET[loiGoi.approvalStatus].nhan}
                </StatusChip>
              )}
              {loiGoi.resultStatus && (
                <StatusChip sacThai={NHAN_KET_QUA_GOI[loiGoi.resultStatus].sacThai}>
                  {NHAN_KET_QUA_GOI[loiGoi.resultStatus].nhan}
                </StatusChip>
              )}
            </div>
            <span className="text-muted-foreground text-xs tabular-nums">
              {loiGoi.contactName ?? 'Không rõ khách'} ·{' '}
              {format(new Date(loiGoi.calledAt), 'HH:mm:ss dd/MM/yyyy')} · kiểm duyệt{' '}
              {doTre(loiGoi.guardLatencyMs)}
              {loiGoi.latencyMs != null && ` · gọi ${doTre(loiGoi.latencyMs)}`}
            </span>
          </div>

          {choDuyet && (
            <Button size="sm" onClick={onDuyet}>
              Xem và duyệt
            </Button>
          )}
        </div>

        {loiGoi.blockedReason && (
          <div className="bg-destructive/8 text-destructive rounded-md px-2.5 py-1.5 text-xs">
            Bị chặn: {NHAN_LY_DO_CHAN[loiGoi.blockedReason]}
          </div>
        )}

        {thamSo.length > 0 && (
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {thamSo.slice(0, 3).map(([khoa, giaTri]) => (
              <span key={khoa} className="min-w-0 text-xs">
                <span className="text-muted-foreground font-mono">{khoa}: </span>
                <span className="font-mono">
                  {typeof giaTri === 'string' ? giaTri : JSON.stringify(giaTri)}
                </span>
              </span>
            ))}
            {thamSo.length > 3 && (
              <span className="text-muted-foreground text-xs">
                và {thamSo.length - 3} tham số nữa
              </span>
            )}
          </div>
        )}

        {/* Kết quả công cụ hiển thị như **dữ liệu**, không phải chỉ thị — nền riêng, chữ đơn sắc */}
        {loiGoi.resultSummary && (
          <p className="bg-muted text-muted-foreground rounded-md px-2.5 py-1.5 text-xs leading-relaxed">
            {loiGoi.resultSummary}
          </p>
        )}

        {loiGoi.approvedByName && (
          <span className="text-muted-foreground text-xs">
            {loiGoi.approvalStatus === 'APPROVED' ? 'Duyệt bởi' : 'Từ chối bởi'}{' '}
            {loiGoi.approvedByName}
            {loiGoi.approvedAt && ` lúc ${format(new Date(loiGoi.approvedAt), 'HH:mm dd/MM')}`}
          </span>
        )}
      </CardContent>
    </Card>
  )
}
