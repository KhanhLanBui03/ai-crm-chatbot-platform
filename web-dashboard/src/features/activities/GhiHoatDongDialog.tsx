import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useDanhSachKhachHangQuery } from '@/api/contacts'
import { useDanhSachNguoiDungQuery } from '@/api/platform'
import { useDanhSachDealQuery, useDanhSachLeadQuery, useGhiNhanHoatDongMutation } from '@/api/sales'
import { useAppSelector } from '@/app/store/hooks'
import { FormDialog } from '@/components/layout/FormDialog'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { NHAN_KET_QUA, NHAN_LOAI_HOAT_DONG } from '@/features/leads/nhan'
import { useTriHoan } from '@/hooks/useTriHoan'
import type { KetQuaHoatDong, LoaiHoatDong } from '@/types/schema'

const luocDo = z
  .object({
    contactId: z.string().min(1, 'Chọn khách hàng.'),
    dich: z.string(),
    type: z.enum(['CALL', 'MEETING', 'QUOTE', 'EMAIL', 'NOTE']),
    subject: z.string().max(200, 'Tối đa 200 ký tự.'),
    content: z.string().max(5000, 'Tối đa 5.000 ký tự.'),
    outcome: z.string(),
    remindAt: z.string(),
    remindUserId: z.string(),
  })
  .superRefine((v, ctx) => {
    if (!v.subject.trim() && !v.content.trim()) {
      ctx.addIssue({ code: 'custom', path: ['subject'], message: 'Nhập tiêu đề hoặc nội dung.' })
    }
    if (v.remindAt && new Date(v.remindAt).getTime() <= Date.now()) {
      ctx.addIssue({ code: 'custom', path: ['remindAt'], message: 'Giờ nhắc phải ở tương lai.' })
    }
    if (v.outcome === 'RESCHEDULED' && !v.remindAt) {
      ctx.addIssue({ code: 'custom', path: ['remindAt'], message: 'Kết quả "Hẹn lại" cần đặt giờ nhắc.' })
    }
  })

type GiaTri = z.infer<typeof luocDo>

/** Nơi hoạt động được gắn: biết sẵn (tab Lead/Deal/hồ sơ khách) hoặc chọn trong hộp thoại (trang chung). */
export interface DichGhi {
  contactId: string
  contactName: string
  leadId?: string
  dealId?: string
}

/**
 * UC035 — ghi một hoạt động (gọi điện, gặp mặt, báo giá, email, ghi chú), tuỳ chọn đặt nhắc việc.
 *
 * - Mở từ tab Lead/Deal: gắn sẵn lead/deal đó. Mở từ hồ sơ khách: gắn hồ sơ khách, chọn được lead/deal
 *   của khách. Mở từ trang Hoạt động chung: chọn khách trước.
 * - Không có ô "thời điểm thực hiện": ghi lúc nào là lúc đó (máy chủ đặt `now()`).
 * - Nhắc việc mặc định cho chính mình; chỉ quản trị viên giao cho người khác (máy chủ cũng chặn).
 */
