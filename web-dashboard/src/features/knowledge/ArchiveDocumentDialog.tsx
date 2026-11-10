import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

/**
 * Hộp xác nhận gỡ tài liệu khỏi kho — UC020 bước 7 (đặc tả giao cho CRM "hộp xác nhận xoá").
 *
 * Câu chữ nói rõ ba điều người dùng cần biết trước khi bấm: tác tử AI thôi trích dẫn tài liệu này,
 * câu trả lời đã gửi vẫn giữ nguyên trích dẫn cũ (luồng phụ 7.1), và tài liệu không mất hẳn mà
 * chuyển sang "Đã lưu trữ".
 */
export function ArchiveDocumentDialog({
  mo,
  onDoiMo,
  doiTuong,
  dangXuLy,
  onXacNhan,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
  /** Tiêu đề tài liệu, hoặc "3 tài liệu" khi gỡ hàng loạt. */
  doiTuong: string
  dangXuLy: boolean
  onXacNhan: () => void
}) {
  return (
    <Dialog open={mo} onOpenChange={(m) => !dangXuLy && onDoiMo(m)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Gỡ khỏi kho tri thức?</DialogTitle>
          <DialogDescription>
            Các đoạn của <strong>{doiTuong}</strong> sẽ bị xoá khỏi chỉ mục và tác tử AI không còn
            trích dẫn nữa. Câu trả lời đã gửi trước đó giữ nguyên trích dẫn. Tài liệu chuyển sang
            "Đã lưu trữ" — lọc theo trạng thái này để xem lại.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-2">
          <Button type="button" variant="outline" disabled={dangXuLy} onClick={() => onDoiMo(false)}>
            Huỷ
          </Button>
          <Button type="button" variant="destructive" disabled={dangXuLy} onClick={onXacNhan}>
            {dangXuLy ? 'Đang gỡ…' : 'Gỡ khỏi kho'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
