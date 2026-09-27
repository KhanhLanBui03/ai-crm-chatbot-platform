import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useCapNhatNguoiDungMutation } from '@/api/platform'
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
import type { NguoiDung } from '@/types/schema'

const luocDo = z.object({
  fullName: z.string().min(1, 'Vui lòng nhập họ tên.').max(200, 'Tối đa 200 ký tự.'),
  roleCode: z.enum(['TENANT_ADMIN', 'AGENT']),
})

type GiaTri = z.infer<typeof luocDo>

interface EditUserDialogProps {
  nguoiDung: NguoiDung | null
  mo: boolean
  onDoiMo: (mo: boolean) => void
}

export function EditUserDialog({ nguoiDung, mo, onDoiMo }: EditUserDialogProps) {
  const [capNhat, ketQua] = useCapNhatNguoiDungMutation()

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: {
      fullName: '',
      roleCode: 'AGENT',
    },
  })

  useEffect(() => {
    if (mo && nguoiDung) {
      const role = nguoiDung.roleCode === 'TENANT_ADMIN' ? 'TENANT_ADMIN' : 'AGENT'
      form.reset({
        fullName: nguoiDung.fullName ?? '',
        roleCode: role,
      })
    }
  }, [mo, nguoiDung])

  if (!nguoiDung) return null

  return (
    <FormDialog<GiaTri>
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Chỉnh sửa thông tin thành viên"
      moTa={`Cập nhật vai trò và thông tin của ${nguoiDung.email}`}
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Lưu thay đổi"
      onGui={async (giaTri) => {
        await capNhat({
          id: nguoiDung.id,
          fullName: giaTri.fullName,
          roleCode: giaTri.roleCode,
        }).unwrap()
        toast.success(`Đã cập nhật thông tin thành viên ${nguoiDung.email}`)
        onDoiMo(false)
      }}
    >
      <Field>
        <FieldLabel htmlFor="sua-email">Địa chỉ thư</FieldLabel>
        <Input id="sua-email" type="email" value={nguoiDung.email} disabled className="bg-muted cursor-not-allowed opacity-75" />
        <FieldDescription>Địa chỉ email được cố định và không thể sửa đổi.</FieldDescription>
      </Field>

      <Field>
        <FieldLabel htmlFor="sua-ten">Họ tên</FieldLabel>
        <Input id="sua-ten" placeholder="Nhập họ và tên..." {...form.register('fullName')} />
        <FieldError errors={[form.formState.errors.fullName]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="sua-vai-tro">Vai trò</FieldLabel>
        <Select
          value={form.watch('roleCode')}
          onValueChange={(v) => form.setValue('roleCode', v as GiaTri['roleCode'])}
        >
          <SelectTrigger id="sua-vai-tro">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="AGENT">Nhân viên chăm sóc</SelectItem>
            <SelectItem value="TENANT_ADMIN">Quản trị doanh nghiệp</SelectItem>
          </SelectContent>
        </Select>
        <FieldDescription>
          Quản trị doanh nghiệp có toàn quyền quản lý thành viên, cấu hình, gói và hóa đơn.
        </FieldDescription>
      </Field>
    </FormDialog>
  )
}
