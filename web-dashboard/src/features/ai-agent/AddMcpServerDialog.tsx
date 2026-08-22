import { zodResolver } from '@hookform/resolvers/zod'
import { ShieldAlert } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useThemMayChuMcpMutation } from '@/api/ai-agent'
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

/**
 * Phiên bản đặc tả được **ghim**, không phải "mới nhất".
 *
 * Máy chủ MCP là mã của bên thứ ba; để nó tự quyết định nói phiên bản nào là để một bản cập nhật
 * ngoài tầm kiểm soát đổi hình dạng dữ liệu đi vào lời nhắc gửi mô hình.
 */
const PHIEN_BAN = ['2025-06-18', '2025-03-26'] as const

const luocDo = z
  .object({
    name: z.string().min(2, 'Tên máy chủ cần ít nhất 2 ký tự.').max(120),
    endpointUrl: z
      .string()
      .url('Địa chỉ phải là một URL hợp lệ.')
      .refine((v) => v.startsWith('https://'), 'Chỉ nhận HTTPS — bí mật xác thực đi qua đường này.'),
    transport: z.enum(['STREAMABLE_HTTP', 'HTTP_SSE']),
    specVersion: z.enum(PHIEN_BAN),
    authType: z.enum(['NONE', 'BEARER', 'API_KEY', 'OAUTH2']),
    secret: z.string().optional(),
    timeoutMs: z.number().int().min(1_000, 'Tối thiểu 1.000 ms.').max(30_000, 'Tối đa 30.000 ms.'),
    maxCallsPerConversation: z
      .number()
      .int()
      .min(1, 'Ít nhất 1 lời gọi.')
      .max(50, 'Tối đa 50 lời gọi mỗi hội thoại.'),
  })
  .refine((v) => v.authType === 'NONE' || Boolean(v.secret?.trim()), {
    message: 'Kiểu xác thực này cần một bí mật.',
    path: ['secret'],
  })

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR038 — thêm máy chủ MCP. Mẫu M3.
 *
 * Máy chủ mới **không** ở trạng thái hoạt động ngay: nó là `PENDING` cho tới khi bắt tay thành
 * công ở SCR037. Công cụ dò được cũng mặc định **tắt** — mở sẵn một công cụ ghi chỉ vì vừa nối
 * máy chủ là bỏ qua đúng bước kiểm soát mà cả cơ chế này dựng lên để có.
 */
export function AddMcpServerDialog({
  mo,
  onDoiMo,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const [them, ketQua] = useThemMayChuMcpMutation()

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: {
      name: '',
      endpointUrl: 'https://',
      transport: 'STREAMABLE_HTTP',
      specVersion: '2025-06-18',
      authType: 'BEARER',
      secret: '',
      timeoutMs: 5_000,
      maxCallsPerConversation: 10,
    },
  })

  const kieuXacThuc = form.watch('authType')

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Thêm máy chủ MCP"
      moTa="Máy chủ cung cấp công cụ cho tác tử AI. Sau khi thêm, bấm Bắt tay để dò danh sách công cụ."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Thêm máy chủ"
      rong="rong"
      onGui={async (giaTri) => {
        await them({
          ...giaTri,
          secret: giaTri.authType === 'NONE' ? null : (giaTri.secret ?? null),
        }).unwrap()
        toast.success('Đã thêm máy chủ. Bấm Bắt tay để dò danh sách công cụ.')
        form.reset()
        onDoiMo(false)
      }}
    >
      <Field>
        <FieldLabel htmlFor="mcp-ten">Tên máy chủ</FieldLabel>
        <Input id="mcp-ten" placeholder="Kho vận Cát Tường" {...form.register('name')} />
        <FieldError errors={[form.formState.errors.name]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="mcp-url">Địa chỉ đầu cuối</FieldLabel>
        <Input id="mcp-url" placeholder="https://mcp.cattuong.vn/kho-van" {...form.register('endpointUrl')} />
        <FieldError errors={[form.formState.errors.endpointUrl]} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="mcp-transport">Giao thức truyền</FieldLabel>
          <Select
            value={form.watch('transport')}
            onValueChange={(v) => form.setValue('transport', v as GiaTri['transport'])}
          >
            <SelectTrigger id="mcp-transport">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="STREAMABLE_HTTP">Streamable HTTP</SelectItem>
              <SelectItem value="HTTP_SSE">HTTP + SSE</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        <Field>
          <FieldLabel htmlFor="mcp-spec">Phiên bản đặc tả</FieldLabel>
          <Select
            value={form.watch('specVersion')}
            onValueChange={(v) => form.setValue('specVersion', v as GiaTri['specVersion'])}
          >
            <SelectTrigger id="mcp-spec">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PHIEN_BAN.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldDescription>Ghim cứng. Máy chủ không hỗ trợ thì từ chối kết nối.</FieldDescription>
        </Field>
      </div>

      <Field>
        <FieldLabel htmlFor="mcp-auth">Kiểu xác thực</FieldLabel>
        <Select
          value={kieuXacThuc}
          onValueChange={(v) => form.setValue('authType', v as GiaTri['authType'])}
        >
          <SelectTrigger id="mcp-auth">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="BEARER">Bearer token</SelectItem>
            <SelectItem value="API_KEY">Khoá API</SelectItem>
            <SelectItem value="OAUTH2">OAuth 2</SelectItem>
            <SelectItem value="NONE">Không xác thực</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      {kieuXacThuc !== 'NONE' && (
        <Field>
          <FieldLabel htmlFor="mcp-secret">Bí mật xác thực</FieldLabel>
          <Input
            id="mcp-secret"
            type="password"
            autoComplete="new-password"
            placeholder="Dán token hoặc khoá API"
            {...form.register('secret')}
          />
          <FieldDescription>
            Mã hoá trước khi ghi và không bao giờ trả lại qua API. Muốn đổi thì nhập giá trị mới.
          </FieldDescription>
          <FieldError errors={[form.formState.errors.secret]} />
        </Field>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="mcp-timeout">Hạn chờ mỗi lời gọi (ms)</FieldLabel>
          <Input
            id="mcp-timeout"
            type="number"
            min={1_000}
            max={30_000}
            step={500}
            {...form.register('timeoutMs', { valueAsNumber: true })}
          />
          <FieldError errors={[form.formState.errors.timeoutMs]} />
        </Field>

        <Field>
          <FieldLabel htmlFor="mcp-max">Số lời gọi tối đa mỗi hội thoại</FieldLabel>
          <Input
            id="mcp-max"
            type="number"
            min={1}
            max={50}
            {...form.register('maxCallsPerConversation', { valueAsNumber: true })}
          />
          <FieldDescription>Chặn vòng lặp gọi công cụ không kiểm soát.</FieldDescription>
          <FieldError errors={[form.formState.errors.maxCallsPerConversation]} />
        </Field>
      </div>

      <Alert>
        <ShieldAlert />
        <AlertDescription>
          Mô tả công cụ do máy chủ này cung cấp sẽ đi thẳng vào lời nhắc gửi mô hình, nên nó là một
          bề mặt tiêm chỉ thị (T4). Chỉ nối máy chủ do doanh nghiệp kiểm soát, và duyệt từng công
          cụ ở sổ đăng ký trước khi bật.
        </AlertDescription>
      </Alert>
    </FormDialog>
  )
}
