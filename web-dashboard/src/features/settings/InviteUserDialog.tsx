import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useMoiNguoiDungMutation } from '@/api/platform'
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

/** Hai vai trò, đúng như `platform.roles` của ERD — không phải bốn như mô tả SCR010 ban đầu. */
const luocDo = z.object({
  email: z.email('Địa chỉ thư không hợp lệ.'),
  fullName: z.string().max(200, 'Tối đa 200 ký tự.').optional(),
  roleCode: z.enum(['TENANT_ADMIN', 'AGENT']),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR009 — mời người dùng mới. Mẫu M3.
 *
 * Không có ô mật khẩu: người được mời tự đặt sau khi xác thực thư. Quản trị viên đặt hộ mật khẩu
 * là tạo ra một mật khẩu mà hai người cùng biết.
 */
export function InviteUserDialog({ mo, onDoiMo }: { mo: boolean; onDoiMo: (m: boolean) => void }) {
  const [moi, ketQua] = useMoiNguoiDungMutation()

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { email: '', fullName: '', roleCode: 'AGENT' },
  })

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Mời người dùng mới"
      moTa="Người được mời nhận thư kích hoạt và tự đặt mật khẩu."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Gửi lời mời"
      onGui={async (giaTri) => {
        await moi({ ...giaTri, fullName: giaTri.fullName || null }).unwrap()
        toast.success(`Đã gửi lời mời tới ${giaTri.email}`)
        // Reset **sau khi** thành công, không phải lúc đóng — đóng nhầm mà mất hết là lỗi khó tha
        form.reset()
        onDoiMo(false)
      }}
    >
      <Field>
        <FieldLabel htmlFor="moi-email">Địa chỉ thư</FieldLabel>
        <Input
          id="moi-email"
          type="email"
          placeholder="ten@congty.vn"
          autoComplete="off"
          {...form.register('email')}
        />
        <FieldError errors={[form.formState.errors.email]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="moi-ten">Họ tên</FieldLabel>
        <Input id="moi-ten" placeholder="Không bắt buộc" {...form.register('fullName')} />
        <FieldDescription>Để trống thì người được mời tự điền khi kích hoạt.</FieldDescription>
        <FieldError errors={[form.formState.errors.fullName]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="moi-vai-tro">Vai trò</FieldLabel>
        <Select
          value={form.watch('roleCode')}
          onValueChange={(v) => form.setValue('roleCode', v as GiaTri['roleCode'])}
        >
          <SelectTrigger id="moi-vai-tro">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="AGENT">Nhân viên chăm sóc</SelectItem>
            <SelectItem value="TENANT_ADMIN">Quản trị doanh nghiệp</SelectItem>
          </SelectContent>
        </Select>
        <FieldDescription>
          Quản trị doanh nghiệp thấy được cấu hình, hoá đơn và nhật ký kiểm toán.
        </FieldDescription>
      </Field>
    </FormDialog>
  )
}
