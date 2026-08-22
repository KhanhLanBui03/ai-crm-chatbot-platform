import { zodResolver } from '@hookform/resolvers/zod'
import { ShieldAlert } from 'lucide-react'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useThucThiYeuCauXoaMutation } from '@/api/audit'
import { FormDialog } from '@/components/layout/FormDialog'
import { HangThongTin } from '@/components/layout/DetailPage'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { NHAN_THAO_TAC_XOA } from '@/features/audit/nhan'
import type { YeuCauXoaChiTiet } from '@/types/schema'

const XAC_NHAN = 'XOA VINH VIEN'

const luocDo = z.object({
  xacNhan: z.string().refine((v) => v.trim() === XAC_NHAN, `Gõ đúng "${XAC_NHAN}" để xác nhận.`),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR058 — thực thi yêu cầu xoá. Mẫu M3.
 *
 * Bắt gõ lại một chuỗi thay vì chỉ bấm "Xác nhận". Với thao tác không đảo ngược được, một nút bấm
 * là quá ít ma sát: người dùng bấm nhầm nút này ở nhịp thứ ba của một chuỗi thao tác quen tay thì
 * không có cách nào lấy lại dữ liệu.
 *
 * Hộp thoại tóm tắt lại **con số cụ thể** sắp bị đụng tới, không phải một câu "bạn có chắc không":
 * người ký phải biết mình đang xoá 148 tin nhắn và ẩn danh 34 lượt xử lý AI, chứ không phải "dữ
 * liệu của khách hàng này".
 */
export function ExecuteErasureDialog({
  yeuCau,
  onDong,
}: {
  yeuCau: YeuCauXoaChiTiet | null
  onDong: () => void
}) {
  const [thucThi, ketQua] = useThucThiYeuCauXoaMutation()

  const form = useForm<GiaTri>({ resolver: zodResolver(luocDo), defaultValues: { xacNhan: '' } })

  useEffect(() => {
    if (yeuCau) form.reset({ xacNhan: '' })
  }, [yeuCau, form])

  if (!yeuCau) return null

  const chuaChay = yeuCau.items.filter((m) => m.status !== 'DONE')
  const soXoaHan = chuaChay
    .filter((m) => m.action === 'DELETE')
    .reduce((t, m) => t + (m.affectedRows ?? 0), 0)
  const soAnDanh = chuaChay
    .filter((m) => m.action === 'ANONYMIZE')
    .reduce((t, m) => t + (m.affectedRows ?? 0), 0)
  const chayLai = yeuCau.status === 'PARTIALLY_FAILED'

  return (
    <FormDialog
      mo
      onDoiMo={(m) => !m && onDong()}
      tieuDe={chayLai ? 'Chạy lại phần xoá còn dở dang' : 'Thực thi xoá dữ liệu cá nhân'}
      moTa={`Khách hàng ${yeuCau.contactName ?? 'không rõ tên'} · ${yeuCau.legalBasis ?? 'không ghi căn cứ'}`}
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      rong="rong"
      nhanGui={chayLai ? 'Chạy lại phần còn lại' : 'Xoá vĩnh viễn'}
      nhanHuy="Không xoá"
      onGui={async () => {
        await thucThi(yeuCau.id).unwrap()
        toast.success('Đã thực thi xoá. Biên bản xác nhận đã sẵn sàng để tải về.')
        onDong()
      }}
    >
      <Alert variant="destructive">
        <ShieldAlert />
        <AlertTitle>Thao tác này không đảo ngược được</AlertTitle>
        <AlertDescription>
          Không có bản sao lưu nào để khôi phục dữ liệu đã xoá. Chỉ tiếp tục khi danh tính khách đã
          được xác minh và hồ sơ yêu cầu đã lưu.
        </AlertDescription>
      </Alert>

      <div className="flex flex-col rounded-lg border p-3">
        <HangThongTin nhan="Xác minh danh tính">
          {yeuCau.identityVerifiedByName ?? 'Chưa xác minh'}
        </HangThongTin>
        <HangThongTin nhan="Số bảng bị đụng tới">
          <span className="tabular-nums">{chuaChay.length}</span>
        </HangThongTin>
        <HangThongTin nhan={NHAN_THAO_TAC_XOA.DELETE.nhan}>
          <span className="text-destructive tabular-nums">
            {soXoaHan.toLocaleString('vi-VN')} dòng
          </span>
        </HangThongTin>
        <HangThongTin nhan={NHAN_THAO_TAC_XOA.ANONYMIZE.nhan}>
          <span className="tabular-nums">{soAnDanh.toLocaleString('vi-VN')} dòng</span>
        </HangThongTin>
        <HangThongTin nhan={NHAN_THAO_TAC_XOA.KEEP_AGGREGATE.nhan}>
          <span className="tabular-nums">
            {chuaChay.filter((m) => m.action === 'KEEP_AGGREGATE').length} bảng
          </span>
        </HangThongTin>
      </div>

      {yeuCau.externalSystemsNote && (
        <Alert>
          <AlertDescription>{yeuCau.externalSystemsNote}</AlertDescription>
        </Alert>
      )}

      <Field>
        <FieldLabel htmlFor="xoa-xac-nhan">
          Gõ <span className="font-mono">{XAC_NHAN}</span> để xác nhận
        </FieldLabel>
        <Input id="xoa-xac-nhan" autoComplete="off" {...form.register('xacNhan')} />
        <FieldDescription>
          Thao tác và tên bạn được ghi vào nhật ký kiểm toán dưới hành động{' '}
          <span className="font-mono">ERASURE_EXECUTED</span>.
        </FieldDescription>
        <FieldError errors={[form.formState.errors.xacNhan]} />
      </Field>
    </FormDialog>
  )
}
