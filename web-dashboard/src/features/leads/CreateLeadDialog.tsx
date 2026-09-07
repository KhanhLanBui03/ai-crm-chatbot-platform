import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useDanhSachKhachHangQuery } from '@/api/contacts'
import { useDanhSachNguoiDungQuery } from '@/api/platform'
import { useTaoLeadMutation } from '@/api/sales'
import { FormDialog } from '@/components/layout/FormDialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTriHoan } from '@/hooks/useTriHoan'

const luocDo = z
  .object({
    contactId: z.string().min(1, 'Chọn khách hàng.'),
    interestedProduct: z.string().max(200).optional(),
    budgetMin: z.number().min(0).optional(),
    budgetMax: z.number().min(0).optional(),
    urgency: z.enum(['LOW', 'MEDIUM', 'HIGH']),
    ownerUserId: z.string().optional(),
  })
  .refine((v) => v.budgetMin == null || v.budgetMax == null || v.budgetMin <= v.budgetMax, {
    message: 'Ngân sách tối thiểu phải nhỏ hơn hoặc bằng tối đa.',
    path: ['budgetMax'],
  })

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR043 — tạo cơ hội tiềm năng thủ công. Mẫu M3.
 *
 * Không có ô nhập điểm. Điểm do mô hình chấm từ tín hiệu hội thoại; lead nhập tay chưa có hội
 * thoại nên **chưa có điểm**, và màn hình nói thẳng điều đó thay vì đặt tạm một con số.
 */
export function CreateLeadDialog({ mo, onDoiMo }: { mo: boolean; onDoiMo: (m: boolean) => void }) {
  const dieuHuong = useNavigate()
  const [tao, ketQua] = useTaoLeadMutation()
  const [oTim, datOTim] = useState('')
  const tuKhoa = useTriHoan(oTim)
  const khachHang = useDanhSachKhachHangQuery({ tuKhoa }, { skip: tuKhoa.length < 2 })
  const nguoiDung = useDanhSachNguoiDungQuery({ trangThai: 'ACTIVE' })

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { contactId: '', interestedProduct: '', urgency: 'MEDIUM', ownerUserId: '' },
  })

  const daChon = khachHang.data?.items.find((k) => k.id === form.watch('contactId'))

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Tạo cơ hội tiềm năng"
      moTa="Dùng khi cơ hội đến từ ngoài kênh chat — gọi điện, gặp trực tiếp, hội chợ."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Tạo cơ hội"
      onGui={async (giaTri) => {
        const kq = await tao({
          contactId: giaTri.contactId,
          interestedProduct: giaTri.interestedProduct || null,
          budgetMin: giaTri.budgetMin ?? null,
          budgetMax: giaTri.budgetMax ?? null,
          urgency: giaTri.urgency,
          ownerUserId: giaTri.ownerUserId || null,
        }).unwrap()
        toast.success('Đã tạo cơ hội tiềm năng.')
        form.reset()
        datOTim('')
        onDoiMo(false)
        dieuHuong(`/ban-hang/co-hoi-tiem-nang/${kq.id}`)
      }}
    >
      <Field>
        <FieldLabel htmlFor="ld-khach">Khách hàng</FieldLabel>
        <Input
          id="ld-khach"
          placeholder="Gõ tên, số điện thoại hoặc thư để tìm…"
          value={daChon ? (daChon.fullName ?? daChon.phone ?? '') : oTim}
          onChange={(e) => {
            datOTim(e.target.value)
            form.setValue('contactId', '')
          }}
        />
        {!daChon && tuKhoa.length >= 2 && (
          <div className="flex max-h-40 flex-col gap-1 overflow-y-auto rounded-lg border p-1">
            {khachHang.data?.items.length === 0 ? (
              <span className="text-muted-foreground px-2 py-3 text-center text-[13px]">
                Không tìm thấy. Tạo hồ sơ khách hàng trước rồi quay lại đây.
              </span>
            ) : (
              khachHang.data?.items.map((k) => (
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
              ))
            )}
          </div>
        )}
        <FieldError errors={[form.formState.errors.contactId]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="ld-sp">Sản phẩm quan tâm</FieldLabel>
        <Input
          id="ld-sp"
          placeholder="Ví dụ: 200 bộ ấm siêu tốc"
          {...form.register('interestedProduct')}
        />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="ld-min">Ngân sách từ</FieldLabel>
          <Input
            id="ld-min"
            type="number"
            min={0}
            step={100000}
            {...form.register('budgetMin', { valueAsNumber: true })}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="ld-max">đến</FieldLabel>
          <Input
            id="ld-max"
            type="number"
            min={0}
            step={100000}
            {...form.register('budgetMax', { valueAsNumber: true })}
          />
          <FieldError errors={[form.formState.errors.budgetMax]} />
        </Field>
      </div>

      <Field>
        <FieldLabel htmlFor="ld-gap">Mức gấp</FieldLabel>
        <Select
          value={form.watch('urgency')}
          onValueChange={(v) => form.setValue('urgency', v as GiaTri['urgency'])}
        >
          <SelectTrigger id="ld-gap">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="HIGH">Cao</SelectItem>
            <SelectItem value="MEDIUM">Trung bình</SelectItem>
            <SelectItem value="LOW">Thấp</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field>
        <FieldLabel htmlFor="ld-chu">Người phụ trách</FieldLabel>
        <Select
          value={form.watch('ownerUserId') ?? ''}
          onValueChange={(v) => form.setValue('ownerUserId', v)}
        >
          <SelectTrigger id="ld-chu">
            <SelectValue placeholder="Để trống thì quy tắc phân công tự chia" />
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

      <Alert>
        <AlertDescription>
          Cơ hội nhập tay <strong>chưa có điểm tiềm năng</strong>: mô hình chấm điểm chạy trên tín
          hiệu của hội thoại, mà cơ hội này chưa gắn với hội thoại nào. Điểm sẽ xuất hiện nếu sau
          đó khách nhắn qua một trong các kênh.
        </AlertDescription>
      </Alert>
    </FormDialog>
  )
}
