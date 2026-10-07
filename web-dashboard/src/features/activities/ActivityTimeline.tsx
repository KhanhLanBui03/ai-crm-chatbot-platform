import { format, formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { AlarmClock, Bot, Check, MessagesSquare, Pencil, Phone, Plus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useCapNhatHoatDongMutation, useDanhSachHoatDongQuery } from '@/api/sales'
import { useAppSelector } from '@/app/store/hooks'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { StatusChip } from '@/components/ui/status-chip'
import { Textarea } from '@/components/ui/textarea'
import { GhiHoatDongDialog, type DichGhi } from '@/features/activities/GhiHoatDongDialog'
import { NHAN_KET_QUA, NHAN_LOAI_HOAT_DONG } from '@/features/leads/nhan'
import type { HoatDong, KetQuaHoatDong } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * UC035 — dòng thời gian hoạt động của một lead / deal / khách, kèm nút "Ghi hoạt động". Dùng chung cho
 * tab Hoạt động ở SCR042 (lead), SCR045 (deal) và hồ sơ khách (UC016).
 *
 * Dòng AUTO ("Tiếp nhận hội thoại từ AI") có nhãn riêng và đường dẫn mở hội thoại — không sửa được.
 */
export function ActivityTimeline({ dich, hienNoiGan }: { dich: DichGhi; hienNoiGan?: boolean }) {
  const [moGhi, datMoGhi] = useState(false)
  const truyVan = useDanhSachHoatDongQuery({
    khachHangId: dich.leadId || dich.dealId ? undefined : dich.contactId,
    leadId: dich.leadId,
    dealId: dich.dealId,
    coTrang: 50,
  })
  const ds = truyVan.data?.items ?? []

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-muted-foreground text-[13px]">
          {truyVan.data ? `${truyVan.data.totalItems} hoạt động` : 'Đang tải…'}
        </span>
        <Button size="sm" onClick={() => datMoGhi(true)}>
          <Plus />
          Ghi hoạt động
        </Button>
      </div>

      {truyVan.data && ds.length === 0 ? (
        <EmptyState
          BieuTuong={Phone}
          tieuDe="Chưa có hoạt động nào"
          moTa="Ghi lại cuộc gọi, buổi gặp hoặc báo giá để cả nhóm biết khách này đã tới đâu."
        />
      ) : (
        ds.map((h) => <DongHoatDong key={h.id} h={h} hienNoiGan={hienNoiGan} />)
      )}

      <GhiHoatDongDialog mo={moGhi} onDoiMo={datMoGhi} dich={dich} />
    </div>
  )
}

