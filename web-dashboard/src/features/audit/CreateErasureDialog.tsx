import { zodResolver } from '@hookform/resolvers/zod'
import { Search, X } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { useTaoYeuCauXoaMutation } from '@/api/audit'
import { useDanhSachKhachHangQuery } from '@/api/contacts'
import { FormDialog } from '@/components/layout/FormDialog'
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
import { useTriHoan } from '@/hooks/useTriHoan'
import { NHAN_NGUON_YEU_CAU } from '@/features/audit/nhan'

const luocDo = z.object({
  contactId: z.string().min(1, 'Chọn khách hàng cần xoá dữ liệu.'),
  legalBasis: z
    .string()
    .trim()
    .min(1, 'Căn cứ pháp lý là trường bắt buộc.')
    .max(2000, 'Tối đa 2.000 ký tự.'),
  requestedBy: z.enum(['CONTACT', 'STAFF']),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * UC041 bước 1–2 — tạo yêu cầu xoá dữ liệu cá nhân. Mẫu M3.
 *
 * Căn cứ pháp lý là ô bắt buộc chứ không phải ghi chú: thiếu nó thì yêu cầu không có cơ sở để thực thi
 * và cũng không có gì để đưa vào biên bản. Tạo xong mở thẳng trang yêu cầu — bước kế tiếp (xác minh danh
 * tính) làm được ở đó hoặc ngay trên dòng của danh sách.
 */
export function CreateErasureDialog({ mo, onDoiMo }: { mo: boolean; onDoiMo: (m: boolean) => void }) {
  const dieuHuong = useNavigate()
  const [tao, ketQua] = useTaoYeuCauXoaMutation()
  const [oTim, datOTim] = useState('')
  const [tenDaChon, datTenDaChon] = useState<string | null>(null)
  const tuKhoa = useTriHoan(oTim)
  const khachHang = useDanhSachKhachHangQuery({ tuKhoa }, { skip: tuKhoa.length < 2 || !mo })

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { contactId: '', legalBasis: '', requestedBy: 'CONTACT' },
  })
  const daChon = form.watch('contactId')

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Tạo yêu cầu xoá dữ liệu cá nhân"
      moTa="Yêu cầu được tạo ở trạng thái chờ. Quản trị viên phải xác minh danh tính khách trước khi thực thi."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Tạo yêu cầu"
      rong="rong"
      onGui={async (giaTri) => {
        const kq = await tao(giaTri).unwrap()
        toast.success('Đã tạo yêu cầu xoá — bước tiếp theo là xác minh danh tính.')
        // Reset sau khi gửi thành công, không phải lúc đóng (web-dashboard CLAUDE.md mục 13)
        form.reset()
        datOTim('')
        datTenDaChon(null)
        onDoiMo(false)
        dieuHuong(`/kiem-toan/yeu-cau-xoa/${kq.id}`)
      }}
    >
      <Field>
        <FieldLabel htmlFor="xoa-tim-khach">Khách hàng</FieldLabel>
        {daChon ? (
          <div className="flex items-center gap-2 rounded-lg border px-2.5 py-1.5">
            <span className="flex-1 truncate text-[13px] font-medium">{tenDaChon}</span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                form.setValue('contactId', '')
                datTenDaChon(null)
              }}
            >
              <X />
              Chọn khách khác
            </Button>
          </div>
        ) : (
          <>
            <div className="relative">
              <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
              <Input
                id="xoa-tim-khach"
                className="pl-8"
                placeholder="Tìm theo tên, số điện thoại hoặc thư…"
                autoComplete="off"
                value={oTim}
                onChange={(e) => datOTim(e.target.value)}
              />
            </div>
            {tuKhoa.length >= 2 && (
              <div className="flex max-h-48 flex-col gap-0.5 overflow-y-auto rounded-lg border p-1">
                {khachHang.data?.items.length === 0 ? (
                  <span className="text-muted-foreground px-2 py-2 text-center text-[13px]">
                    Không tìm thấy khách hàng nào khớp.
                  </span>
                ) : (
                  khachHang.data?.items.map((k) => (
                    <button
                      key={k.id}
                      type="button"
                      onClick={() => {
                        form.setValue('contactId', k.id, { shouldValidate: true })
                        datTenDaChon(k.fullName ?? 'Khách chưa có tên')
                      }}
                      className="hover:bg-muted flex flex-col rounded-md px-2 py-1.5 text-left transition-colors"
                    >
                      <span className="text-[13px] font-medium">
                        {k.fullName ?? 'Khách chưa có tên'}
                      </span>
                      <span className="text-muted-foreground text-xs">
                        {[k.phone, k.email].filter(Boolean).join(' · ') ||
                          'Không có thông tin liên hệ'}
                      </span>
                    </button>
                  ))
                )}
              </div>
            )}
          </>
        )}
        <FieldError errors={[form.formState.errors.contactId]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="xoa-nguon">Nguồn yêu cầu</FieldLabel>
        <Select
          value={form.watch('requestedBy')}
          onValueChange={(v) => form.setValue('requestedBy', v as GiaTri['requestedBy'])}
        >
          <SelectTrigger id="xoa-nguon">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="CONTACT">{NHAN_NGUON_YEU_CAU.CONTACT}</SelectItem>
            <SelectItem value="STAFF">{NHAN_NGUON_YEU_CAU.STAFF}</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field>
        <FieldLabel htmlFor="xoa-can-cu">Căn cứ pháp lý</FieldLabel>
        <Textarea
          id="xoa-can-cu"
          rows={3}
          placeholder="Vd. Điều 16 Nghị định 13/2023/NĐ-CP — khách gửi thư yêu cầu xoá ngày 12/11/2026"
          {...form.register('legalBasis')}
        />
        <FieldDescription>Bắt buộc. Được ghi vào hồ sơ yêu cầu và biên bản sau khi xoá.</FieldDescription>
        <FieldError errors={[form.formState.errors.legalBasis]} />
      </Field>
    </FormDialog>
  )
}
