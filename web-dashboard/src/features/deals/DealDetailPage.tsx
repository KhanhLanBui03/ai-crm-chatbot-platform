import { format, formatDistanceStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { CalendarClock, Hand, Pencil, RotateCcw, Target, TriangleAlert, User, UserCog } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import {
  useCapNhatDealMutation,
  useChiTietDealQuery,
  useDanhSachPheuQuery,
  useKeoDealSangGiaiDoanMutation,
} from '@/api/sales'
import { useAppSelector } from '@/app/store/hooks'
import { DetailPage, HangThongTin } from '@/components/layout/DetailPage'
import type { ThaoTac } from '@/components/layout/ListPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { StatusChip } from '@/components/ui/status-chip'
import { DoiPhuTrachDealDialog, LyDoThuaDialog, SuaDealDialog } from '@/features/deals/DealDialogs'
import { NHAN_LY_DO_THUA, NHAN_TRANG_THAI_DEAL, tien } from '@/features/leads/nhan'
import type { LyDoThuaDeal } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * SCR045 — chi tiết deal (UC034). Màn chữ ký.
 *
 * Tab **Lịch sử giai đoạn** là phần đáng giá nhất: nó cho biết deal mắc kẹt ở đâu và bao lâu. Một
 * deal nằm 21 ngày ở "Đã báo giá" là tín hiệu rõ hơn mọi con số dự báo — và chỉ thấy được khi hiển
 * thị **thời lượng từng chặng** (máy chủ tính sẵn `durationSeconds`).
 *
 * Quyền giống bảng phễu: deal của mình / chưa ai nhận / quản trị viên. Hoạt động (UC035) chưa có API
 * nên tab đó ẩn đi.
 */
export function DealDetailPage() {
  const { id = '' } = useParams()
  const dieuHuong = useNavigate()
  const [tab, datTab] = useState('lich-su')
  const [moSua, datMoSua] = useState(false)
  const [moDoiChu, datMoDoiChu] = useState(false)
  const [choThua, datChoThua] = useState<string | null>(null)
  const [choBoSung, datChoBoSung] = useState<{ stageId: string; lyDo: string } | null>(null)
  const toi = useAppSelector((s) => s.auth.nguoiDung)
  const laQuanTri = toi?.roleCode === 'TENANT_ADMIN'

  const truyVan = useChiTietDealQuery(id)
  const pheu = useDanhSachPheuQuery()
  const [keo, ketQuaKeo] = useKeoDealSangGiaiDoanMutation()
  const [capNhat] = useCapNhatDealMutation()

  const d = truyVan.data
  const giaiDoan = pheu.data?.find((p) => p.id === d?.pipelineId)?.stages ?? []
  const hienTai = giaiDoan.find((g) => g.id === d?.stageId)
  const keTiep = giaiDoan.find((g) => g.position === (hienTai?.position ?? 0) + 1 && !g.isWon && !g.isLost)
  const duocSua = !!d && (laQuanTri || !d.ownerUserId || d.ownerUserId === toi?.id)
  const dangMo = d?.status === 'OPEN'
  // Mở lại: về giai đoạn mở gần nhất trước khi đóng (theo lịch sử), không có thì cột đầu
  const giaiDoanMoLai =
    [...(d?.stageHistory ?? [])].reverse().map((h) => giaiDoan.find((g) => g.id === h.fromStageId))
      .find((g) => g && !g.isWon && !g.isLost) ?? giaiDoan.find((g) => !g.isWon && !g.isLost)

  async function chuyen(stageId: string, closeReason?: LyDoThuaDeal) {
    const ten = giaiDoan.find((g) => g.id === stageId)?.name
    try {
      await keo({ id, stageId, closeReason: closeReason ?? null }).unwrap()
      toast.success(`Đã chuyển sang "${ten}".`)
      return true
    } catch (loi) {
      if (laLoiTruyVan(loi) && loi.code === 'MISSING_REQUIRED_FIELDS') {
        datChoBoSung({ stageId, lyDo: loi.message })
      } else {
        toast.error(laLoiTruyVan(loi) ? loi.message : 'Không chuyển được giai đoạn.')
      }
      return false
    }
  }

  const thaoTac: ThaoTac[] = []
  if (d && duocSua) {
    if (!d.ownerUserId && !laQuanTri) {
      thaoTac.push({
        nhan: 'Nhận deal',
        BieuTuong: Hand,
        onClick: async () => {
          try {
            await capNhat({ id, than: { ownerUserId: toi?.id } }).unwrap()
            toast.success('Bạn đang phụ trách deal này.')
          } catch (loi) {
            toast.error(laLoiTruyVan(loi) ? loi.message : 'Không nhận được deal.')
          }
        },
      })
    }
    if (dangMo) thaoTac.push({ nhan: 'Sửa thông tin', BieuTuong: Pencil, onClick: () => datMoSua(true) })
    if (laQuanTri) thaoTac.push({ nhan: 'Đổi phụ trách', BieuTuong: UserCog, onClick: () => datMoDoiChu(true) })
    if (!dangMo && giaiDoanMoLai) {
      thaoTac.push({
        nhan: `Mở lại (về "${giaiDoanMoLai.name}")`,
        BieuTuong: RotateCcw,
        onClick: () => void chuyen(giaiDoanMoLai.id),
      })
    }
  }

  return (
    <>
      <DetailPage
        quayLai={{ duongDan: '/ban-hang/pheu', nhan: 'Phễu bán hàng' }}
        tieuDe={d?.title ?? 'Deal'}
        phuDe={d ? `${d.contactName} · ${tien(d.amount)}` : undefined}
        dangTai={truyVan.isLoading}
        chip={
          d && (
            <>
              <StatusChip sacThai={NHAN_TRANG_THAI_DEAL[d.status].sacThai}>
                {NHAN_TRANG_THAI_DEAL[d.status].nhan}
              </StatusChip>
              {/* Deal đã đóng thì tên giai đoạn trùng trạng thái (Thắng/Thua) — không lặp lại */}
              {d.status === 'OPEN' && <StatusChip>{d.stageName}</StatusChip>}
              {d.source === 'AI_LEAD' && <StatusChip sacThai="info">Từ lead AI</StatusChip>}
              {d.isOverdue && (
                <StatusChip sacThai="destructive" BieuTuong={CalendarClock}>
                  Quá hạn chốt
                </StatusChip>
              )}
            </>
          )
        }
        thaoTacChinh={
          d && duocSua && dangMo && keTiep
            ? { nhan: `Chuyển sang "${keTiep.name}"`, onClick: () => void chuyen(keTiep.id) }
            : undefined
        }
        thaoTacPhu={thaoTac.length > 0 ? thaoTac : undefined}
        tab={[
          {
            khoa: 'lich-su',
            nhan: 'Lịch sử giai đoạn',
            soLuong: d?.stageHistory?.length,
            noiDung: d && (
              <div className="flex flex-col gap-4">
                {!duocSua && (
                  <Alert>
                    <User />
                    <AlertDescription>
                      Deal do <strong>{d.ownerName ?? 'người khác'}</strong> phụ trách — bạn chỉ xem được.
                    </AlertDescription>
                  </Alert>
                )}

                {dangMo && d.amount == null && (
                  <Alert>
                    <TriangleAlert />
                    <AlertDescription>
                      Deal chưa có giá trị — giai đoạn &quot;Đã báo giá&quot; bắt buộc có số tiền, và mọi báo
                      cáo doanh thu đang bỏ sót deal này.
                    </AlertDescription>
                  </Alert>
                )}

                {d.status === 'LOST' && (
                  <Alert>
                    <AlertDescription>
                      Thua
                      {d.closeReason && (
                        <>
                          {' '}
                          — lý do: <strong>{NHAN_LY_DO_THUA[d.closeReason]}</strong>
                        </>
                      )}
                      {d.closedAt && ` · ${format(new Date(d.closedAt), 'dd/MM/yyyy HH:mm')}`}
                    </AlertDescription>
                  </Alert>
                )}
                {d.status === 'WON' && d.closedAt && (
                  <Alert>
                    <AlertDescription>
                      Thắng · {format(new Date(d.closedAt), 'dd/MM/yyyy HH:mm')}
                    </AlertDescription>
                  </Alert>
                )}

                {(d.stageHistory?.length ?? 0) === 0 ? (
                  <EmptyState BieuTuong={Target} tieuDe="Chưa có lịch sử" moTa="Deal vừa được tạo." />
                ) : (
                  <ol className="flex flex-col">
                    {d.stageHistory?.map((h, i, ds) => (
                      <li key={`${h.toStageId}-${i}`} className="flex gap-3">
                        <div className="flex flex-col items-center">
                          <span
                            className={cn(
                              'size-2.5 shrink-0 rounded-full',
                              i === ds.length - 1 ? 'bg-primary' : 'bg-muted-foreground/40',
                            )}
                          />
                          {i < ds.length - 1 && <span className="bg-border w-px flex-1" />}
                        </div>
                        <div className="flex flex-1 flex-col gap-0.5 pb-5">
                          <span className="text-[13px] font-medium">
                            {h.fromStageName ? `${h.fromStageName} → ${h.toStageName}` : `Tạo deal ở "${h.toStageName}"`}
                          </span>
                          <span className="text-muted-foreground text-xs">
                            {format(new Date(h.changedAt), 'dd/MM/yyyy HH:mm', { locale: vi })}
                            {h.changedByName && ` · ${h.changedByName}`}
                          </span>
                          {/* Thời lượng ở chặng trước — chỗ nào lâu bất thường thì lộ ra ngay */}
                          {h.durationSeconds != null && (
                            <span className="text-muted-foreground text-xs">
                              Đã ở &quot;{h.fromStageName}&quot;{' '}
                              {formatDistanceStrict(0, h.durationSeconds * 1000, { locale: vi })}
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            ),
          },
        ]}
        tabHienTai={tab}
        onDoiTab={datTab}
        cotPhu={
          d && (
            <div className="flex flex-col gap-3">
              <HangThongTin BieuTuong={User} nhan="Khách hàng">
                <button
                  type="button"
                  className="underline underline-offset-2"
                  onClick={() => dieuHuong(`/khach-hang/${d.contactId}`)}
                >
                  {d.contactName}
                </button>
              </HangThongTin>
              <HangThongTin nhan="Giá trị">{tien(d.amount)}</HangThongTin>
              <HangThongTin BieuTuong={CalendarClock} nhan="Dự kiến chốt">
                {d.expectedCloseDate ? format(new Date(d.expectedCloseDate), 'dd/MM/yyyy') : 'Chưa đặt'}
              </HangThongTin>
              <HangThongTin BieuTuong={User} nhan="Phụ trách">
                {d.ownerName ?? <span className="text-destructive">Chưa ai nhận</span>}
              </HangThongTin>
              {d.leadId && (
                <HangThongTin BieuTuong={Target} nhan="Sinh từ lead">
                  <button
                    type="button"
                    className="underline underline-offset-2"
                    onClick={() => dieuHuong(`/ban-hang/co-hoi-tiem-nang/${d.leadId}`)}
                  >
                    Mở lead
                  </button>
                </HangThongTin>
              )}

              {dangMo && duocSua && (
                <div className="flex flex-col gap-1.5 pt-1">
                  <span className="text-muted-foreground text-xs font-medium">Kết thúc deal</span>
                  {giaiDoan
                    .filter((g) => g.isWon || g.isLost)
                    .map((g) => (
                      <Button
                        key={g.id}
                        variant={g.isLost ? 'outline' : 'default'}
                        size="sm"
                        disabled={ketQuaKeo.isLoading}
                        onClick={() => (g.isLost ? datChoThua(g.id) : void chuyen(g.id))}
                      >
                        {g.name}
                      </Button>
                    ))}
                </div>
              )}
            </div>
          )
        }
      />

      {d && <SuaDealDialog deal={d} mo={moSua} onDoiMo={datMoSua} />}
      {d && laQuanTri && <DoiPhuTrachDealDialog deal={d} mo={moDoiChu} onDoiMo={datMoDoiChu} />}
      {d && choBoSung && (
        <SuaDealDialog
          deal={d}
          mo
          onDoiMo={(m) => !m && datChoBoSung(null)}
          lyDo={choBoSung.lyDo}
          onDaLuu={() => {
            const { stageId } = choBoSung
            datChoBoSung(null)
            void chuyen(stageId)
          }}
        />
      )}
      <LyDoThuaDialog
        mo={!!choThua}
        onDoiMo={(m) => !m && datChoThua(null)}
        dangGui={ketQuaKeo.isLoading}
        onChon={async (lyDo) => {
          if (choThua && (await chuyen(choThua, lyDo))) datChoThua(null)
        }}
      />
    </>
  )
}
