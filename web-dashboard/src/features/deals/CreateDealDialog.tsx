import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useDanhSachKhachHangQuery } from '@/api/contacts'
import { useDanhSachNguoiDungQuery } from '@/api/platform'
import { useDanhSachPheuQuery, useTaoDealMutation } from '@/api/sales'
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
import { useTriHoan } from '@/hooks/useTriHoan'

/** Ô số để trống là "chưa rõ", không phải 0 và không phải NaN. */
const so = (v: unknown) => (v === '' || v == null || Number.isNaN(v) ? undefined : Number(v))

const luocDo = z.object({
  contactId: z.string().min(1, 'Chọn khách hàng.'),
  title: z.string().trim().min(1, 'Đặt tên cho deal.').max(200, 'Tối đa 200 ký tự.'),
  stageId: z.string().min(1, 'Chọn giai đoạn.'),
  amount: z.number().min(0, 'Không âm.').optional(),
  expectedCloseDate: z.string().optional(),
  ownerUserId: z.string().optional(),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR046 — tạo deal thủ công (UC034, nguồn MANUAL): khách cũ mua thêm, không cần qua lead. Deal từ
 * lead đi qua nút "Chuyển thành Deal" ở trang lead. Người phụ trách mặc định là người tạo; chỉ quản
 * trị viên chọn người khác (máy chủ cũng chặn).
 */
export function CreateDealDialog({ mo, onDoiMo }: { mo: boolean; onDoiMo: (m: boolean) => void }) {
  const dieuHuong = useNavigate()
  const [tao, ketQua] = useTaoDealMutation()
  const pheu = useDanhSachPheuQuery()
  const laQuanTri = useAppSelector((s) => s.auth.nguoiDung?.roleCode === 'TENANT_ADMIN')
  const nguoiDung = useDanhSachNguoiDungQuery({ trangThai: 'ACTIVE' }, { skip: !laQuanTri || !mo })
  const [oTim, datOTim] = useState('')
  const tuKhoa = useTriHoan(oTim)
  const khachHang = useDanhSachKhachHangQuery({ tuKhoa }, { skip: tuKhoa.length < 2 })

  const giaiDoan = (pheu.data?.[0]?.stages ?? []).filter((g) => !g.isWon && !g.isLost)

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { contactId: '', title: '', stageId: '', ownerUserId: '' },
  })

  // Mỗi lần mở là một lần nhập mới, giai đoạn mặc định là cột đầu
  useEffect(() => {
    if (!mo) return
    form.reset({ contactId: '', title: '', stageId: giaiDoan[0]?.id ?? '', ownerUserId: '' })
    datOTim('')
    ketQua.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mo, giaiDoan[0]?.id])

  const daChon = khachHang.data?.items.find((k) => k.id === form.watch('contactId'))
  const gdDangChon = giaiDoan.find((g) => g.id === form.watch('stageId'))
  const canSoTien = (gdDangChon?.requiredFields ?? []).includes('amount')

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Tạo deal"
      moTa="Dùng cho khách cũ mua thêm. Khách mới thì tạo lead rồi bấm &quot;Chuyển thành Deal&quot;."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Tạo deal"
      onGui={async (giaTri) => {
        if (!pheu.data?.[0]) return
        try {
          const kq = await tao({
            contactId: giaTri.contactId,
            pipelineId: pheu.data[0].id,
            stageId: giaTri.stageId,
            title: giaTri.title.trim(),
            amount: giaTri.amount ?? null,
            expectedCloseDate: giaTri.expectedCloseDate || null,
            ownerUserId: giaTri.ownerUserId || null,
          }).unwrap()
          toast.success('Đã tạo deal.')
          onDoiMo(false)
          dieuHuong(`/ban-hang/pheu/${kq.id}`)
        } catch {
          // lỗi hiện trong hộp thoại qua `loi`
        }
      }}
    >
      <Field>
        <FieldLabel htmlFor="dl-khach">Khách hàng</FieldLabel>
        <Input
          id="dl-khach"
          placeholder="Gõ tên, số điện thoại hoặc thư để tìm…"
          value={daChon ? (daChon.fullName ?? daChon.phone ?? '') : oTim}
          onChange={(e) => {
            datOTim(e.target.value)
            form.setValue('contactId', '')
          }}
        />
        {!daChon && tuKhoa.length >= 2 && (
          <div className="flex max-h-40 flex-col gap-1 overflow-y-auto rounded-lg border p-1">
            {khachHang.data?.items.length === 0 && (
              <span className="text-muted-foreground px-2 py-3 text-center text-[13px]">
                Không tìm thấy — tạo hồ sơ ở Khách hàng trước.
              </span>
            )}
            {khachHang.data?.items.map((k) => (
              <button
                key={k.id}
                type="button"
                className="hover:bg-muted flex flex-col rounded-md px-2 py-1.5 text-left"
                onClick={() => form.setValue('contactId', k.id, { shouldValidate: true })}
              >
                <span className="text-[13px] font-medium">{k.fullName ?? 'Chưa có tên'}</span>
                <span className="text-muted-foreground text-xs">
                  {[k.phone, k.email].filter(Boolean).join(' · ')}
                </span>
              </button>
            ))}
          </div>
        )}
        <FieldError errors={[form.formState.errors.contactId]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="dl-ten">Tên deal</FieldLabel>
        <Input id="dl-ten" placeholder="Ví dụ: Đơn 200 bộ ấm siêu tốc" {...form.register('title')} />
        <FieldError errors={[form.formState.errors.title]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="dl-gd">Giai đoạn</FieldLabel>
        <Select
          value={form.watch('stageId') ?? ''}
          onValueChange={(v) => form.setValue('stageId', v, { shouldValidate: true })}
        >
          <SelectTrigger id="dl-gd">
            <SelectValue placeholder="Chọn giai đoạn" />
          </SelectTrigger>
          <SelectContent>
            {giaiDoan.map((g) => (
              <SelectItem key={g.id} value={g.id}>
                {g.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <FieldError errors={[form.formState.errors.stageId]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="dl-tien">Giá trị (VND)</FieldLabel>
        <Input
          id="dl-tien"
          type="number"
          min={0}
          step={100000}
          {...form.register('amount', { setValueAs: so })}
        />
        <FieldError errors={[form.formState.errors.amount]} />
        {canSoTien && (
          <FieldDescription>
            Giai đoạn &quot;{gdDangChon?.name}&quot; bắt buộc có số tiền — máy chủ sẽ từ chối nếu
            để trống.
          </FieldDescription>
        )}
      </Field>

      <Field>
        <FieldLabel htmlFor="dl-han">Dự kiến chốt</FieldLabel>
        <Input id="dl-han" type="date" className="max-w-44" {...form.register('expectedCloseDate')} />
      </Field>

      {laQuanTri && (
        <Field>
          <FieldLabel htmlFor="dl-chu">Người phụ trách</FieldLabel>
          <Select
            value={form.watch('ownerUserId') || 'toi'}
            onValueChange={(v) => form.setValue('ownerUserId', v === 'toi' ? '' : v)}
          >
            <SelectTrigger id="dl-chu">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="toi">Tôi phụ trách</SelectItem>
              {nguoiDung.data?.items.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.fullName ?? u.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )}
    </FormDialog>
  )
}
