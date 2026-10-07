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
import { CalendarClock, Lock, Plus, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import {
  useDanhSachDealQuery,
  useDanhSachPheuQuery,
  useKeoDealSangGiaiDoanMutation,
} from '@/api/sales'
import { useAppSelector } from '@/app/store/hooks'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { CreateDealDialog } from '@/features/deals/CreateDealDialog'
import { LyDoThuaDialog, SuaDealDialog } from '@/features/deals/DealDialogs'
import { tienGon } from '@/features/leads/nhan'
import type { Deal, GiaiDoanPheu, LyDoThuaDeal } from '@/types/schema'
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
 *
 * Luật UC034 đã chốt (máy chủ quyết, màn này chỉ dẫn người dùng qua):
 * - Thả vào cột "Thua" → hỏi lý do trong danh sách cố định rồi mới gửi.
 * - Máy chủ trả 422 `MISSING_REQUIRED_FIELDS` → mở hộp bổ sung đúng trường thiếu, lưu xong kéo lại.
 * - Deal của người khác (nhân viên thường) có ổ khoá, không kéo được — máy chủ cũng chặn.
 */
export function DealsBoardPage() {
  const dieuHuong = useNavigate()
  const [moTao, datMoTao] = useState(false)
  const [dangKeo, datDangKeo] = useState<Deal | null>(null)
  /** Lần kéo đang chờ người dùng bổ sung: lý do thua hoặc trường bắt buộc. */
  const [choThua, datChoThua] = useState<{ deal: Deal; stageId: string } | null>(null)
  const [choBoSung, datChoBoSung] = useState<{ deal: Deal; stageId: string; lyDo: string } | null>(null)
  const toi = useAppSelector((s) => s.auth.nguoiDung)
  const laQuanTri = toi?.roleCode === 'TENANT_ADMIN'
  const keoDuoc = (d: Deal) => laQuanTri || !d.ownerUserId || d.ownerUserId === toi?.id

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
    if (giaiDoan.find((g) => g.id === idGiaiDoanMoi)?.isLost) {
      datChoThua({ deal: d, stageId: idGiaiDoanMoi })
      return
    }
    await guiKeo(d, idGiaiDoanMoi)
  }

  async function guiKeo(d: Deal, stageId: string, closeReason?: LyDoThuaDeal) {
    const ten = giaiDoan.find((g) => g.id === stageId)?.name
    try {
      await keo({ id: d.id, stageId, closeReason: closeReason ?? null }).unwrap()
      toast.success(`Đã chuyển sang "${ten}".`)
      return true
    } catch (loi) {
      // Thiếu trường bắt buộc → mở đúng ô cần nhập thay vì chỉ báo lỗi (UC034 luồng 5.1)
      if (laLoiTruyVan(loi) && loi.code === 'MISSING_REQUIRED_FIELDS') {
        datChoBoSung({ deal: d, stageId, lyDo: loi.message })
        return false
      }
      // Máy chủ từ chối → cache không đổi → thẻ tự về chỗ cũ. Nói rõ vì sao, đừng để im lặng.
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không chuyển được giai đoạn.')
      return false
    }
  }

  return (
    <>
      {/* min-w-0: không có thì 5 cột đẩy rộng cả trang, kéo thẻ làm trang trượt ngang dưới thanh bên */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="flex shrink-0 flex-wrap items-start justify-between gap-3 px-4 pt-4 pb-3">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight">Phễu bán hàng</h1>
            <p className="text-muted-foreground text-[13px]">
              Kéo thẻ để đổi giai đoạn. Tổng tiền mỗi cột cập nhật ngay theo.
            </p>
          </div>
          <Button size="sm" onClick={() => datMoTao(true)}>
            <Plus />
            Tạo deal
          </Button>
        </div>

        {laLoiTruyVan(ketQuaKeo.error) && ketQuaKeo.error.code !== 'MISSING_REQUIRED_FIELDS' && (
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
                  keoDuoc={keoDuoc}
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

      <LyDoThuaDialog
        mo={!!choThua}
        onDoiMo={(m) => !m && datChoThua(null)}
        dangGui={ketQuaKeo.isLoading}
        onChon={async (lyDo) => {
          if (!choThua) return
          if (await guiKeo(choThua.deal, choThua.stageId, lyDo)) datChoThua(null)
        }}
      />

      {choBoSung && (
        <SuaDealDialog
          deal={choBoSung.deal}
          mo
          onDoiMo={(m) => !m && datChoBoSung(null)}
          lyDo={choBoSung.lyDo}
          onDaLuu={() => {
            const { deal: d, stageId } = choBoSung
            datChoBoSung(null)
            void guiKeo(d, stageId)
          }}
        />
      )}
    </>
  )
}

function CotGiaiDoan({
  giaiDoan,
  deal,
  keoDuoc,
  onMoDeal,
}: {
  giaiDoan: GiaiDoanPheu
  deal: Deal[]
  keoDuoc: (d: Deal) => boolean
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
        giaiDoan.isWon && 'bg-success/5',
        giaiDoan.isLost && 'bg-destructive/5',
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
            Chưa có deal nào
          </span>
        ) : (
          deal.map((d) => (
            <TheDealKeoDuoc key={d.id} deal={d} khoa={!keoDuoc(d)} onMo={() => onMoDeal(d.id)} />
          ))
        )}
      </div>
    </div>
  )
}

function TheDealKeoDuoc({ deal, khoa, onMo }: { deal: Deal; khoa: boolean; onMo: () => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: deal.id, disabled: khoa })
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={onMo}
      title={khoa ? `Deal do ${deal.ownerName ?? 'người khác'} phụ trách — chỉ xem` : undefined}
      className={cn(khoa ? 'cursor-pointer' : 'cursor-grab', isDragging && 'opacity-40')}
    >
      <TheDeal deal={deal} khoa={khoa} />
    </div>
  )
}

function TheDeal({ deal, dangKeo, khoa }: { deal: Deal; dangKeo?: boolean; khoa?: boolean }) {
  return (
    <div
      className={cn(
        'bg-background flex flex-col gap-1.5 rounded-lg border p-2.5',
        dangKeo && 'shadow-lg',
      )}
    >
      <span className="line-clamp-2 text-[13px] font-medium">
        {khoa && <Lock className="text-muted-foreground mr-1 inline size-3" />}
        {deal.title}
      </span>
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
      <span className="text-muted-foreground text-xs tabular-nums">
        {deal.expectedCloseDate ? `Dự kiến ${format(new Date(deal.expectedCloseDate), 'dd/MM')}` : 'Chưa đặt ngày chốt'}
        {` · ${deal.ownerName ?? 'Chưa ai nhận'}`}
      </span>
    </div>
  )
}
