import { format, formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import {
  ArrowRight,
  Ban,
  Calendar,
  MessagesSquare,
  Phone,
  Sparkles,
  TrendingDown,
  TrendingUp,
  User,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import {
  useCapNhatLeadMutation,
  useChiTietLeadQuery,
  useChuyenLeadThanhDealMutation,
  useDanhSachHoatDongQuery,
  useDanhSachPheuQuery,
} from '@/api/sales'
import { DetailPage, HangThongTin } from '@/components/layout/DetailPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { EmptyState } from '@/components/ui/empty-state'
import { Progress } from '@/components/ui/progress'
import { StatusChip } from '@/components/ui/status-chip'
import {
  NHAN_KET_QUA,
  NHAN_LOAI_HOAT_DONG,
  NHAN_MUC_DO,
  NHAN_TRANG_THAI_LEAD,
  sacThaiDiem,
  tien,
} from '@/features/leads/nhan'
import type { YeuToDiem } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * SCR042 — chi tiết cơ hội tiềm năng. Màn chữ ký.
 *
 * Trọng tâm là **giải thích điểm**, không phải hiển thị điểm. Một con số 87 không giúp nhân viên
 * quyết định gì; danh sách yếu tố cộng/trừ thì có — và nó cũng là cách duy nhất để phát hiện mô
 * hình đang chấm sai (ví dụ cộng điểm cho một tín hiệu vô nghĩa).
 */
export function LeadDetailPage() {
  const { id = '' } = useParams()
  const dieuHuong = useNavigate()
  const [tab, datTab] = useState('diem')

  const truyVan = useChiTietLeadQuery(id)
  const hoatDong = useDanhSachHoatDongQuery({ leadId: id })
  const pheu = useDanhSachPheuQuery()
  const [chuyenDoi, ketQuaChuyen] = useChuyenLeadThanhDealMutation()
  const [capNhat, ketQuaCapNhat] = useCapNhatLeadMutation()

  const l = truyVan.data
  const diem = l?.latestScore
  const giaiDoanDau = pheu.data?.[0]?.stages.find((g) => g.position === 0)

  return (
    <DetailPage
      quayLai={{ duongDan: '/ban-hang/co-hoi-tiem-nang', nhan: 'Cơ hội tiềm năng' }}
      tieuDe={l?.contactName ?? 'Cơ hội tiềm năng'}
      phuDe={l?.interestedProduct ?? undefined}
      dangTai={truyVan.isLoading}
      chip={
        l && (
          <>
            <StatusChip sacThai={NHAN_TRANG_THAI_LEAD[l.status].sacThai}>
              {NHAN_TRANG_THAI_LEAD[l.status].nhan}
            </StatusChip>
            {l.source === 'AI_AUTO' && (
              <StatusChip sacThai="info" BieuTuong={Sparkles}>
                Tác tử AI tạo
              </StatusChip>
            )}
          </>
        )
      }
      thaoTacChinh={
        l && l.status !== 'CONVERTED' && l.status !== 'DISQUALIFIED'
          ? {
              nhan: 'Chuyển thành cơ hội bán hàng',
              BieuTuong: ArrowRight,
              onClick: async () => {
                if (!pheu.data?.[0] || !giaiDoanDau) return
                const kq = await chuyenDoi({
                  id,
                  pipelineId: pheu.data[0].id,
                  stageId: giaiDoanDau.id,
                }).unwrap()
                toast.success('Đã chuyển thành cơ hội bán hàng.')
                dieuHuong(`/ban-hang/pheu/${kq.id}`)
              },
            }
          : undefined
      }
      thaoTacPhu={
        l && l.status !== 'CONVERTED' && l.status !== 'DISQUALIFIED'
          ? [
              {
                nhan: 'Đánh dấu không phù hợp',
                BieuTuong: Ban,
                onClick: async () => {
                  await capNhat({ id, than: { status: 'DISQUALIFIED' } }).unwrap()
                  toast.success('Đã đánh dấu không phù hợp.')
                },
              },
            ]
          : undefined
      }
      tab={[
        {
          khoa: 'diem',
          nhan: 'Điểm tiềm năng',
          noiDung: l && (
            <div className="flex flex-col gap-4">
              {(ketQuaChuyen.isLoading || ketQuaCapNhat.isLoading) && (
                <Alert>
                  <AlertDescription>Đang xử lý…</AlertDescription>
                </Alert>
              )}

              {l.status === 'CONVERTED' && l.convertedDealId && (
                <Alert>
                  <ArrowRight />
                  <AlertDescription>
                    Đã chuyển thành cơ hội bán hàng{' '}
                    <button
                      type="button"
                      className="underline underline-offset-2"
                      onClick={() => dieuHuong(`/ban-hang/pheu/${l.convertedDealId}`)}
                    >
                      mở cơ hội đó
                    </button>
                    .
                  </AlertDescription>
                </Alert>
              )}

              {l.disqualifyReason && (
                <Alert>
                  <Ban />
                  <AlertDescription>{l.disqualifyReason}</AlertDescription>
                </Alert>
              )}

              {!diem ? (
                <EmptyState
                  BieuTuong={Sparkles}
                  tieuDe="Chưa có điểm tiềm năng"
                  moTa="Mô hình chấm điểm chạy trên tín hiệu hội thoại. Cơ hội nhập tay chưa gắn với hội thoại nào nên chưa có điểm."
                />
              ) : (
                <>
                  {diem.confidence === 'LOW' && (
                    <Alert>
                      <AlertDescription>
                        Độ tin cậy <strong>thấp</strong>: mô hình thiếu đặc trưng bắt buộc (thường
                        là ngân sách hoặc thông tin liên hệ). Con số này chỉ để tham khảo, đừng
                        dùng nó để xếp thứ tự gọi.
                      </AlertDescription>
                    </Alert>
                  )}

                  {diem.scoringMode === 'RULE' && (
                    <Alert>
                      <AlertDescription>
                        Chấm bằng <strong>bảng điểm theo luật</strong>, không phải mô hình — đây là
                        phương án dự phòng khi mô hình không chạy được. Điểm loại này không so
                        sánh trực tiếp với điểm mô hình.
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="flex items-center gap-4 rounded-lg border p-4">
                    <div className="flex flex-col items-center gap-1">
                      <span className="text-3xl font-semibold tabular-nums">{diem.score}</span>
                      <StatusChip sacThai={sacThaiDiem(diem.score)}>
                        {diem.score >= 80 ? 'Ưu tiên cao' : diem.score >= 60 ? 'Cân nhắc' : 'Thấp'}
                      </StatusChip>
                    </div>
                    <div className="flex min-w-0 flex-1 flex-col gap-2">
                      <Progress value={diem.score} />
                      <span className="text-muted-foreground text-xs">
                        {diem.modelVersion} · chấm{' '}
                        {formatDistanceToNowStrict(new Date(diem.computedAt), {
                          locale: vi,
                          addSuffix: true,
                        })}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <span className="text-[13px] font-medium">Yếu tố ảnh hưởng</span>
                    <p className="text-muted-foreground text-xs leading-relaxed">
                      Cộng và trừ so với điểm nền. Yếu tố có đóng góp 0 nghĩa là mô hình không tìm
                      thấy tín hiệu đó — khác với &quot;tín hiệu xấu&quot;.
                    </p>
                    {diem.topFactors.map((y) => (
                      <DongYeuTo key={y.name} yeuTo={y} />
                    ))}
                  </div>
                </>
              )}
            </div>
          ),
        },
        {
          khoa: 'hoat-dong',
          nhan: 'Hoạt động',
          soLuong: hoatDong.data?.totalItems,
          noiDung: (
            <div className="flex flex-col gap-2">
              {hoatDong.data?.items.length === 0 ? (
                <EmptyState
                  BieuTuong={Phone}
                  tieuDe="Chưa có hoạt động nào"
                  moTa="Ghi nhận cuộc gọi, buổi gặp hoặc báo giá để cả nhóm biết cơ hội này đã đi tới đâu."
                />
              ) : (
                hoatDong.data?.items.map((h) => (
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
        l && (
          <div className="flex flex-col gap-3">
            <HangThongTin BieuTuong={User} nhan="Khách hàng">
              <button
                type="button"
                className="underline underline-offset-2"
                onClick={() => dieuHuong(`/khach-hang/${l.contactId}`)}
              >
                {l.contactName}
              </button>
            </HangThongTin>
            <HangThongTin BieuTuong={Phone} nhan="Điện thoại">
              {l.contactPhone ?? '—'}
            </HangThongTin>
            <HangThongTin nhan="Ngân sách">
              {l.budgetMin || l.budgetMax ? `${tien(l.budgetMin)} – ${tien(l.budgetMax)}` : 'Chưa rõ'}
            </HangThongTin>
            <HangThongTin nhan="Mức gấp">
              {l.urgency ? NHAN_MUC_DO[l.urgency] : '—'}
            </HangThongTin>
            <HangThongTin BieuTuong={User} nhan="Phụ trách">
              {l.ownerName ?? 'Chưa ai nhận'}
            </HangThongTin>
            <HangThongTin BieuTuong={Calendar} nhan="Tạo lúc">
              {format(new Date(l.createdAt), 'dd/MM/yyyy HH:mm')}
            </HangThongTin>
            {l.sourceConversationId && (
              <HangThongTin BieuTuong={MessagesSquare} nhan="Sinh từ hội thoại">
                <button
                  type="button"
                  className="underline underline-offset-2"
                  onClick={() => dieuHuong('/hop-thu')}
                >
                  Mở hộp thư
                </button>
              </HangThongTin>
            )}
          </div>
        )
      }
    />
  )
}

function DongYeuTo({ yeuTo }: { yeuTo: YeuToDiem }) {
  const duong = yeuTo.contribution > 0
  const khong = yeuTo.contribution === 0
  return (
    <div className="flex items-center gap-2.5 rounded-lg border px-3 py-2">
      <span
        className={cn(
          'flex size-6 shrink-0 items-center justify-center rounded-md',
          khong ? 'bg-muted text-muted-foreground' : duong ? 'bg-chart-2/15 text-chart-2' : 'bg-destructive/10 text-destructive',
        )}
      >
        {khong ? '–' : duong ? <TrendingUp className="size-3.5" /> : <TrendingDown className="size-3.5" />}
      </span>
      <span className="min-w-0 flex-1 truncate text-[13px]">{yeuTo.name}</span>
      {yeuTo.value && <span className="text-muted-foreground text-xs">{yeuTo.value}</span>}
      <span
        className={cn(
          'w-10 shrink-0 text-right text-[13px] font-medium tabular-nums',
          khong ? 'text-muted-foreground' : duong ? 'text-chart-2' : 'text-destructive',
        )}
      >
        {khong ? '0' : duong ? `+${yeuTo.contribution}` : yeuTo.contribution}
      </span>
    </div>
  )
}