/** Một hoạt động — dùng chung cho dòng thời gian và trang Hoạt động. */
export function DongHoatDong({ h, hienKhach, hienNoiGan }: { h: HoatDong; hienKhach?: boolean; hienNoiGan?: boolean }) {
  const dieuHuong = useNavigate()
  const toi = useAppSelector((s) => s.auth.nguoiDung)
  const laQuanTri = toi?.roleCode === 'TENANT_ADMIN'
  const [capNhat, ketQua] = useCapNhatHoatDongMutation()
  const [moSua, datMoSua] = useState(false)

  const tuDong = h.source === 'AUTO'
  const laTacGia = !tuDong && (laQuanTri || h.performedBy === toi?.id)
  const conNhac = h.remindStatus === 'PENDING' || h.remindStatus === 'SENT'
  const doiNhacDuoc = conNhac && !tuDong && (laTacGia || h.remindUserId === toi?.id)
  const quaHan = conNhac && !!h.remindAt && new Date(h.remindAt).getTime() < Date.now()

  async function danhDau(remindStatus: 'DONE' | 'CANCELED') {
    try {
      await capNhat({ id: h.id, than: { remindStatus } }).unwrap()
      toast.success(remindStatus === 'DONE' ? 'Đã xong việc.' : 'Đã huỷ nhắc việc.')
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không cập nhật được.')
    }
  }

  return (
    <div className={cn('flex items-start gap-3 rounded-lg border p-3', quaHan && 'border-destructive/50')}>
      {tuDong ? (
        <StatusChip sacThai="info" BieuTuong={Bot}>
          Tự động
        </StatusChip>
      ) : (
        <StatusChip>{NHAN_LOAI_HOAT_DONG[h.type]}</StatusChip>
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-[13px] font-medium">{h.subject ?? NHAN_LOAI_HOAT_DONG[h.type]}</span>
        {h.content && <span className="text-[13px] whitespace-pre-line">{h.content}</span>}
        <span className="text-muted-foreground text-xs">
          {h.performedByName}
          {h.performedAt && ` · ${formatDistanceToNowStrict(new Date(h.performedAt), { locale: vi, addSuffix: true })}`}
          {hienKhach && ` · ${h.contactName}`}
          {hienNoiGan && h.dealTitle && ` · Deal: ${h.dealTitle}`}
          {hienNoiGan && h.leadId && ` · Lead: ${h.leadLabel ?? ''}`}
        </span>
        {h.remindAt && h.remindStatus !== 'NONE' && (
          <span
            className={cn(
              'flex items-center gap-1 text-xs',
              quaHan ? 'text-destructive font-medium' : 'text-muted-foreground',
            )}
          >
            <AlarmClock className="size-3.5" />
            Nhắc {format(new Date(h.remindAt), 'HH:mm dd/MM/yyyy')}
            {h.remindUserName && ` · ${h.remindUserName}`}
            {h.remindStatus === 'DONE' && ' · đã xong'}
            {h.remindStatus === 'CANCELED' && ' · đã huỷ'}
            {quaHan && ' · quá hạn'}
          </span>
        )}
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {tuDong && h.conversationId && (
            <Button size="sm" variant="outline" onClick={() => dieuHuong(`/hop-thu?c=${h.conversationId}`)}>
              <MessagesSquare />
              Mở hội thoại
            </Button>
          )}
          {doiNhacDuoc && (
            <>
              <Button size="sm" variant="outline" disabled={ketQua.isLoading} onClick={() => void danhDau('DONE')}>
                <Check />
                Xong
              </Button>
              <Button size="sm" variant="ghost" disabled={ketQua.isLoading} onClick={() => void danhDau('CANCELED')}>
                <X />
                Huỷ nhắc
              </Button>
            </>
          )}
          {laTacGia && (
            <Button size="sm" variant="ghost" onClick={() => datMoSua(true)}>
              <Pencil />
              Cập nhật
            </Button>
          )}
        </div>
      </div>
      {h.outcome && (
        <StatusChip sacThai={NHAN_KET_QUA[h.outcome].sacThai}>{NHAN_KET_QUA[h.outcome].nhan}</StatusChip>
      )}
      {laTacGia && <CapNhatHoatDongDialog h={h} mo={moSua} onDoiMo={datMoSua} />}
    </div>
  )
}

/** Cập nhật kết quả / nội dung / hẹn lại giờ nhắc. Không có xoá — hoạt động là lịch sử. */
function CapNhatHoatDongDialog({ h, mo, onDoiMo }: { h: HoatDong; mo: boolean; onDoiMo: (m: boolean) => void }) {
  const [capNhat, ketQua] = useCapNhatHoatDongMutation()
  const [ketQuaHd, datKetQuaHd] = useState('KHONG')
  const [noiDung, datNoiDung] = useState('')
  const [henLai, datHenLai] = useState('')

  useEffect(() => {
    if (!mo) return
    datKetQuaHd(h.outcome ?? 'KHONG')
    datNoiDung(h.content ?? '')
    datHenLai('')
  }, [mo, h.outcome, h.content])

  return (
    <Dialog open={mo} onOpenChange={onDoiMo}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Cập nhật hoạt động</DialogTitle>
        </DialogHeader>
        <Field>
          <FieldLabel htmlFor="cn-kq">Kết quả</FieldLabel>
          <Select value={ketQuaHd} onValueChange={datKetQuaHd}>
            <SelectTrigger id="cn-kq">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="KHONG">Chưa có</SelectItem>
              {Object.entries(NHAN_KET_QUA).map(([ma, v]) => (
                <SelectItem key={ma} value={ma}>
                  {v.nhan}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field>
          <FieldLabel htmlFor="cn-nd">Nội dung</FieldLabel>
          <Textarea id="cn-nd" rows={3} value={noiDung} onChange={(e) => datNoiDung(e.target.value)} />
        </Field>
        <Field>
          <FieldLabel htmlFor="cn-hen">Hẹn lại lúc (tuỳ chọn)</FieldLabel>
          <Input id="cn-hen" type="datetime-local" value={henLai} onChange={(e) => datHenLai(e.target.value)} />
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={() => onDoiMo(false)} disabled={ketQua.isLoading}>
            Huỷ
          </Button>
          <Button
            disabled={ketQua.isLoading}
            onClick={async () => {
              try {
                await capNhat({
                  id: h.id,
                  than: {
                    outcome: ketQuaHd === 'KHONG' ? null : (ketQuaHd as KetQuaHoatDong),
                    content: noiDung.trim() || null,
                    ...(henLai ? { remindAt: new Date(henLai).toISOString() } : {}),
                  },
                }).unwrap()
                toast.success('Đã cập nhật hoạt động.')
                onDoiMo(false)
              } catch (loi) {
                toast.error(laLoiTruyVan(loi) ? loi.message : 'Không cập nhật được.')
              }
            }}
          >
            Lưu
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
