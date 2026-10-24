import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useSuaTaiLieuMutation } from '@/api/knowledge'
import { FormDialog } from '@/components/layout/FormDialog'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { TaiLieu } from '@/types/schema'

// Cùng giới hạn với hộp thoại tải lên và với java-core (`UpdateDocumentRequest`): 255 khớp
// varchar(255) của V202 — đặc tả ghi 300 (ADR-0020 quyết định 3).
const luocDo = z.object({
  title: z.string().trim().min(3, 'Tiêu đề cần ít nhất 3 ký tự.').max(255, 'Tiêu đề tối đa 255 ký tự.'),
  description: z.string().max(500, 'Mô tả tối đa 500 ký tự.'),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * UC020 bước 5 — sửa siêu dữ liệu của một tài liệu. Mẫu M3.
 *
 * Chỉ tiêu đề và mô tả. Ngôn ngữ không sửa được ở đây vì nó quyết định cách tách từ lúc nạp — đổi
 * nó là phải nạp lại. Sửa xong chỉ mục vector **giữ nguyên**: số đoạn không đổi.
 *
 * Trùng tiêu đề với một tài liệu khác cùng phiên bản thì máy chủ trả 422 `INVALID_METADATA` và câu
 * lỗi hiện ngay trong hộp thoại (vùng lỗi của `FormDialog`), hộp thoại không đóng.
 */
export function EditDocumentDialog({
  taiLieu,
  mo,
  onDoiMo,
}: {
  taiLieu: TaiLieu
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const [sua, ketQua] = useSuaTaiLieuMutation()
  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { title: taiLieu.title, description: taiLieu.description ?? '' },
  })

  // Mỗi lần mở lại thì nạp giá trị hiện tại — tài liệu có thể đã đổi từ lần sửa trước
  useEffect(() => {
    if (mo) {
      form.reset({ title: taiLieu.title, description: taiLieu.description ?? '' })
      ketQua.reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mo, taiLieu.id])

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Sửa thông tin tài liệu"
      moTa="Chỉ đổi tiêu đề và mô tả. Các đoạn đã lập chỉ mục giữ nguyên, không phải nạp lại."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Lưu thay đổi"
      onGui={async (giaTri) => {
        await sua({
          id: taiLieu.id,
          title: giaTri.title.trim(),
          description: giaTri.description.trim() || null,
        }).unwrap()
        toast.success('Đã cập nhật thông tin tài liệu.')
        onDoiMo(false)
      }}
    >
      <Field>
        <FieldLabel htmlFor="sua-tieu-de">Tiêu đề tài liệu</FieldLabel>
        <Input id="sua-tieu-de" {...form.register('title')} />
        <FieldDescription>Tên hiện trong trích dẫn mà khách nhìn thấy.</FieldDescription>
        <FieldError errors={[form.formState.errors.title]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="sua-mo-ta">Mô tả</FieldLabel>
        <Textarea id="sua-mo-ta" rows={3} {...form.register('description')} />
        <FieldDescription>Để trống là xoá mô tả.</FieldDescription>
        <FieldError errors={[form.formState.errors.description]} />
      </Field>
    </FormDialog>
  )
}