export function GhiHoatDongDialog({
  mo,
  onDoiMo,
  dich,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
  dich?: DichGhi
}) {
  const laQuanTri = useAppSelector((s) => s.auth.nguoiDung?.roleCode === 'TENANT_ADMIN')
  const [ghi, ketQua] = useGhiNhanHoatDongMutation()
  const [oTim, datOTim] = useState('')
  const tuKhoa = useTriHoan(oTim)
  const khachHang = useDanhSachKhachHangQuery({ tuKhoa }, { skip: !mo || !!dich || tuKhoa.length < 2 })
  const nguoiDung = useDanhSachNguoiDungQuery({ trangThai: 'ACTIVE' }, { skip: !mo || !laQuanTri })

  const form = useForm<GiaTri>({ resolver: zodResolver(luocDo) })
  const contactId = form.watch('contactId')
  // Đã gắn sẵn lead/deal thì không cần chọn; còn lại cho chọn lead/deal của đúng khách đó
  const canChonDich = mo && !!contactId && !dich?.leadId && !dich?.dealId
  const leads = useDanhSachLeadQuery({ khachHangId: contactId, trang: 0 }, { skip: !canChonDich })
  const deals = useDanhSachDealQuery({ khachHangId: contactId }, { skip: !canChonDich })
  const daChon = khachHang.data?.items.find((k) => k.id === contactId)

  useEffect(() => {
    if (!mo) return
    form.reset({
      contactId: dich?.contactId ?? '',
      dich: dich?.dealId ? `deal:${dich.dealId}` : dich?.leadId ? `lead:${dich.leadId}` : 'khach',
      type: 'CALL',
      subject: '',
      content: '',
      outcome: 'KHONG',
      remindAt: '',
      remindUserId: '',
    })
    datOTim('')
    ketQua.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mo, dich?.contactId, dich?.leadId, dich?.dealId])

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Ghi hoạt động"
      moTa={dich ? `Khách hàng: ${dich.contactName}` : 'Ghi lại việc đã làm với khách — cả nhóm sẽ thấy.'}
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Ghi lại"
      onGui={async (g) => {
        const [loaiDich, idDich] = g.dich.split(':')
        try {
          await ghi({
            contactId: g.contactId,
            leadId: loaiDich === 'lead' ? idDich : null,
            dealId: loaiDich === 'deal' ? idDich : null,
            type: g.type as LoaiHoatDong,
            subject: g.subject.trim() || null,
            content: g.content.trim() || null,
            outcome: g.outcome === 'KHONG' ? null : (g.outcome as KetQuaHoatDong),
            remindAt: g.remindAt ? new Date(g.remindAt).toISOString() : null,
            remindUserId: g.remindAt && g.remindUserId ? g.remindUserId : null,
          }).unwrap()
          toast.success(g.remindAt ? 'Đã ghi hoạt động và đặt nhắc việc.' : 'Đã ghi hoạt động.')
          onDoiMo(false)
        } catch {
          // lỗi hiện trong hộp thoại qua `loi`
        }
      }}
    >
      {!dich && (
        <Field>
          <FieldLabel htmlFor="hd-khach">Khách hàng</FieldLabel>
          <Input
            id="hd-khach"
            placeholder="Gõ tên hoặc số điện thoại để tìm…"
            value={daChon ? (daChon.fullName ?? daChon.phone ?? '') : oTim}
            onChange={(e) => {
              datOTim(e.target.value)
              form.setValue('contactId', '')
              form.setValue('dich', 'khach')
            }}
          />
          {!daChon && tuKhoa.length >= 2 && (
            <div className="flex max-h-40 flex-col gap-1 overflow-y-auto rounded-lg border p-1">
              {khachHang.data?.items.length === 0 && (
                <span className="text-muted-foreground px-2 py-3 text-center text-[13px]">Không tìm thấy.</span>
              )}
              {khachHang.data?.items.map((k) => (
                <button
                  key={k.id}
                  type="button"
                  className="hover:bg-muted flex flex-col rounded-md px-2 py-1.5 text-left"
                  onClick={() => form.setValue('contactId', k.id, { shouldValidate: true })}
                >
                  <span className="text-[13px] font-medium">{k.fullName ?? 'Chưa có tên'}</span>
                  <span className="text-muted-foreground text-xs">{[k.phone, k.email].filter(Boolean).join(' · ')}</span>
                </button>
              ))}
            </div>
          )}
          <FieldError errors={[form.formState.errors.contactId]} />
        </Field>
      )}

      {canChonDich && (
        <Field>
          <FieldLabel htmlFor="hd-dich">Gắn vào</FieldLabel>
          <Select value={form.watch('dich')} onValueChange={(v) => form.setValue('dich', v)}>
            <SelectTrigger id="hd-dich">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="khach">Chỉ hồ sơ khách</SelectItem>
              {deals.data?.items.map((d) => (
                <SelectItem key={d.id} value={`deal:${d.id}`}>
                  Deal: {d.title}
                  {d.status !== 'OPEN' ? ' (đã đóng)' : ''}
                </SelectItem>
              ))}
              {leads.data?.items.map((l) => (
                <SelectItem key={l.id} value={`lead:${l.id}`}>
                  Lead: {l.interestedProduct ?? 'chưa rõ sản phẩm'}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="hd-loai">Loại</FieldLabel>
          <Select value={form.watch('type')} onValueChange={(v) => form.setValue('type', v as GiaTri['type'])}>
            <SelectTrigger id="hd-loai">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(NHAN_LOAI_HOAT_DONG).map(([ma, nhan]) => (
                <SelectItem key={ma} value={ma}>
                  {nhan}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field>
          <FieldLabel htmlFor="hd-kq">Kết quả</FieldLabel>
          <Select value={form.watch('outcome')} onValueChange={(v) => form.setValue('outcome', v)}>
            <SelectTrigger id="hd-kq">
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
      </div>

      <Field>
        <FieldLabel htmlFor="hd-tieu-de">Tiêu đề</FieldLabel>
        <Input id="hd-tieu-de" placeholder="Ví dụ: Gọi tư vấn gói Pro" {...form.register('subject')} />
        <FieldError errors={[form.formState.errors.subject]} />
      </Field>
      <Field>
        <FieldLabel htmlFor="hd-noi-dung">Nội dung</FieldLabel>
        <Textarea id="hd-noi-dung" rows={3} placeholder="Khách nói gì, hẹn gì…" {...form.register('content')} />
        <FieldError errors={[form.formState.errors.content]} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="hd-nhac">Nhắc việc lúc</FieldLabel>
          <Input id="hd-nhac" type="datetime-local" {...form.register('remindAt')} />
          <FieldError errors={[form.formState.errors.remindAt]} />
        </Field>
        {laQuanTri && form.watch('remindAt') && (
          <Field>
            <FieldLabel htmlFor="hd-nguoi-nhac">Nhắc ai</FieldLabel>
            <Select
              value={form.watch('remindUserId') || 'toi'}
              onValueChange={(v) => form.setValue('remindUserId', v === 'toi' ? '' : v)}
            >
              <SelectTrigger id="hd-nguoi-nhac">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="toi">Tôi</SelectItem>
                {nguoiDung.data?.items.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.fullName ?? u.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        )}
      </div>
      <FieldDescription>Có giờ nhắc thì việc hiện ở "Việc của tôi" và số đỏ trên menu Hoạt động.</FieldDescription>
    </FormDialog>
  )
}
