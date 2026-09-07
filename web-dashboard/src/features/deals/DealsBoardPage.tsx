import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { format } from 'date-fns'
import { CalendarClock, Plus, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import {
  useDanhSachDealQuery,
  useDanhSachPheuQuery,
  useKeoDealSangGiaiDoanMutation,
} from '@/api/sales'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { CreateDealDialog } from '@/features/deals/CreateDealDialog'
import { tienGon } from '@/features/leads/nhan'
import type { Deal, GiaiDoanPheu } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * SCR044 — cơ hội bán hàng xếp theo phễu. Màn chữ ký.
 *
 * Kéo thả bằng `@dnd-kit`. Hai điều quyết định màn này dùng được hay không:
 *
 * 1. **Kéo hỏng phải bật lại đúng chỗ cũ.** Giai đoạn từ "Đã báo giá" trở đi bắt buộc có số tiền;
 *    máy chủ từ chối thì thẻ phải quay về cột cũ kèm lý do, chứ không nằm lại chỗ mới và để người
 *    dùng tưởng đã lưu.
 * 2. **Tổng tiền mỗi cột nằm ngay trên đầu cột.** Kanban không có tổng thì nó chỉ là một danh
 *    sách nhiều cột — giá trị của phễu là thấy tiền đang đọng ở giai đoạn nào.
 */
export function DealsBoardPage() {
  const dieuHuong = useNavigate()
  const [moTao, datMoTao] = useState(false)
  const [dangKeo, datDangKeo] = useState<Deal | null>(null)

  const pheu = useDanhSachPheuQuery()
  const deal = useDanhSachDealQuery({ pheuId: pheu.data?.[0]?.id, trangThai: undefined })
  const [keo, ketQuaKeo] = useKeoDealSangGiaiDoanMutation()

  // Ngưỡng 6px: bấm để mở chi tiết và kéo để đổi giai đoạn dùng chung một cử chỉ chuột, không
  // tách ngưỡng thì mọi cú bấm đều bị hiểu thành kéo.
  const camBien = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  const giaiDoan = pheu.data?.[0]?.stages ?? []
  const theoGiaiDoan = useMemo(() => {
    const m = new Map<string, Deal[]>()
    for (const g of giaiDoan) m.set(g.id, [])
    for (const d of deal.data?.items ?? []) m.get(d.stageId)?.push(d)
    return m
  }, [giaiDoan, deal.data])

  async function khiTha(su: DragEndEvent) {
    datDangKeo(null)
    const idDeal = String(su.active.id)
    const idGiaiDoanMoi = su.over ? String(su.over.id) : null
    const d = deal.data?.items.find((x) => x.id === idDeal)
    if (!d || !idGiaiDoanMoi || d.stageId === idGiaiDoanMoi) return

    try {
      await keo({ id: idDeal, stageId: idGiaiDoanMoi }).unwrap()
      const ten = giaiDoan.find((g) => g.id === idGiaiDoanMoi)?.name
      toast.success(`Đã chuyển sang "${ten}".`)
    } catch (loi) {
      // Máy chủ từ chối → cache không đổi → thẻ tự về chỗ cũ. Nói rõ vì sao, đừng để im lặng.
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không chuyển được giai đoạn.')
    }
  }

  return (
    <>
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex shrink-0 flex-wrap items-start justify-between gap-3 px-4 pt-4 pb-3">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight">Phễu bán hàng</h1>
            <p className="text-muted-foreground text-[13px]">
              Kéo thẻ để đổi giai đoạn. Tổng tiền mỗi cột cập nhật ngay theo.
            </p>
          </div>
          <Button size="sm" onClick={() => datMoTao(true)}>
            <Plus />
            Tạo cơ hội
          </Button>
        </div>

        {laLoiTruyVan(ketQuaKeo.error) && (
          <div className="shrink-0 px-4 pb-3">
            <Alert variant="destructive">
              <TriangleAlert />
              <AlertDescription>{ketQuaKeo.error.message}</AlertDescription>
            </Alert>
          </div>
        )}

        {pheu.isLoading || deal.isLoading ? (
          <div className="flex gap-3 overflow-x-auto p-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-72 w-64 shrink-0" />
            ))}
          </div>
        ) : (
          <DndContext
            sensors={camBien}
            onDragStart={(su: DragStartEvent) =>
              datDangKeo(deal.data?.items.find((d) => d.id === String(su.active.id)) ?? null)
            }
            onDragEnd={khiTha}
            onDragCancel={() => datDangKeo(null)}
          >
            <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto p-4">
              {giaiDoan.map((g) => (
                <CotGiaiDoan
                  key={g.id}
                  giaiDoan={g}
                  deal={theoGiaiDoan.get(g.id) ?? []}
                  onMoDeal={(id) => dieuHuong(`/ban-hang/pheu/${id}`)}
                />
              ))}
            </div>

            {/* Lớp phủ khi kéo: thẻ gốc mờ đi, bản sao đi theo con trỏ — nếu không thì thẻ nhảy
                giật khỏi cột và người dùng mất dấu nó đang ở đâu. */}
            <DragOverlay>{dangKeo && <TheDeal deal={dangKeo} dangKeo />}</DragOverlay>
          </DndContext>
        )}
      </div>

      <CreateDealDialog mo={moTao} onDoiMo={datMoTao} />
    </>
  )
}

