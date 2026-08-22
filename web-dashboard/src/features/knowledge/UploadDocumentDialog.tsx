import { zodResolver } from '@hookform/resolvers/zod'
import { FileUp, ShieldAlert, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useTaiLenTaiLieuMutation } from '@/api/knowledge'
import { FormDialog } from '@/components/layout/FormDialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { coTep } from '@/features/knowledge/nhan'
import { cn } from '@/utils/cn'

const DUOI_NHAN = ['.pdf', '.docx', '.txt', '.md', '.html'] as const
const CO_TOI_DA = 20 * 1024 * 1024

const luocDo = z.object({
  title: z.string().min(3, 'Tiêu đề cần ít nhất 3 ký tự.').max(300, 'Tiêu đề tối đa 300 ký tự.'),
  description: z.string().max(500, 'Mô tả tối đa 500 ký tự.').optional(),
  language: z.enum(['vi', 'en']),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR029 — tải lên tài liệu tri thức. Màn chữ ký, dựng trên khung M3.
 *
 * Vùng thả tệp là phần phải tự dựng: `FormDialog` lo tiêu đề, vùng lỗi và hai nút chân, còn kéo
 * thả thì không có mẫu nào phủ. Tệp **không** nằm trong lược đồ zod — react-hook-form giữ giá trị
 * chuỗi, còn `File` là đối tượng có trạng thái riêng; ép nó vào biểu mẫu chỉ để lấy một dòng kiểm
 * tra là đổi lấy rắc rối ở mọi lần reset.
 *
 * Tiêu đề tự điền từ tên tệp nhưng vẫn sửa được: "chinh-sach-bao-hanh-2026.pdf" là tên tệp, không
 * phải tên tài liệu, mà tên tài liệu mới là thứ hiện ra trong trích dẫn khách nhìn thấy.
 */
export function UploadDocumentDialog({
  mo,
  onDoiMo,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const dieuHuong = useNavigate()
  const [taiLen, ketQua] = useTaiLenTaiLieuMutation()
  const [tep, datTep] = useState<File | null>(null)
  const [loiTep, datLoiTep] = useState<string | null>(null)
  const [dangKeo, datDangKeo] = useState(false)
  const oTep = useRef<HTMLInputElement>(null)

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { title: '', description: '', language: 'vi' },
  })

  function nhanTep(t: File | null) {
    if (!t) return
    const duoi = `.${t.name.split('.').pop()?.toLowerCase() ?? ''}`
    if (!DUOI_NHAN.includes(duoi as (typeof DUOI_NHAN)[number])) {
      datTep(null)
      datLoiTep(`Định dạng ${duoi} không được hỗ trợ. Nhận ${DUOI_NHAN.join(', ')}.`)
      return
    }
    if (t.size > CO_TOI_DA) {
      datTep(null)
      datLoiTep(`Tệp ${coTep(t.size)} vượt quá giới hạn 20 MB. Tách nhỏ rồi tải lên từng phần.`)
      return
    }
    datLoiTep(null)
    datTep(t)
    if (!form.getValues('title')) {
      // Bỏ phần mở rộng và đổi gạch nối thành khoảng trắng — vẫn để người dùng sửa lại
      form.setValue('title', t.name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' '), {
        shouldValidate: true,
      })
    }
  }

  function dongLai() {
    datTep(null)
    datLoiTep(null)
    form.reset()
    onDoiMo(false)
  }

  return (
    <FormDialog
      mo={mo}
      onDoiMo={(m) => (m ? onDoiMo(true) : dongLai())}
      tieuDe="Tải lên tài liệu tri thức"
      moTa="Tài liệu được chia đoạn, tạo vector nhúng rồi lập chỉ mục. Tác tử AI chỉ trả lời dựa trên những gì có ở đây."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Tải lên và nạp"
      rong="rong"
      onGui={async (giaTri) => {
        if (!tep) {
          datLoiTep('Chọn một tệp trước khi tải lên.')
          return
        }
        const kq = await taiLen({
          tep,
          title: giaTri.title,
          description: giaTri.description || null,
          language: giaTri.language,
        }).unwrap()
        toast.success('Đã nhận tài liệu. Quá trình nạp đang chạy nền.')
        datTep(null)
        form.reset()
        onDoiMo(false)
        dieuHuong(`/tri-thuc/tai-lieu/${kq.id}/tien-do`)
      }}
    >
      <Field>
        <FieldLabel htmlFor="tl-tep">Tệp tài liệu</FieldLabel>
        {tep ? (
          <div className="flex items-center gap-3 rounded-lg border p-3">
            <div className="bg-secondary text-secondary-foreground flex size-9 shrink-0 items-center justify-center rounded-md">
              <FileUp className="size-4" />
            </div>
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-[13px] font-medium">{tep.name}</span>
              <span className="text-muted-foreground text-xs tabular-nums">{coTep(tep.size)}</span>
            </div>
            <Button type="button" variant="ghost" size="icon" onClick={() => datTep(null)}>
              <X />
              <span className="sr-only">Bỏ tệp đã chọn</span>
            </Button>
          </div>
        ) : (
          <div
            role="button"
            tabIndex={0}
            onClick={() => oTep.current?.click()}
            onKeyDown={(su) => {
              if (su.key === 'Enter' || su.key === ' ') oTep.current?.click()
            }}
            onDragOver={(su) => {
              su.preventDefault()
              datDangKeo(true)
            }}
            onDragLeave={() => datDangKeo(false)}
            onDrop={(su) => {
              su.preventDefault()
              datDangKeo(false)
              nhanTep(su.dataTransfer.files[0] ?? null)
            }}
            className={cn(
              'flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-8 text-center transition-colors',
              dangKeo ? 'border-primary bg-primary/5' : 'hover:bg-muted/50',
            )}
          >
            <FileUp className="text-muted-foreground size-5" />
            <span className="text-[13px] font-medium">Kéo tệp vào đây hoặc bấm để chọn</span>
            <span className="text-muted-foreground text-xs">
              {DUOI_NHAN.join(' · ')} — tối đa 20 MB
            </span>
          </div>
        )}
        <input
          id="tl-tep"
          ref={oTep}
          type="file"
          className="hidden"
          accept={DUOI_NHAN.join(',')}
          onChange={(su) => nhanTep(su.target.files?.[0] ?? null)}
        />
        {loiTep && <FieldError errors={[{ message: loiTep }]} />}
      </Field>

      <Field>
        <FieldLabel htmlFor="tl-tieu-de">Tiêu đề tài liệu</FieldLabel>
        <Input id="tl-tieu-de" placeholder="Chính sách bảo hành 2026" {...form.register('title')} />
        <FieldDescription>
          Đây là tên hiện trong trích dẫn mà khách nhìn thấy, không phải tên tệp.
        </FieldDescription>
        <FieldError errors={[form.formState.errors.title]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="tl-mo-ta">Mô tả</FieldLabel>
        <Textarea
          id="tl-mo-ta"
          rows={2}
          placeholder="Một câu về phạm vi nội dung — giúp người sau biết tài liệu này trả lời được gì."
          {...form.register('description')}
        />
        <FieldError errors={[form.formState.errors.description]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="tl-ngon-ngu">Ngôn ngữ</FieldLabel>
        <Select
          value={form.watch('language')}
          onValueChange={(v) => form.setValue('language', v as GiaTri['language'])}
        >
          <SelectTrigger id="tl-ngon-ngu">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="vi">Tiếng Việt</SelectItem>
            <SelectItem value="en">Tiếng Anh</SelectItem>
          </SelectContent>
        </Select>
        <FieldDescription>
          Quyết định bộ tách từ khi chia đoạn. Chọn sai thì đoạn bị cắt giữa câu và truy hồi kém hẳn.
        </FieldDescription>
      </Field>

      <Alert>
        <ShieldAlert />
        <AlertDescription>
          Nội dung tài liệu đi vào lời nhắc gửi mô hình, nên nó là một bề mặt tiêm chỉ thị (T3).
          Hệ thống luôn coi mọi câu trong tài liệu là <strong>dữ liệu</strong>, không phải mệnh
          lệnh — nhưng vẫn chỉ nên tải lên tài liệu từ nguồn nội bộ tin được.
        </AlertDescription>
      </Alert>
    </FormDialog>
  )
}
