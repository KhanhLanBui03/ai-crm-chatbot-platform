import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  isLoading?: boolean
}

/**
 * Hộp thoại xác nhận trước khi đăng xuất tài khoản để tránh bấm nhầm.
 */
export function XacNhanDangXuatDialog({ open, onOpenChange, onConfirm, isLoading }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Xác nhận đăng xuất</DialogTitle>
          <DialogDescription>
            Bạn có chắc chắn muốn đăng xuất khỏi hệ thống không? Phiên làm việc hiện tại sẽ kết thúc và bạn cần đăng nhập lại để tiếp tục.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={isLoading}
            onClick={() => onOpenChange(false)}
          >
            Ở lại
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={isLoading}
            onClick={onConfirm}
          >
            {isLoading ? 'Đang đăng xuất…' : 'Đăng xuất'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