function CotGiaiDoan({
  giaiDoan,
  deal,
  onMoDeal,
}: {
  giaiDoan: GiaiDoanPheu
  deal: Deal[]
  onMoDeal: (id: string) => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: giaiDoan.id })
  const tong = deal.reduce((t, d) => t + (d.amount ?? 0), 0)

  return (
    <div
      ref={setNodeRef}
      data-giai-doan={giaiDoan.id}
      className={cn(
        'bg-muted/40 flex w-64 shrink-0 flex-col gap-2 rounded-lg border p-2 transition-colors',
        isOver && 'border-primary bg-primary/5',
      )}
    >
      <div className="flex flex-col gap-0.5 px-1">
        <div className="flex items-center gap-2">
          <span className="flex-1 text-[13px] font-medium">{giaiDoan.name}</span>
          <span className="text-muted-foreground text-xs tabular-nums">{deal.length}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold tabular-nums">{tienGon(tong)}</span>
          {giaiDoan.probability != null && !giaiDoan.isWon && !giaiDoan.isLost && (
            <span className="text-muted-foreground text-xs">~{giaiDoan.probability}% chốt</span>
          )}
        </div>
      </div>

      <div className="flex min-h-24 flex-col gap-1.5">
        {deal.length === 0 ? (
          <span className="text-muted-foreground px-1 py-4 text-center text-xs">
            Chưa có cơ hội nào
          </span>
        ) : (
          deal.map((d) => <TheDealKeoDuoc key={d.id} deal={d} onMo={() => onMoDeal(d.id)} />)
        )}
      </div>
    </div>
  )
}

function TheDealKeoDuoc({ deal, onMo }: { deal: Deal; onMo: () => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: deal.id })
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={onMo}
      className={cn('cursor-grab', isDragging && 'opacity-40')}
    >
      <TheDeal deal={deal} />
    </div>
  )
}

function TheDeal({ deal, dangKeo }: { deal: Deal; dangKeo?: boolean }) {
  return (
    <div
      className={cn(
        'bg-background flex flex-col gap-1.5 rounded-lg border p-2.5',
        dangKeo && 'shadow-lg',
      )}
    >
      <span className="line-clamp-2 text-[13px] font-medium">{deal.title}</span>
      <span className="text-muted-foreground truncate text-xs">{deal.contactName}</span>
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-sm font-semibold tabular-nums">{tienGon(deal.amount)}</span>
        {/* Quá hạn chốt mà vẫn mở — thứ duy nhất trên thẻ cần màu cảnh báo */}
        {deal.isOverdue && (
          <StatusChip sacThai="destructive" BieuTuong={CalendarClock}>
            Quá hạn
          </StatusChip>
        )}
        {deal.amount == null && <StatusChip sacThai="warning">Chưa có giá</StatusChip>}
      </div>
      {deal.expectedCloseDate && (
        <span className="text-muted-foreground text-xs tabular-nums">
          Dự kiến {format(new Date(deal.expectedCloseDate), 'dd/MM')}
          {deal.ownerName && ` · ${deal.ownerName}`}
        </span>
      )}
    </div>
  )
}
