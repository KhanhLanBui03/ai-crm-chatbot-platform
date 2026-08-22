import { AlertCircle } from 'lucide-react'
import type { FieldValues, UseFormReturn } from 'react-hook-form'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { FieldGroup } from '@/components/ui/field'
import { laLoiTruyVan } from '@/api/baseQuery'

export interface FormDialogProps<T extends FieldValues> {
  mo: boolean
  onDoiMo: (mo: boolean) => void
  tieuDe: string
  moTa?: string
  /** Biểu mẫu do phía gọi dựng — mỗi màn một lược đồ zod riêng, không gộp vào đây được. */
  form: UseFormReturn<T>
  onGui: (giaTri: T) => Promise<unknown>
  /** Lỗi từ RTK Query của lần gửi gần nhất. Lỗi theo từng trường thì `form` tự hiện. */
  loi?: unknown
  dangGui?: boolean
  nhanGui?: string
  nhanHuy?: string
  /** Rộng hơn mặc định cho biểu mẫu nhiều trường. */
  rong?: 'vua' | 'rong'
  children: React.ReactNode
}

/**
 * Mẫu M3 — hộp thoại biểu mẫu. Phủ 7 màn hình (ADR-0011).
 *
 * shadcn 4.x **đã bỏ `Form`**, nên biểu mẫu ghép `Field` với react-hook-form. Component này lo
 * phần khung lặp lại ở cả 7 màn: tiêu đề, vùng lỗi cấp biểu mẫu, hai nút chân, khoá nút khi đang
 * gửi. Các trường cụ thể do phía gọi truyền vào `children`.
 *
 * Đóng hộp thoại **không** reset biểu mẫu — người dùng lỡ tay bấm ra ngoài mà mất hết những gì đã
 * gõ là lỗi khó tha thứ. Muốn xoá thì gọi `form.reset()` sau khi gửi thành công.
 */
export function FormDialog<T extends FieldValues>({
  mo,
  onDoiMo,
  tieuDe,
  moTa,
  form,
  onGui,
  loi,
  dangGui = false,
  nhanGui = 'Lưu',
  nhanHuy = 'Huỷ',
  rong = 'vua',
  children,
}: FormDialogProps<T>) {
  const thongDiepLoi = laLoiTruyVan(loi) ? loi.message : null

  return (
    <Dialog open={mo} onOpenChange={onDoiMo}>
      <DialogContent className={rong === 'rong' ? 'sm:max-w-2xl' : 'sm:max-w-lg'}>
        <form
          /**
           * `noValidate` là bắt buộc, không phải tuỳ chọn.
           *
           * Không có nó thì `<input type="email">` kích hoạt kiểm tra sẵn có của trình duyệt và
           * **chặn submit trước khi react-hook-form kịp chạy**: người dùng thấy một bong bóng
           * của trình duyệt, đúng ngôn ngữ hệ điều hành chứ không phải ngôn ngữ ứng dụng, biến
           * mất ngay khi bấm chỗ khác — còn thông báo tiếng Việt do zod sinh thì không bao giờ
           * hiện ra. Lỗi này không nổ ở `tsc` và trông y hệt "nút Gửi bị liệt".
           */
          noValidate
          onSubmit={form.handleSubmit(async (giaTri) => {
            await onGui(giaTri)
          })}
          className="flex flex-col gap-5"
        >
          <DialogHeader>
            <DialogTitle>{tieuDe}</DialogTitle>
            {moTa && <DialogDescription>{moTa}</DialogDescription>}
          </DialogHeader>

          {thongDiepLoi && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{thongDiepLoi}</AlertDescription>
            </Alert>
          )}

          <FieldGroup>{children}</FieldGroup>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onDoiMo(false)}
              disabled={dangGui}
            >
              {nhanHuy}
            </Button>
            <Button type="submit" disabled={dangGui}>
              {dangGui ? 'Đang lưu…' : nhanGui}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
