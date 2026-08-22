import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useDanhSachKhachHangQuery } from '@/api/contacts'
import { useDanhSachNguoiDungQuery } from '@/api/platform'
import { useDanhSachPheuQuery, useTaoDealMutation } from '@/api/sales'
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

const luocDo = z.object({
  contactId: z.string().min(1, 'Chọn khách hàng.'),
  title: z.string().min(1, 'Đặt tên cho cơ hội.').max(200),
  stageId: z.string().min(1, 'Chọn giai đoạn.'),
  amount: z.number().min(0).optional(),
  expectedCloseDate: z.string().optional(),
  ownerUserId: z.string().optional(),
})

type GiaTri = z.infer<typeof luocDo>

/** SCR046 — tạo cơ hội bán hàng. Mẫu M3. */
export function CreateDealDialog({ mo, onDoiMo }: { mo: boolean; onDoiMo: (m: boolean) => void }) {
  const dieuHuong = useNavigate()
  const [tao, ketQua] = useTaoDealMutation()
  const pheu = useDanhSachPheuQuery()
  const nguoiDung = useDanhSachNguoiDungQuery({ trangThai: 'ACTIVE' })
  const [oTim, datOTim] = useState('')
  const tuKhoa = useTriHoan(oTim)
  const khachHang = useDanhSachKhachHangQuery({ tuKhoa }, { skip: tuKhoa.length < 2 })

  const giaiDoan = (pheu.data?.[0]?.stages ?? []).filter((g) => !g.isWon && !g.isLost)

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { contactId: '', title: '', stageId: '', ownerUserId: '' },
  })

  const daChon = khachHang.data?.items.find((k) => k.id === form.watch('contactId'))
  const gdDangChon = giaiDoan.find((g) => g.id === form.watch('stageId'))
  const canSoTien = (gdDangChon?.requiredFields ?? []).includes('amount')

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Tạo cơ hội bán hàng"
      moTa="Cơ hội gắn với một khách hàng và nằm trong một giai đoạn của phễu."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Tạo cơ hội"
      onGui={async (giaTri) => {
        if (!pheu.data?.[0]) return
        const kq = await tao({
          contactId: giaTri.contactId,
          pipelineId: pheu.data[0].id,
          stageId: giaTri.stageId,
          title: giaTri.title,
          amount: giaTri.amount ?? null,
          expectedCloseDate: giaTri.expectedCloseDate || null,
          ownerUserId: giaTri.ownerUserId || null,
        }).unwrap()
        toast.success('Đã tạo cơ hội bán hàng.')
        form.reset()
        datOTim('')
        onDoiMo(false)
        dieuHuong(`/ban-hang/pheu/${kq.id}`)
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
        <FieldLabel htmlFor="dl-ten">Tên cơ hội</FieldLabel>
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
        <FieldLabel htmlFor="dl-tien">Giá trị cơ hội</FieldLabel>
        <Input
          id="dl-tien"
          type="number"
          min={0}
          step={100000}
          {...form.register('amount', { valueAsNumber: true })}
        />
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

      <Field>
        <FieldLabel htmlFor="dl-chu">Người phụ trách</FieldLabel>
        <Select
          value={form.watch('ownerUserId') ?? ''}
          onValueChange={(v) => form.setValue('ownerUserId', v)}
        >
          <SelectTrigger id="dl-chu">
            <SelectValue placeholder="Chưa giao cho ai" />
          </SelectTrigger>
          <SelectContent>
            {nguoiDung.data?.items.map((u) => (
              <SelectItem key={u.id} value={u.id}>
                {u.fullName ?? u.email}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
    </FormDialog>
  )
}
