import { format } from 'date-fns'
import { vi } from 'date-fns/locale'
import { CalendarClock, Check, CreditCard } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import {
  useDanhSachGoiQuery,
  useDoiGoiMutation,
  useHanMucHienTaiQuery,
  useThueBaoHienTaiQuery,
} from '@/api/platform'
import { DetailPage, HangThongTin } from '@/components/layout/DetailPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { StatusChip } from '@/components/ui/status-chip'
import type { GoiDichVu, MaGoi, TrangThaiThueBao } from '@/types/schema'
import { cn } from '@/utils/cn'

const NHAN_TRANG_THAI: Record<
  TrangThaiThueBao,
  { nhan: string; sacThai: 'success' | 'warning' | 'destructive' | 'neutral' }
> = {
  TRIALING: { nhan: 'Đang dùng thử', sacThai: 'warning' },
  ACTIVE: { nhan: 'Đang hiệu lực', sacThai: 'success' },
  PAST_DUE: { nhan: 'Quá hạn thanh toán', sacThai: 'destructive' },
  EXPIRED: { nhan: 'Đã hết hạn', sacThai: 'destructive' },
  CANCELED: { nhan: 'Đã huỷ', sacThai: 'neutral' },
}

const tien = (v: number) => new Intl.NumberFormat('vi-VN').format(v) + ' ₫'
const so = (v: number) => new Intl.NumberFormat('vi-VN').format(v)
const ngay = (s: string) => format(new Date(s), 'dd/MM/yyyy', { locale: vi })

/**
 * SCR012 + SCR013 — thuê bao hiện tại và bảng so sánh gói. Mẫu M2.
 *
 * Gộp hai màn vào hai tab của cùng một trang: người dùng vào đây để trả lời **một** câu hỏi —
 * "gói hiện tại có đủ không, có cần đổi không" — và câu trả lời cần cả hai nửa cạnh nhau. Tách
 * thành hai route là bắt họ bấm qua bấm lại để so sánh.
 */
export function SubscriptionPage() {
  const [tab, datTab] = useState('hien-tai')
  const thueBao = useThueBaoHienTaiQuery()
  const goi = useDanhSachGoiQuery()
  const hanMuc = useHanMucHienTaiQuery()
  const [doiGoi, ketQuaDoi] = useDoiGoiMutation()

  const tb = thueBao.data
  const trangThai = tb ? NHAN_TRANG_THAI[tb.status] : null

  const chuyenGoi = async (ma: MaGoi, lenGoi: boolean) => {
    const kq = await doiGoi(ma).unwrap()
    toast.success(
      lenGoi
        ? 'Đã nâng gói. Hạn mức mới có hiệu lực ngay.'
        : `Đã đặt lịch hạ gói từ ${ngay(kq.scheduledEffectiveAt ?? kq.periodEnd)}.`,
    )
  }

  return (
    <DetailPage
      quayLai={{ duongDan: '/cai-dat', nhan: 'Cài đặt' }}
      tieuDe={tb ? `Gói ${tb.plan.name}` : 'Thuê bao'}
      phuDe={tb ? `Chu kỳ ${ngay(tb.periodStart)} – ${ngay(tb.periodEnd)}` : undefined}
      chip={trangThai && <StatusChip sacThai={trangThai.sacThai}>{trangThai.nhan}</StatusChip>}
      dangTai={thueBao.isLoading || goi.isLoading}
      tab={[
        {
          khoa: 'hien-tai',
          nhan: 'Gói hiện tại',
          noiDung: (
            <div className="flex flex-col gap-5">
              {tb?.readOnlyMode && (
                <Alert variant="destructive">
                  <AlertDescription>
                    Thuê bao đang ở chế độ chỉ đọc. Tác tử AI ngừng trả lời khách cho tới khi
                    thanh toán được xác nhận; tin nhắn đến vẫn được ghi lại đầy đủ.
                  </AlertDescription>
                </Alert>
              )}

              {tb?.scheduledPlan && (
                <Alert>
                  <CalendarClock />
                  <AlertDescription>
                    Đã đặt lịch chuyển sang gói <strong>{tb.scheduledPlan.name}</strong> từ{' '}
                    {ngay(tb.scheduledEffectiveAt ?? tb.periodEnd)}. Hạ gói giữa chu kỳ sẽ cắt mất
                    phần hạn mức đã trả tiền, nên nó chờ tới hết chu kỳ này.
                  </AlertDescription>
                </Alert>
              )}

              {hanMuc.data && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <ODungTrenHanMuc
                    nhan="Hội thoại"
                    daDung={hanMuc.data.conversations.used}
                    hanMuc={hanMuc.data.conversations.quota}
                  />
                  <ODungTrenHanMuc
                    nhan="Token"
                    daDung={hanMuc.data.tokens.used}
                    hanMuc={hanMuc.data.tokens.quota}
                  />
                  <ODungTrenHanMuc
                    nhan="Người dùng"
                    daDung={hanMuc.data.users.used}
                    hanMuc={hanMuc.data.users.quota}
                  />
                  <ODungTrenHanMuc
                    nhan="Tài liệu"
                    daDung={hanMuc.data.documents.used}
                    hanMuc={hanMuc.data.documents.quota}
                  />
                </div>
              )}
            </div>
          ),
        },
        {
          khoa: 'so-sanh',
          nhan: 'So sánh gói',
          soLuong: goi.data?.length,
          noiDung: (
            <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
              {goi.data?.map((g) => (
                <TheGoi
                  key={g.code}
                  goi={g}
                  hienTai={g.code === tb?.plan.code}
                  dangDoi={ketQuaDoi.isLoading}
                  onChon={() =>
                    chuyenGoi(g.code, (g.sortOrder ?? 0) > (tb?.plan.sortOrder ?? 0))
                  }
                />
              ))}
            </div>
          ),
        },
      ]}
      tabHienTai={tab}
      onDoiTab={datTab}
      cotPhu={
        tb && (
          <div className="flex flex-col gap-3">
            <HangThongTin BieuTuong={CreditCard} nhan="Giá mỗi tháng">
              {tien(tb.plan.monthlyPriceVnd)}
            </HangThongTin>
            <HangThongTin BieuTuong={CalendarClock} nhan="Gia hạn tiếp theo">
              {ngay(tb.periodEnd)}
            </HangThongTin>
            {hanMuc.data?.costVnd !== undefined && (
              <HangThongTin nhan="Chi phí AI chu kỳ này">{tien(hanMuc.data.costVnd)}</HangThongTin>
            )}
            <p className="text-muted-foreground text-xs leading-relaxed">
              Chi phí AI tính theo token thực dùng, tách khỏi giá thuê bao. Nó thay đổi theo độ dài
              tài liệu được truy hồi, nên không phải một con số cố định hàng tháng.
            </p>
          </div>
        )
      }
    />
  )
}

