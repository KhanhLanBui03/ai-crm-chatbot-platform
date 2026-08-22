import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useTaoQuyTacMutation } from '@/api/conversations'
import { useDanhSachNguoiDungQuery } from '@/api/platform'
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

const luocDo = z
  .object({
    name: z.string().min(1, 'Đặt tên cho quy tắc.').max(100),
    appliesTo: z.enum(['CONVERSATION', 'LEAD']),
    strategy: z.enum(['LEAST_BUSY', 'ROUND_ROBIN', 'FIXED_USER']),
    channelType: z.enum(['tat-ca', 'WEB_WIDGET', 'ZALO', 'FACEBOOK']),
    targetUserId: z.string().optional(),
    // `z.number()` chứ không phải `z.coerce.number()`: coerce trong zod 4 làm kiểu đầu vào thành
    // `unknown` và phá luôn kiểu của `zodResolver`. Chuyển đổi để `valueAsNumber` của
    // react-hook-form lo, đúng chỗ của nó.
    priority: z.number().int().min(0).max(1000),
  })
  // Chiến lược "người cố định" mà không chọn người thì quy tắc không làm được gì, và máy chủ sẽ
  // lặng lẽ bỏ qua nó — kiểu lỗi tệ nhất: cấu hình trông như đang chạy nhưng không chạy.
  .refine((v) => v.strategy !== 'FIXED_USER' || Boolean(v.targetUserId), {
    message: 'Chọn người nhận khi dùng chiến lược người cố định.',
    path: ['targetUserId'],
  })

type GiaTri = z.infer<typeof luocDo>

/** SCR023 — tạo quy tắc phân công. Mẫu M3. */
export function CreateRuleDialog({
  mo,
  onDoiMo,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const [tao, ketQua] = useTaoQuyTacMutation()
  const nguoiDung = useDanhSachNguoiDungQuery({ trangThai: 'ACTIVE' })

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: {
      name: '',
      appliesTo: 'CONVERSATION',
      strategy: 'LEAST_BUSY',
      channelType: 'tat-ca',
      targetUserId: '',
      priority: 50,
    },
  })

  const chienLuoc = form.watch('strategy')

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Tạo quy tắc phân công"
      moTa="Quy tắc ưu tiên cao được duyệt trước; quy tắc khớp đầu tiên thắng."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Tạo quy tắc"
      onGui={async (giaTri) => {
        await tao({
          name: giaTri.name,
          appliesTo: giaTri.appliesTo,
          strategy: giaTri.strategy,
          channelType: giaTri.channelType === 'tat-ca' ? null : giaTri.channelType,
          targetUserId: giaTri.strategy === 'FIXED_USER' ? (giaTri.targetUserId ?? null) : null,
          maxConcurrent: null,
          priority: giaTri.priority,
          isActive: true,
        }).unwrap()
        toast.success('Đã tạo quy tắc.')
        form.reset()
        onDoiMo(false)
      }}
    >
      <Field>
        <FieldLabel htmlFor="qt-ten">Tên quy tắc</FieldLabel>
        <Input id="qt-ten" placeholder="Ví dụ: Zalo → người ít việc nhất" {...form.register('name')} />
        <FieldError errors={[form.formState.errors.name]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="qt-ap-dung">Áp dụng cho</FieldLabel>
        <Select
          value={form.watch('appliesTo')}
          onValueChange={(v) => form.setValue('appliesTo', v as GiaTri['appliesTo'])}
        >
          <SelectTrigger id="qt-ap-dung">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="CONVERSATION">Hội thoại</SelectItem>
            <SelectItem value="LEAD">Cơ hội tiềm năng</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field>
        <FieldLabel htmlFor="qt-kenh">Chỉ áp dụng cho kênh</FieldLabel>
        <Select
          value={form.watch('channelType')}
          onValueChange={(v) => form.setValue('channelType', v as GiaTri['channelType'])}
        >
          <SelectTrigger id="qt-kenh">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tat-ca">Mọi kênh</SelectItem>
            <SelectItem value="WEB_WIDGET">Web Widget</SelectItem>
            <SelectItem value="ZALO">Zalo</SelectItem>
            <SelectItem value="FACEBOOK">Facebook</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field>
        <FieldLabel htmlFor="qt-chien-luoc">Cách chia</FieldLabel>
        <Select
          value={chienLuoc}
          onValueChange={(v) => form.setValue('strategy', v as GiaTri['strategy'])}
        >
          <SelectTrigger id="qt-chien-luoc">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="LEAST_BUSY">Người ít việc nhất</SelectItem>
            <SelectItem value="ROUND_ROBIN">Chia lượt</SelectItem>
            <SelectItem value="FIXED_USER">Người cố định</SelectItem>
          </SelectContent>
        </Select>
        <FieldDescription>
          {chienLuoc === 'LEAST_BUSY'
            ? 'Nhìn số hội thoại đang giữ. Công bằng theo tải thật, nhưng người trả lời nhanh sẽ nhận nhiều hơn.'
            : chienLuoc === 'ROUND_ROBIN'
              ? 'Lần lượt từng người, không nhìn tải. Đều tuyệt đối, nhưng có thể dồn việc cho người đang bận.'
              : 'Luôn giao cho một người. Dùng cho nhóm khách đặc thù, không dùng làm mặc định.'}
        </FieldDescription>
      </Field>

      {chienLuoc === 'FIXED_USER' && (
        <Field>
          <FieldLabel htmlFor="qt-nguoi">Người nhận</FieldLabel>
          {/* `value` luôn là chuỗi, kể cả khi chưa chọn gì. Truyền `undefined` lúc đầu rồi
              truyền chuỗi sau là chuyển Select từ không kiểm soát sang có kiểm soát giữa chừng —
              React cảnh báo, và giá trị có thể mất khi component render lại. */}
          <Select
            value={form.watch('targetUserId') ?? ''}
            onValueChange={(v) => form.setValue('targetUserId', v, { shouldValidate: true })}
          >
            <SelectTrigger id="qt-nguoi">
              <SelectValue placeholder="Chọn người" />
            </SelectTrigger>
            <SelectContent>
              {nguoiDung.data?.items.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.fullName ?? u.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldError errors={[form.formState.errors.targetUserId]} />
        </Field>
      )}

      <Field>
        <FieldLabel htmlFor="qt-uu-tien">Ưu tiên</FieldLabel>
        <Input
          id="qt-uu-tien"
          type="number"
          min={0}
          max={1000}
          className="max-w-28"
          {...form.register('priority', { valueAsNumber: true })}
        />
        <FieldDescription>
          Số lớn hơn được duyệt trước. Quy tắc hẹp (theo thẻ, theo khách đặc thù) nên để cao hơn
          quy tắc rộng (theo kênh), nếu không quy tắc rộng sẽ nuốt hết.
        </FieldDescription>
        <FieldError errors={[form.formState.errors.priority]} />
      </Field>
    </FormDialog>
  )
}
