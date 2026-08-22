import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useThemGhiChuMutation } from '@/api/contacts'
import { FormDialog } from '@/components/layout/FormDialog'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Textarea } from '@/components/ui/textarea'

const luocDo = z.object({
  content: z.string().min(1, 'Ghi chú không được để trống.').max(4000, 'Tối đa 4000 ký tự.'),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR028 — thêm ghi chú nội bộ. Mẫu M3.
 *
 * `conversationId` truyền vào khi ghi chú được mở từ cạnh một hội thoại: cùng một nội dung nhưng
 * biết nó sinh ra trong ngữ cảnh nào thì sau này lần lại được. Mở từ hồ sơ khách thì để trống.
 */
export function AddNoteDialog({
  mo,
  onDoiMo,
  contactId,
  conversationId,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
  contactId: string
  conversationId?: string | null
}) {
  const [them, ketQua] = useThemGhiChuMutation()
  const form = useForm<GiaTri>({ resolver: zodResolver(luocDo), defaultValues: { content: '' } })

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Thêm ghi chú"
      moTa="Chỉ nhân viên đọc được. Khách hàng không bao giờ thấy ghi chú nội bộ."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Lưu ghi chú"
      onGui={async (giaTri) => {
        await them({ contactId, conversationId: conversationId ?? null, ...giaTri }).unwrap()
        toast.success('Đã lưu ghi chú.')
        form.reset()
        onDoiMo(false)
      }}
    >
      <Field>
        <FieldLabel htmlFor="gc-noi-dung">Nội dung</FieldLabel>
        <Textarea
          id="gc-noi-dung"
          rows={5}
          className="resize-none"
          placeholder="Ví dụ: khách chỉ rảnh cuối tuần, đã hẹn kỹ thuật gọi lại sáng thứ Bảy."
          {...form.register('content')}
        />
        <FieldDescription>
          Tránh chép số giấy tờ hay số thẻ vào đây. Máy chủ tự đánh dấu ghi chú có dạng số dài là
          &quot;có dữ liệu cá nhân&quot;, và những ghi chú đó sẽ bị xoá khi khách yêu cầu xoá dữ
          liệu (Nghị định 13).
        </FieldDescription>
        <FieldError errors={[form.formState.errors.content]} />
      </Field>
    </FormDialog>
  )
}