function ODungTrenHanMuc({
  nhan,
  daDung,
  hanMuc,
}: {
  nhan: string
  daDung: number
  hanMuc: number
}) {
  const phanTram = Math.min(Math.round((daDung / hanMuc) * 100), 100)
  const gan = phanTram >= 80
  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13px] font-medium">{nhan}</span>
        <span
          className={cn('text-xs tabular-nums', gan ? 'text-destructive' : 'text-muted-foreground')}
        >
          {so(daDung)} / {so(hanMuc)}
        </span>
      </div>
      <Progress value={phanTram} className={gan ? '[&>div]:bg-destructive' : undefined} />
    </div>
  )
}

function TheGoi({
  goi,
  hienTai,
  dangDoi,
  onChon,
}: {
  goi: GoiDichVu
  hienTai: boolean
  dangDoi: boolean
  onChon: () => void
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-lg border p-4',
        hienTai && 'ring-primary ring-1',
      )}
    >
      <div className="flex flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="font-medium">{goi.name}</span>
          {hienTai && <StatusChip sacThai="info">Đang dùng</StatusChip>}
        </div>
        <span className="text-lg font-semibold tabular-nums">
          {goi.monthlyPriceVnd === 0 ? 'Miễn phí' : tien(goi.monthlyPriceVnd)}
        </span>
      </div>

      <ul className="text-muted-foreground flex flex-col gap-1.5 text-[13px]">
        <DongGoi>{so(goi.conversationQuota)} hội thoại mỗi tháng</DongGoi>
        {goi.tokenQuota !== undefined && <DongGoi>{so(goi.tokenQuota)} token</DongGoi>}
        {goi.maxUsers !== undefined && <DongGoi>{goi.maxUsers} người dùng</DongGoi>}
        {goi.maxDocuments !== undefined && <DongGoi>{so(goi.maxDocuments)} tài liệu</DongGoi>}
      </ul>

      <span className="flex-1" />

      {hienTai ? (
        <Button variant="outline" size="sm" disabled>
          Gói hiện tại
        </Button>
      ) : (
        <Button variant="outline" size="sm" onClick={onChon} disabled={dangDoi}>
          Chọn gói này
        </Button>
      )}
    </div>
  )
}

function DongGoi({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-1.5">
      <Check className="text-chart-2 size-3.5 shrink-0" />
      {children}
    </li>
  )
}
