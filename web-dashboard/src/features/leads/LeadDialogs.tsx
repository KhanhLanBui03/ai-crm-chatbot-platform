import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useDanhSachNguoiDungQuery } from '@/api/platform'
import { useCapNhatLeadMutation } from '@/api/sales'
import { FormDialog } from '@/components/layout/FormDialog'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { NHAN_LY_DO_LOAI } from '@/features/leads/nhan'
import type { LeadChiTiet, LyDoLoaiLead } from '@/types/schema'

/** Các hộp thoại sửa lead của SCR042 (UC032 bước 7–8, luồng 7.x). */

const baoLoi = (loi: unknown, macDinh: string) => toast.error(laLoiTruyVan(loi) ? loi.message : macDinh)

/** UC032 7.1–7.2 — loại lead bắt buộc chọn lý do trong danh sách cố định (nhãn học của UC030). */
export function LoaiLeadDialog({
  lead,
  mo,
  onDoiMo,
}: {
  lead: LeadChiTiet
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const [capNhat, ketQua] = useCapNhatLeadMutation()
  const [lyDo, datLyDo] = useState<LyDoLoaiLead | ''>('')

  useEffect(() => {
    if (mo) datLyDo('')
  }, [mo])

  return (
    <Dialog open={mo} onOpenChange={onDoiMo}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Loại lead</DialogTitle>
          <DialogDescription>
            Lý do loại là dữ liệu để mô hình chấm điểm học cách nhận ra khách không tiềm năng — chọn
            đúng lý do nhất.
          </DialogDescription>
        </DialogHeader>
        <Field>
          <FieldLabel htmlFor="ly-do-loai">Lý do</FieldLabel>
          <Select value={lyDo} onValueChange={(v) => datLyDo(v as LyDoLoaiLead)}>
            <SelectTrigger id="ly-do-loai">
              <SelectValue placeholder="Chọn lý do…" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(NHAN_LY_DO_LOAI).map(([ma, nhan]) => (
                <SelectItem key={ma} value={ma}>
                  {nhan}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={() => onDoiMo(false)} disabled={ketQua.isLoading}>
            Huỷ
          </Button>
          <Button
            variant="destructive"
            disabled={!lyDo || ketQua.isLoading}
            onClick={async () => {
              try {
                await capNhat({
                  id: lead.id,
                  than: { status: 'DISQUALIFIED', disqualifyReason: lyDo as LyDoLoaiLead },
                }).unwrap()
                toast.success('Đã loại lead.')
                onDoiMo(false)
              } catch (loi) {
                baoLoi(loi, 'Không loại được lead.')
              }
            }}
          >
            Loại lead
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const so = (v: unknown) => (v === '' || v == null || Number.isNaN(v) ? null : Number(v))

const luocDoSua = z
  .object({
    interestedProduct: z.string().max(200, 'Tối đa 200 ký tự.'),
    budgetMin: z.number().min(0, 'Không âm.').nullable(),
    budgetMax: z.number().min(0, 'Không âm.').nullable(),
    urgency: z.enum(['LOW', 'MEDIUM', 'HIGH', 'KHONG']),
  })
  .refine((v) => v.budgetMin == null || v.budgetMax == null || v.budgetMin <= v.budgetMax, {
    message: 'Ngân sách tối đa phải lớn hơn hoặc bằng tối thiểu.',
    path: ['budgetMax'],
  })

type GiaTriSua = z.infer<typeof luocDoSua>

/** UC032 bước 7 — sửa thông tin cơ hội. Ô bỏ trống = xoá giá trị (PATCH gửi `null`). */
export function SuaLeadDialog({
  lead,
  mo,
  onDoiMo,
}: {
  lead: LeadChiTiet
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const [capNhat, ketQua] = useCapNhatLeadMutation()
  const form = useForm<GiaTriSua>({ resolver: zodResolver(luocDoSua) })

  useEffect(() => {
    if (!mo) return
    form.reset({
      interestedProduct: lead.interestedProduct ?? '',
      budgetMin: lead.budgetMin ?? null,
      budgetMax: lead.budgetMax ?? null,
      urgency: lead.urgency ?? 'KHONG',
    })
    ketQua.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mo])

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Sửa thông tin lead"
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      onGui={async (g) => {
        try {
          await capNhat({
            id: lead.id,
            than: {
              interestedProduct: g.interestedProduct.trim() || null,
              budgetMin: g.budgetMin,
              budgetMax: g.budgetMax,
              urgency: g.urgency === 'KHONG' ? null : g.urgency,
            },
          }).unwrap()
          toast.success('Đã lưu thông tin lead.')
          onDoiMo(false)
        } catch {
          // lỗi hiện trong hộp thoại qua `loi`
        }
      }}
    >
      <Field>
        <FieldLabel htmlFor="sl-sp">Sản phẩm quan tâm</FieldLabel>
        <Input id="sl-sp" {...form.register('interestedProduct')} />
        <FieldError errors={[form.formState.errors.interestedProduct]} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="sl-min">Ngân sách từ</FieldLabel>
          <Input id="sl-min" type="number" min={0} step={100000} {...form.register('budgetMin', { setValueAs: so })} />
          <FieldError errors={[form.formState.errors.budgetMin]} />
        </Field>
        <Field>
          <FieldLabel htmlFor="sl-max">đến</FieldLabel>
          <Input id="sl-max" type="number" min={0} step={100000} {...form.register('budgetMax', { setValueAs: so })} />
          <FieldError errors={[form.formState.errors.budgetMax]} />
        </Field>
      </div>
      <Field>
        <FieldLabel htmlFor="sl-gap">Mức gấp</FieldLabel>
        <Select
          value={form.watch('urgency')}
          onValueChange={(v) => form.setValue('urgency', v as GiaTriSua['urgency'])}
        >
          <SelectTrigger id="sl-gap">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="HIGH">Cao</SelectItem>
            <SelectItem value="MEDIUM">Trung bình</SelectItem>
            <SelectItem value="LOW">Thấp</SelectItem>
            <SelectItem value="KHONG">Chưa rõ</SelectItem>
          </SelectContent>
        </Select>
      </Field>
    </FormDialog>
  )
}

/** UC032 — chỉ quản trị viên giao lead cho người khác hoặc bỏ trống (máy chủ cũng chặn). */
export function DoiPhuTrachDialog({
  lead,
  mo,
  onDoiMo,
}: {
  lead: LeadChiTiet
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const [capNhat, ketQua] = useCapNhatLeadMutation()
  const nguoiDung = useDanhSachNguoiDungQuery({ trangThai: 'ACTIVE' }, { skip: !mo })
  const [chon, datChon] = useState('')

  useEffect(() => {
    if (mo) datChon(lead.ownerUserId ?? 'trong')
  }, [mo, lead.ownerUserId])

  return (
    <Dialog open={mo} onOpenChange={onDoiMo}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Đổi người phụ trách</DialogTitle>
          <DialogDescription>Người phụ trách là người gọi lại và theo lead này tới khi chốt.</DialogDescription>
        </DialogHeader>
        <Field>
          <FieldLabel htmlFor="doi-chu">Người phụ trách</FieldLabel>
          <Select value={chon} onValueChange={datChon}>
            <SelectTrigger id="doi-chu">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="trong">Chưa ai nhận</SelectItem>
              {nguoiDung.data?.items.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.fullName ?? u.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={() => onDoiMo(false)} disabled={ketQua.isLoading}>
            Huỷ
          </Button>
          <Button
            disabled={ketQua.isLoading || chon === (lead.ownerUserId ?? 'trong')}
            onClick={async () => {
              try {
                await capNhat({ id: lead.id, than: { ownerUserId: chon === 'trong' ? null : chon } }).unwrap()
                toast.success('Đã đổi người phụ trách.')
                onDoiMo(false)
              } catch (loi) {
                baoLoi(loi, 'Không đổi được người phụ trách.')
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
