import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useThemKenhMutation } from '@/api/channels'
import { FormDialog } from '@/components/layout/FormDialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const luocDo = z.object({
  channelType: z.enum(['ZALO', 'FACEBOOK']),
  externalAccountId: z.string().min(1, 'Bắt buộc nhập.'),
  accountName: z.string().max(200).optional(),
  accessToken: z.string().min(1, 'Bắt buộc nhập.'),
})

type GiaTri = z.infer<typeof luocDo>

const HUONG_DAN: Record<GiaTri['channelType'], { idNhan: string; idGoiY: string; noi: string }> = {
  ZALO: {
    idNhan: 'ID của Official Account',
    idGoiY: '3358274190028471',
    noi: 'Lấy ở Zalo OA Manager → Thông tin OA. Mã truy cập lấy ở tab Ứng dụng.',
  },
  FACEBOOK: {
    idNhan: 'ID của Trang',
    idGoiY: '102938475610293',
    noi: 'Lấy ở Meta Business Suite → Cài đặt Trang. Mã truy cập cần quyền pages_messaging.',
  },
}

/**
 * SCR017 — kết nối một kênh mới. Mẫu M3.
 *
 * Kết nối xong kênh ở trạng thái `PENDING_VERIFY` chứ không phải `ACTIVE`: webhook phải bắt tay
 * được thì mới có tin nhắn về. Cho nó `ACTIVE` ngay là hứa một điều chưa chắc đúng, rồi người
 * dùng ngồi chờ tin nhắn không bao giờ tới.
 */
export function ConnectChannelDialog({
  mo,
  onDoiMo,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const [them, ketQua] = useThemKenhMutation()

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { channelType: 'ZALO', externalAccountId: '', accountName: '', accessToken: '' },
  })

  const loai = form.watch('channelType')
  const huongDan = HUONG_DAN[loai]

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Kết nối kênh"
      moTa="Sau khi kết nối, kênh cần xác minh webhook rồi mới nhận được tin nhắn."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Kết nối"
      onGui={async (giaTri) => {
        await them(giaTri).unwrap()
        toast.success('Đã kết nối. Bấm "Xác minh" để hoàn tất bắt tay webhook.')
        form.reset()
        onDoiMo(false)
      }}
    >
      <Field>
        <FieldLabel htmlFor="kenh-loai">Nền tảng</FieldLabel>
        <Select
          value={loai}
          onValueChange={(v) => form.setValue('channelType', v as GiaTri['channelType'])}
        >
          <SelectTrigger id="kenh-loai">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ZALO">Zalo OA</SelectItem>
            <SelectItem value="FACEBOOK">Facebook Messenger</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field>
        <FieldLabel htmlFor="kenh-id">{huongDan.idNhan}</FieldLabel>
        <Input
          id="kenh-id"
          placeholder={huongDan.idGoiY}
          className="font-mono"
          {...form.register('externalAccountId')}
        />
        <FieldDescription>{huongDan.noi}</FieldDescription>
        <FieldError errors={[form.formState.errors.externalAccountId]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="kenh-ten">Tên hiển thị</FieldLabel>
        <Input id="kenh-ten" placeholder="Không bắt buộc" {...form.register('accountName')} />
      </Field>

      <Field>
        <FieldLabel htmlFor="kenh-token">Mã truy cập</FieldLabel>
        <Input
          id="kenh-token"
          type="password"
          autoComplete="off"
          {...form.register('accessToken')}
        />
        <FieldError errors={[form.formState.errors.accessToken]} />
      </Field>

      <Alert>
        <AlertDescription>
          Mã truy cập được mã hoá trước khi lưu và <strong>không bao giờ hiện lại</strong>. Mất mã
          thì cấp lại trên cổng của nền tảng rồi kết nối lại — đó là cách duy nhất.
        </AlertDescription>
      </Alert>
    </FormDialog>
  )
}
