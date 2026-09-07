import { zodResolver } from '@hookform/resolvers/zod'
import { AlertTriangle } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useTaoKhachHangMutation } from '@/api/contacts'
import { FormDialog } from '@/components/layout/FormDialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { KhachHang } from '@/types/schema'

const luocDo = z
  .object({
    fullName: z.string().max(200).optional(),
    phone: z.string().max(30).optional(),
    email: z.union([z.email('Địa chỉ thư không hợp lệ.'), z.literal('')]).optional(),
    primaryChannel: z.enum(['WEB_WIDGET', 'ZALO', 'FACEBOOK', 'PHONE']),
    consentGranted: z.boolean(),
  })
  // Một hồ sơ không có cách nào liên hệ lại là một hồ sơ vô dụng. Ràng buộc ở mức lược đồ chứ
  // không ở từng ô, vì nó nói về quan hệ giữa hai ô.
  .refine((v) => Boolean(v.phone?.trim() || v.email?.trim()), {
    message: 'Phải có ít nhất số điện thoại hoặc địa chỉ thư.',
    path: ['phone'],
  })

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR027 — tạo khách hàng thủ công. Mẫu M3.
 *
 * Trùng số điện thoại hay thư thì **cảnh báo rồi vẫn tạo**, không chặn. Chặn cứng nghe an toàn
 * nhưng làm luồng hợp nhất (SCR025) không chạy được — muốn hợp nhất thì hai hồ sơ phải cùng tồn
 * tại. Ai là người mới, ai là người cũ đổi số, chỉ nhân viên biết.
 */
export function CreateContactDialog({
  mo,
  onDoiMo,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const dieuHuong = useNavigate()
  const [tao, ketQua] = useTaoKhachHangMutation()
  const [trung, datTrung] = useState<KhachHang[]>([])

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: {
      fullName: '',
      phone: '',
      email: '',
      primaryChannel: 'PHONE',
      consentGranted: false,
    },
  })

  return (
    <FormDialog
      mo={mo}
      onDoiMo={(m) => {
        onDoiMo(m)
        if (!m) datTrung([])
      }}
      tieuDe="Thêm khách hàng"
      moTa="Dùng khi khách gọi điện hoặc gặp trực tiếp — các kênh chat tự tạo hồ sơ."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Tạo hồ sơ"
      onGui={async (giaTri) => {
        const kq = await tao({
          ...giaTri,
          fullName: giaTri.fullName || null,
          phone: giaTri.phone || null,
          email: giaTri.email || null,
          consentSource: giaTri.consentGranted ? 'AGENT_MANUAL' : undefined,
        }).unwrap()

        if (kq.duplicateCandidates.length > 0) {
          // Đã tạo rồi mới cảnh báo — và giữ hộp thoại mở để nhân viên thấy danh sách trùng
          datTrung(kq.duplicateCandidates)
          toast.warning(
            `Đã tạo hồ sơ, nhưng có ${kq.duplicateCandidates.length} hồ sơ trùng liên hệ.`,
          )
          return
        }
        toast.success('Đã tạo hồ sơ khách hàng.')
        form.reset()
        onDoiMo(false)
        dieuHuong(`/khach-hang/${kq.contact.id}`)
      }}
    >
      {trung.length > 0 && (
        <Alert>
          <AlertTriangle />
          <AlertDescription>
            <span className="block font-medium">Có hồ sơ trùng liên hệ</span>
            <ul className="mt-1 flex flex-col gap-0.5">
              {trung.map((k) => (
                <li key={k.id}>
                  <button
                    type="button"
                    className="underline underline-offset-2"
                    onClick={() => {
                      onDoiMo(false)
                      dieuHuong(`/khach-hang/${k.id}`)
                    }}
                  >
                    {k.fullName ?? 'Chưa có tên'} · {k.phone ?? k.email}
                  </button>
                </li>
              ))}
            </ul>
            <span className="mt-1 block">
              Hồ sơ mới vẫn đã được tạo. Nếu đây là cùng một người thì mở hồ sơ và hợp nhất.
            </span>
          </AlertDescription>
        </Alert>
      )}

      <Field>
        <FieldLabel htmlFor="kh-ten">Họ tên</FieldLabel>
        <Input id="kh-ten" placeholder="Nguyễn Văn A" {...form.register('fullName')} />
        <FieldError errors={[form.formState.errors.fullName]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="kh-dt">Điện thoại</FieldLabel>
        <Input id="kh-dt" placeholder="0903 000 000" {...form.register('phone')} />
        <FieldError errors={[form.formState.errors.phone]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="kh-mail">Thư điện tử</FieldLabel>
        <Input id="kh-mail" type="email" placeholder="a@example.com" {...form.register('email')} />
        <FieldError errors={[form.formState.errors.email]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="kh-kenh">Kênh chính</FieldLabel>
        <Select
          value={form.watch('primaryChannel')}
          onValueChange={(v) => form.setValue('primaryChannel', v as GiaTri['primaryChannel'])}
        >
          <SelectTrigger id="kh-kenh">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="PHONE">Nhập tay / điện thoại</SelectItem>
            <SelectItem value="WEB_WIDGET">Web Widget</SelectItem>
            <SelectItem value="ZALO">Zalo</SelectItem>
            <SelectItem value="FACEBOOK">Facebook</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field>
        <label className="flex items-start gap-2.5">
          <Checkbox
            checked={form.watch('consentGranted')}
            onCheckedChange={(v) => form.setValue('consentGranted', v === true)}
            className="mt-0.5"
          />
          <span className="flex flex-col gap-0.5">
            <span className="text-[13px] font-medium">Khách đã đồng ý xử lý dữ liệu cá nhân</span>
            <FieldDescription>
              Chỉ tích khi khách thật sự đã đồng ý. Nghị định 13/2023/NĐ-CP: chưa đồng ý thì không
              được dùng dữ liệu cho tiếp thị, và ô này được ghi vào nhật ký kiểm toán.
            </FieldDescription>
          </span>
        </label>
      </Field>
    </FormDialog>
  )
}
