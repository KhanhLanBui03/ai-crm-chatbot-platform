import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useChuyenLeadThanhDealMutation } from '@/api/sales'
import { FormDialog } from '@/components/layout/FormDialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import type { LeadChiTiet } from '@/types/schema'

const so = (v: unknown) => (v === '' || v == null || Number.isNaN(v) ? null : Number(v))

const luocDo = z.object({
  title: z.string().trim().min(1, 'Nhập tên deal.').max(200, 'Tối đa 200 ký tự.'),
  amount: z.number().min(0, 'Không âm.').nullable(),
  expectedCloseDate: z.string(),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * UC033 — chuyển lead thành deal. Hỏi đúng ba thứ đã chốt: tên (điền sẵn "Khách – Sản phẩm"), giá trị
 * (gợi ý = ngân sách tối đa của lead) và ngày dự kiến chốt. Deal luôn vào cột đầu của phễu mặc định;
 * người phụ trách = người phụ trách lead — máy chủ quyết, hộp thoại không hỏi.
 */
export function ChuyenDealDialog({
  lead,
  mo,
  onDoiMo,
}: {
  lead: LeadChiTiet
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const dieuHuong = useNavigate()
  const [chuyen, ketQua] = useChuyenLeadThanhDealMutation()
  const form = useForm<GiaTri>({ resolver: zodResolver(luocDo) })

  useEffect(() => {
    if (!mo) return
    form.reset({
      title: lead.interestedProduct ? `${lead.contactName} – ${lead.interestedProduct}` : lead.contactName,
      amount: lead.budgetMax ?? lead.budgetMin ?? null,
      expectedCloseDate: '',
    })
    ketQua.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mo])

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Chuyển thành Deal"
      moTa="Deal mới vào cột đầu tiên của phễu bán hàng. Lead sẽ khoá lại và trỏ sang deal này."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Tạo deal"
      onGui={async (g) => {
        try {
          const kq = await chuyen({
            id: lead.id,
            title: g.title.trim(),
            amount: g.amount,
            expectedCloseDate: g.expectedCloseDate || null,
          }).unwrap()
          onDoiMo(false)
          toast.success('Đã chuyển thành deal.')
          // Khách đã có deal khác đang mở: không chặn (một khách mua nhiều lần), nhưng phải nói ra
          for (const canhBao of kq.warnings) toast.warning(canhBao)
          dieuHuong(`/ban-hang/pheu/${kq.deal.id}`)
        } catch {
          // lỗi hiện trong hộp thoại qua `loi`
        }
      }}
    >
      <Field>
        <FieldLabel htmlFor="cd-ten">Tên deal</FieldLabel>
        <Input id="cd-ten" {...form.register('title')} />
        <FieldError errors={[form.formState.errors.title]} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="cd-tien">Giá trị (VND)</FieldLabel>
          <Input
            id="cd-tien"
            type="number"
            min={0}
            step={100000}
            {...form.register('amount', { setValueAs: so })}
          />
          <FieldError errors={[form.formState.errors.amount]} />
        </Field>
        <Field>
          <FieldLabel htmlFor="cd-ngay">Dự kiến chốt</FieldLabel>
          <Input id="cd-ngay" type="date" {...form.register('expectedCloseDate')} />
        </Field>
      </div>
      {lead.budgetMax != null && (
        <Alert>
          <AlertDescription>Giá trị gợi ý lấy từ ngân sách tối đa khách đã nêu — sửa lại nếu đã báo giá khác.</AlertDescription>
        </Alert>
      )}
    </FormDialog>
  )
}
