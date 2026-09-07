import { format, formatDistanceStrict, formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { CalendarClock, Phone, Target, TriangleAlert, User } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import {
  useChiTietDealQuery,
  useDanhSachPheuQuery,
  useKeoDealSangGiaiDoanMutation,
} from '@/api/sales'
import { DetailPage, HangThongTin } from '@/components/layout/DetailPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { StatusChip } from '@/components/ui/status-chip'
import {
  NHAN_KET_QUA,
  NHAN_LOAI_HOAT_DONG,
  NHAN_TRANG_THAI_DEAL,
  tien,
} from '@/features/leads/nhan'
import { cn } from '@/utils/cn'

/**
 * SCR045 — chi tiết cơ hội bán hàng. Màn chữ ký.
 *
 * Tab **Lịch sử giai đoạn** là phần đáng giá nhất: nó cho biết cơ hội mắc kẹt ở đâu và bao lâu.
 * Một cơ hội nằm 21 ngày ở "Đã báo giá" là tín hiệu rõ hơn mọi con số dự báo — và chỉ nhìn thấy
 * được khi hiển thị **thời lượng từng chặng**, không phải chỉ mốc thời gian.
 */
export function DealDetailPage() {
  const { id = '' } = useParams()
  const dieuHuong = useNavigate()
  const [tab, datTab] = useState('lich-su')

  const truyVan = useChiTietDealQuery(id)
  const pheu = useDanhSachPheuQuery()
  const [keo, ketQuaKeo] = useKeoDealSangGiaiDoanMutation()

  const d = truyVan.data
  const giaiDoan = pheu.data?.[0]?.stages ?? []
  const hienTai = giaiDoan.find((g) => g.id === d?.stageId)
  const keTiep = giaiDoan.find((g) => g.position === (hienTai?.position ?? 0) + 1)

  async function chuyen(stageId: string, ten: string) {
    try {
      await keo({ id, stageId }).unwrap()
      toast.success(`Đã chuyển sang "${ten}".`)
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không chuyển được giai đoạn.')
    }
  }

  return (
    <DetailPage
      quayLai={{ duongDan: '/ban-hang/pheu', nhan: 'Phễu bán hàng' }}
      tieuDe={d?.title ?? 'Cơ hội bán hàng'}
      phuDe={d ? `${d.contactName} · ${tien(d.amount)}` : undefined}
      dangTai={truyVan.isLoading}
      chip={
        d && (
          <>
            <StatusChip sacThai={NHAN_TRANG_THAI_DEAL[d.status].sacThai}>
              {NHAN_TRANG_THAI_DEAL[d.status].nhan}
            </StatusChip>
            <StatusChip>{d.stageName}</StatusChip>
            {d.isOverdue && (
              <StatusChip sacThai="destructive" BieuTuong={CalendarClock}>
                Quá hạn chốt
              </StatusChip>
            )}
          </>
        )
      }
      thaoTacChinh={
        d && d.status === 'OPEN' && keTiep
          ? {
              nhan: `Chuyển sang "${keTiep.name}"`,
              onClick: () => chuyen(keTiep.id, keTiep.name),
            }
          : undefined
      }
      tab={[
        {
          khoa: 'lich-su',
          nhan: 'Lịch sử giai đoạn',
          soLuong: d?.stageHistory?.length,
          noiDung: d && (
            <div className="flex flex-col gap-4">
              {laLoiTruyVan(ketQuaKeo.error) && (
                <Alert variant="destructive">
                  <TriangleAlert />
                  <AlertDescription>{ketQuaKeo.error.message}</AlertDescription>
                </Alert>
              )}

              {d.amount == null && (
                <Alert>
                  <TriangleAlert />
                  <AlertDescription>
                    Cơ hội chưa có giá trị. Các giai đoạn sau &quot;Mới tiếp nhận&quot; bắt buộc có
                    số tiền, nên phải nhập trước khi chuyển tiếp — và mọi báo cáo doanh thu đang bỏ
                    sót cơ hội này.
                  </AlertDescription>
                </Alert>
              )}

              {d.closeReason && (
                <Alert>
                  <AlertDescription>
                    <strong>Lý do kết thúc:</strong> {d.closeReason}
                  </AlertDescription>
                </Alert>
              )}

              {(d.stageHistory?.length ?? 0) === 0 ? (
                <EmptyState
                  BieuTuong={Target}
                  tieuDe="Chưa có lần chuyển giai đoạn nào"
                  moTa="Cơ hội vừa được tạo và còn ở giai đoạn đầu."
                />
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
                          {h.fromStageName ? `${h.fromStageName} → ` : ''}
                          {h.toStageName}
                        </span>
                        <span className="text-muted-foreground text-xs">
                          {format(new Date(h.changedAt), 'dd/MM/yyyy HH:mm', { locale: vi })}
                          {h.changedByName && ` · ${h.changedByName}`}
                        </span>
                        {/* Thời lượng ở chặng trước — chỗ nào lâu bất thường thì lộ ra ngay */}
                        {h.durationSeconds != null && (
                          <span className="text-muted-foreground text-xs">
                            Ở giai đoạn trước{' '}
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
        {
          khoa: 'hoat-dong',
          nhan: 'Hoạt động',
          soLuong: d?.activities?.length,
          noiDung: d && (
            <div className="flex flex-col gap-2">
              {(d.activities?.length ?? 0) === 0 ? (
                <EmptyState
                  BieuTuong={Phone}
                  tieuDe="Chưa có hoạt động nào"
                  moTa="Ghi nhận cuộc gọi, buổi gặp hoặc báo giá gắn với cơ hội này."
                />
              ) : (
                d.activities?.map((h) => (
                  <div key={h.id} className="flex items-start gap-3 rounded-lg border p-3">
                    <StatusChip>{NHAN_LOAI_HOAT_DONG[h.type]}</StatusChip>
                    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="text-[13px] font-medium">{h.subject ?? '—'}</span>
                      <span className="text-muted-foreground text-xs">
                        {h.performedByName}
                        {h.performedAt &&
                          ` · ${formatDistanceToNowStrict(new Date(h.performedAt), { locale: vi, addSuffix: true })}`}
                      </span>
                    </div>
                    {h.outcome && (
                      <StatusChip sacThai={NHAN_KET_QUA[h.outcome].sacThai}>
                        {NHAN_KET_QUA[h.outcome].nhan}
                      </StatusChip>
                    )}
                  </div>
                ))
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
              {d.ownerName ?? 'Chưa giao'}
            </HangThongTin>
            {d.leadId && (
              <HangThongTin BieuTuong={Target} nhan="Sinh từ cơ hội tiềm năng">
                <button
                  type="button"
                  className="underline underline-offset-2"
                  onClick={() => dieuHuong(`/ban-hang/co-hoi-tiem-nang/${d.leadId}`)}
                >
                  Mở cơ hội tiềm năng
                </button>
              </HangThongTin>
            )}

            {d.status === 'OPEN' && (
              <div className="flex flex-col gap-1.5 pt-1">
                <span className="text-muted-foreground text-xs font-medium">Kết thúc cơ hội</span>
                {giaiDoan
                  .filter((g) => g.isWon || g.isLost)
                  .map((g) => (
                    <Button
                      key={g.id}
                      variant="outline"
                      size="sm"
                      disabled={ketQuaKeo.isLoading}
                      onClick={() => chuyen(g.id, g.name)}
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
  )
}
