import { useState } from 'react'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useChuyenGiaoHoiThoaiMutation } from '@/api/conversations'
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
import type { LyDoChuyenGiao } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * Lý do chuyển giao — lấy nguyên văn enum `handoff_events.reason` của ERD.
 *
 * `tinhVaoChatLuong` cho biết lý do đó có bị tính vào chỉ số "tác tử phải nhường người" hay
 * không. Bày ra ngay lúc chọn, vì nhân viên chọn bừa một lý do là làm lệch thước đo chính của
 * chất lượng tác tử (SCR051).
 */
const LY_DO: { ma: LyDoChuyenGiao; nhan: string; moTa: string; tinhVaoChatLuong: boolean }[] = [
  {
    ma: 'CUSTOMER_REQUEST',
    nhan: 'Khách yêu cầu gặp người',
    moTa: 'Khách chủ động đòi nói chuyện với nhân viên.',
    tinhVaoChatLuong: false,
  },
  {
    ma: 'LOW_CONFIDENCE',
    nhan: 'Tác tử không chắc chắn',
    moTa: 'Câu trả lời có độ tin cậy thấp.',
    tinhVaoChatLuong: true,
  },
  {
    ma: 'NO_GROUNDING',
    nhan: 'Không tìm được căn cứ',
    moTa: 'Kho tri thức chưa phủ câu hỏi này.',
    tinhVaoChatLuong: true,
  },
  {
    ma: 'NEGATIVE_SENTIMENT',
    nhan: 'Khách đang bực',
    moTa: 'Giọng điệu tiêu cực, nên để người xử lý.',
    tinhVaoChatLuong: true,
  },
  {
    ma: 'REPEATED_FAILURE',
    nhan: 'Lặp lại nhiều lần không xong',
    moTa: 'Đã thử vài lượt mà vẫn chưa giải quyết được.',
    tinhVaoChatLuong: true,
  },
  {
    ma: 'WRITE_TOOL_APPROVAL',
    nhan: 'Cần duyệt thao tác ghi',
    moTa: 'Tác tử muốn gọi công cụ có ghi dữ liệu, cần người xác nhận.',
    tinhVaoChatLuong: false,
  },
]

export function HandoffDialog({
  mo,
  onDoiMo,
  idHoiThoai,
  huong,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
  idHoiThoai: string
  huong: 'BOT_TO_AGENT' | 'AGENT_TO_BOT'
}) {
  const [chuyen, ketQua] = useChuyenGiaoHoiThoaiMutation()
  const [lyDo, datLyDo] = useState<LyDoChuyenGiao | null>(null)
  const veNguoi = huong === 'BOT_TO_AGENT'

  return (
    <Dialog
      open={mo}
      onOpenChange={(m) => {
        onDoiMo(m)
        if (!m) datLyDo(null)
      }}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {veNguoi ? 'Chuyển cho nhân viên' : 'Trả lại cho tác tử AI'}
          </DialogTitle>
          <DialogDescription>
            {veNguoi
              ? 'Tác tử ngừng tự trả lời hội thoại này cho tới khi có người xử lý xong.'
              : 'Tác tử tiếp tục tự trả lời. Chỉ làm khi vấn đề đã được giải quyết.'}
          </DialogDescription>
        </DialogHeader>

        {laLoiTruyVan(ketQua.error) && (
          <Alert variant="destructive">
            <AlertDescription>{ketQua.error.message}</AlertDescription>
          </Alert>
        )}

        <div className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium">Lý do</span>
          {LY_DO.map((l) => (
            <button
              key={l.ma}
              type="button"
              onClick={() => datLyDo(l.ma)}
              className={cn(
                'flex flex-col gap-0.5 rounded-lg border p-2.5 text-left transition-colors',
                lyDo === l.ma ? 'ring-primary bg-primary/5 ring-1' : 'hover:bg-muted/60',
              )}
            >
              <span className="text-[13px] font-medium">{l.nhan}</span>
              <span className="text-muted-foreground text-xs leading-relaxed">
                {l.moTa}
                {l.tinhVaoChatLuong && ' · tính vào chỉ số chất lượng của tác tử'}
              </span>
            </button>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onDoiMo(false)} disabled={ketQua.isLoading}>
            Huỷ
          </Button>
          <Button
            disabled={!lyDo || ketQua.isLoading}
            onClick={async () => {
              if (!lyDo) return
              await chuyen({ id: idHoiThoai, direction: huong, reason: lyDo }).unwrap()
              toast.success(veNguoi ? 'Đã chuyển cho nhân viên.' : 'Đã trả lại cho tác tử AI.')
              onDoiMo(false)
              datLyDo(null)
            }}
          >
            {ketQua.isLoading ? 'Đang chuyển…' : 'Chuyển giao'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
