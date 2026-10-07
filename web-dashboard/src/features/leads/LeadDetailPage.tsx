import { format, formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import {
  ArrowRight,
  Ban,
  Calendar,
  Hand,
  MessagesSquare,
  Pencil,
  Phone,
  RotateCcw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  User,
  UserCog,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useCapNhatLeadMutation, useChiTietLeadQuery, useLichSuDiemLeadQuery } from '@/api/sales'
import { useAppSelector } from '@/app/store/hooks'
import { DetailPage, HangThongTin } from '@/components/layout/DetailPage'
import type { ThaoTac } from '@/components/layout/ListPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { EmptyState } from '@/components/ui/empty-state'
import { Progress } from '@/components/ui/progress'
import { StatusChip } from '@/components/ui/status-chip'
import { ChuyenDealDialog } from '@/features/leads/ChuyenDealDialog'
import { DoiPhuTrachDialog, LoaiLeadDialog, SuaLeadDialog } from '@/features/leads/LeadDialogs'
import {
  NHAN_LY_DO_LOAI,
  NHAN_MUC_DO,
  NHAN_TRANG_THAI_LEAD,
  NUT_CHUYEN_TRANG_THAI,
  sacThaiDiem,
  tien,
} from '@/features/leads/nhan'
import type { TrangThaiLead, YeuToDiem } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * SCR042 — chi tiết lead (UC032 bước 4–9).
 *
 * Nút chuyển trạng thái lấy từ `allowedNextStatuses` của máy chủ — giao diện không tự suy luật
 * "đi tới, được bỏ bước, không lùi" lần thứ hai. Quyền sửa giống máy chủ: lead của mình, lead chưa
 * ai nhận (sửa = tự nhận), hoặc quản trị viên.
 *
 * "Chuyển thành Deal" (UC033) là thao tác chính khi lead còn mở. Danh sách hoạt động (UC035) chưa có
 * API — ẩn đi thay vì để nút bấm ra lỗi.
 */
export function LeadDetailPage() {
  const { id = '' } = useParams()
  const dieuHuong = useNavigate()
  const [tab, datTab] = useState('diem')
  const [moLoai, datMoLoai] = useState(false)
  const [moSua, datMoSua] = useState(false)
  const [moDoiChu, datMoDoiChu] = useState(false)
  const [moChuyen, datMoChuyen] = useState(false)
  const toi = useAppSelector((s) => s.auth.nguoiDung)
  const laQuanTri = toi?.roleCode === 'TENANT_ADMIN'

  const truyVan = useChiTietLeadQuery(id)
  const lichSu = useLichSuDiemLeadQuery(id)
  const [capNhat, ketQuaCapNhat] = useCapNhatLeadMutation()

  const l = truyVan.data
  const diem = l?.latestScore

  const duocSua = !!l && (laQuanTri || !l.ownerUserId || l.ownerUserId === toi?.id)
  const dongLai = l?.status === 'DISQUALIFIED' || l?.status === 'CONVERTED'

  async function chuyenTrangThai(den: TrangThaiLead) {
    if (den === 'DISQUALIFIED') {
      datMoLoai(true)
      return
    }
    try {
      await capNhat({ id, than: { status: den } }).unwrap()
      toast.success(`Đã chuyển sang "${NHAN_TRANG_THAI_LEAD[den].nhan}".`)
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không đổi được trạng thái.')
    }
  }

  const thaoTac: ThaoTac[] = []
  if (l && duocSua) {
    if (!l.ownerUserId && !laQuanTri) {
      thaoTac.push({
        nhan: 'Nhận lead',
        BieuTuong: Hand,
        onClick: async () => {
          try {
            await capNhat({ id, than: { ownerUserId: toi?.id } }).unwrap()
            toast.success('Bạn đang phụ trách lead này.')
          } catch (loi) {
            toast.error(laLoiTruyVan(loi) ? loi.message : 'Không nhận được lead.')
          }
        },
      })
    }
    if (!dongLai) {
      thaoTac.push({ nhan: 'Sửa thông tin', BieuTuong: Pencil, onClick: () => datMoSua(true) })
    }
    if (laQuanTri && l.status !== 'CONVERTED') {
      thaoTac.push({ nhan: 'Đổi phụ trách', BieuTuong: UserCog, onClick: () => datMoDoiChu(true) })
    }
    for (const den of l.allowedNextStatuses) {
      thaoTac.push({
        nhan: NUT_CHUYEN_TRANG_THAI[den],
        BieuTuong: den === 'DISQUALIFIED' ? Ban : den === 'NEW' ? RotateCcw : undefined,
        bienThe: den === 'DISQUALIFIED' ? 'destructive' : 'outline',
        onClick: () => void chuyenTrangThai(den),
      })
    }
  }

  return (
    <>
      <DetailPage
        quayLai={{ duongDan: '/ban-hang/co-hoi-tiem-nang', nhan: 'Lead' }}
        tieuDe={l?.contactName ?? 'Lead'}
        phuDe={l?.interestedProduct ?? undefined}
        dangTai={truyVan.isLoading}
        chip={
          l && (
            <>
              <StatusChip sacThai={NHAN_TRANG_THAI_LEAD[l.status].sacThai}>
                {NHAN_TRANG_THAI_LEAD[l.status].nhan}
              </StatusChip>
              {l.source === 'AI_AUTO' ? (
                <StatusChip sacThai="info" BieuTuong={Sparkles}>
                  Tác tử AI tạo
                </StatusChip>
              ) : (
                <StatusChip>Nhập tay</StatusChip>
              )}
            </>
          )
        }
        thaoTacChinh={
          l && duocSua && !dongLai
            ? { nhan: 'Chuyển thành Deal', BieuTuong: ArrowRight, onClick: () => datMoChuyen(true) }
            : undefined
        }
        thaoTacPhu={thaoTac.length > 0 ? thaoTac : undefined}
        tab={[
          {
            khoa: 'diem',
            nhan: 'Điểm tiềm năng',
            noiDung: l && (
              <div className="flex flex-col gap-4">
                {ketQuaCapNhat.isLoading && (
                  <Alert>
                    <AlertDescription>Đang lưu…</AlertDescription>
                  </Alert>
                )}

                {!duocSua && (
                  <Alert>
                    <User />
                    <AlertDescription>
                      Lead do <strong>{l.ownerName ?? 'người khác'}</strong> phụ trách — bạn chỉ xem được.
                    </AlertDescription>
                  </Alert>
                )}

                {l.status === 'CONVERTED' && l.convertedDealId && (
                  <Alert>
                    <ArrowRight />
                    <AlertDescription>
                      Đã chuyển thành deal
                      {l.convertedAt && ` lúc ${format(new Date(l.convertedAt), 'dd/MM/yyyy HH:mm')}`} —{' '}
                      <button
                        type="button"
                        className="underline underline-offset-2"
                        onClick={() => dieuHuong(`/ban-hang/pheu/${l.convertedDealId}`)}
                      >
                        mở deal
                      </button>
                      .
                    </AlertDescription>
                  </Alert>
                )}

                {l.status === 'DISQUALIFIED' && (
                  <Alert>
                    <Ban />
                    <AlertDescription>
                      Đã loại
                      {l.disqualifyReason && (
                        <>
                          {' '}
                          — lý do: <strong>{NHAN_LY_DO_LOAI[l.disqualifyReason]}</strong>
                        </>
                      )}
                      {l.closedAt && ` · ${format(new Date(l.closedAt), 'dd/MM/yyyy HH:mm')}`}. Bấm
                      &quot;Mở lại&quot; nếu khách quay lại quan tâm.
                    </AlertDescription>
                  </Alert>
                )}

                {!diem ? (
                  <EmptyState
                    BieuTuong={Sparkles}
                    tieuDe="Chưa chấm điểm"
                    moTa="Điểm do mô hình chấm từ tín hiệu hội thoại (UC030). Lead chưa có lần chấm nào thì xếp cuối danh sách."
                  />
                ) : (
                  <>
                    {diem.confidence === 'LOW' && (
                      <Alert>
                        <AlertDescription>
                          Độ tin cậy <strong>thấp</strong>: mô hình thiếu đặc trưng bắt buộc (thường là
                          ngân sách hoặc thông tin liên hệ). Con số này chỉ để tham khảo.
                        </AlertDescription>
                      </Alert>
                    )}
                    {diem.scoringMode === 'RULE' && (
                      <Alert>
                        <AlertDescription>
                          Chấm bằng <strong>bảng điểm theo luật</strong> (phương án dự phòng khi mô hình
                          không chạy được) — không so sánh trực tiếp với điểm mô hình.
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
                          {formatDistanceToNowStrict(new Date(diem.computedAt), { locale: vi, addSuffix: true })}
                        </span>
                      </div>
                    </div>

                    {diem.topFactors.length > 0 && (
                      <div className="flex flex-col gap-1.5">
                        <span className="text-[13px] font-medium">Yếu tố ảnh hưởng</span>
                        {diem.topFactors.map((y) => (
                          <DongYeuTo key={y.name} yeuTo={y} />
                        ))}
                      </div>
                    )}
                  </>
                )}

                {/* UC032 bước 6 — lịch sử điểm theo thời gian */}
                {lichSu.data && lichSu.data.length > 1 && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-[13px] font-medium">Lịch sử điểm</span>
                    {lichSu.data.map((d) => (
                      <div
                        key={d.computedAt}
                        className="flex items-center gap-3 rounded-lg border px-3 py-2 text-[13px]"
                      >
                        <span className="w-8 font-medium tabular-nums">{d.score}</span>
                        <span className="text-muted-foreground flex-1 truncate text-xs">
                          {d.modelVersion}
                          {d.scoringMode === 'RULE' && ' · bảng luật'}
                        </span>
                        <span className="text-muted-foreground text-xs tabular-nums">
                          {format(new Date(d.computedAt), 'dd/MM/yyyy HH:mm')}
                        </span>
                      </div>
                    ))}
                  </div>
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
                {l.budgetMin != null || l.budgetMax != null
                  ? `${tien(l.budgetMin)} – ${tien(l.budgetMax)}`
                  : 'Chưa rõ'}
              </HangThongTin>
              <HangThongTin nhan="Mức gấp">{l.urgency ? NHAN_MUC_DO[l.urgency] : '—'}</HangThongTin>
              <HangThongTin BieuTuong={User} nhan="Phụ trách">
                {l.ownerName ?? <span className="text-destructive">Chưa ai nhận</span>}
              </HangThongTin>
              <HangThongTin BieuTuong={Calendar} nhan="Tạo lúc">
                {format(new Date(l.createdAt), 'dd/MM/yyyy HH:mm')}
              </HangThongTin>
              {l.sourceConversationId ? (
                <HangThongTin BieuTuong={MessagesSquare} nhan="Hội thoại nguồn">
                  <button
                    type="button"
                    className="underline underline-offset-2"
                    onClick={() => dieuHuong(`/hop-thu?c=${l.sourceConversationId}`)}
                  >
                    Mở trong Hộp thư
                  </button>
                </HangThongTin>
              ) : (
                // UC032 6.1–6.2: lead do AI tạo luôn sinh từ một hội thoại — mất liên kết nghĩa là
                // hội thoại đã bị xoá theo yêu cầu xoá dữ liệu cá nhân (FK ON DELETE SET NULL)
                l.source === 'AI_AUTO' && (
                  <HangThongTin BieuTuong={MessagesSquare} nhan="Hội thoại nguồn">
                    <span className="text-muted-foreground">Hội thoại gốc đã bị xoá</span>
                  </HangThongTin>
                )
              )}
            </div>
          )
        }
      />

      {l && <ChuyenDealDialog lead={l} mo={moChuyen} onDoiMo={datMoChuyen} />}
      {l && <LoaiLeadDialog lead={l} mo={moLoai} onDoiMo={datMoLoai} />}
      {l && <SuaLeadDialog lead={l} mo={moSua} onDoiMo={datMoSua} />}
      {l && laQuanTri && <DoiPhuTrachDialog lead={l} mo={moDoiChu} onDoiMo={datMoDoiChu} />}
    </>
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
