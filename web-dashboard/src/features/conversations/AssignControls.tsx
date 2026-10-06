import { Undo2, UserRoundCog } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import {
  useNguoiNhanHoiThoaiQuery,
  usePhanCongHoiThoaiMutation,
  useTraVeHangChoMutation,
} from '@/api/conversations'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Textarea } from '@/components/ui/textarea'
import type { NguoiNhanHoiThoai } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * UC015 b3 — quản trị viên giao hội thoại cho một người cụ thể. Mỗi người hiện chấm + CHỮ trực
 * tuyến/ngoại tuyến (không truyền đạt chỉ bằng màu) và số hội thoại đang giữ. Chọn người ngoại tuyến
 * vẫn được nhưng phải xác nhận (UC015 6.1) — nếu họ không phản hồi, job quá hạn sẽ tự trả về hàng chờ.
 */
export function GiaoChoNguoi({ idHoiThoai, nguoiDangGiu }: { idHoiThoai: string; nguoiDangGiu?: string | null }) {
  const [mo, datMo] = useState(false)
  const [choXacNhan, datChoXacNhan] = useState<NguoiNhanHoiThoai | null>(null)
  const ds = useNguoiNhanHoiThoaiQuery(undefined, { skip: !mo })
  const [phanCong, ketQua] = usePhanCongHoiThoaiMutation()

  async function giao(nguoi: NguoiNhanHoiThoai) {
    try {
      await phanCong({ id: idHoiThoai, assigneeUserId: nguoi.userId }).unwrap()
      toast.success(`Đã giao cho ${nguoi.fullName}.`)
      datMo(false)
      datChoXacNhan(null)
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không giao được hội thoại.')
    }
  }

  return (
    <>
      <Popover open={mo} onOpenChange={datMo}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm">
            <UserRoundCog />
            Giao cho…
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-72 p-0" align="end">
          <Command>
            <CommandInput placeholder="Tìm nhân viên…" />
            <CommandList>
              <CommandEmpty>{ds.isLoading ? 'Đang tải…' : 'Không có ai phù hợp.'}</CommandEmpty>
              <CommandGroup>
                {ds.data?.map((n) => (
                  <CommandItem
                    key={n.userId}
                    value={n.fullName}
                    disabled={ketQua.isLoading || n.userId === nguoiDangGiu}
                    onSelect={() => (n.online ? giao(n) : datChoXacNhan(n))}
                  >
                    <span
                      aria-hidden
                      className={cn('size-2 shrink-0 rounded-full', n.online ? 'bg-success' : 'bg-muted-foreground/40')}
                    />
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate">{n.fullName}</span>
                      <span className="text-muted-foreground text-xs">
                        {n.online ? 'Trực tuyến' : 'Ngoại tuyến'} · {n.role === 'TENANT_ADMIN' ? 'Quản trị' : 'Nhân viên'}
                      </span>
                    </span>
                    <span className="text-muted-foreground text-xs tabular-nums">
                      {n.openCount.toLocaleString('vi-VN')} việc
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <Dialog open={!!choXacNhan} onOpenChange={(m) => !m && datChoXacNhan(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Giao cho người đang ngoại tuyến?</DialogTitle>
            <DialogDescription>
              {choXacNhan?.fullName} không mở Hộp thư trong 2 phút qua. Nếu sau 5 phút họ chưa trả lời, hệ thống sẽ
              tự trả hội thoại về hàng chờ để khách không phải chờ vô ích.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => datChoXacNhan(null)}>
              Huỷ
            </Button>
            <Button disabled={ketQua.isLoading} onClick={() => choXacNhan && giao(choXacNhan)}>
              Vẫn giao
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

/** UC015 1a — trả hội thoại về hàng chờ, bắt nhập lý do (5–200 ký tự, giống máy chủ). */
export function TraVeHangCho({ idHoiThoai, onXong }: { idHoiThoai: string; onXong?: () => void }) {
  const [mo, datMo] = useState(false)
  const [lyDo, datLyDo] = useState('')
  const [traVe, ketQua] = useTraVeHangChoMutation()
  const hopLe = lyDo.trim().length >= 5 && lyDo.trim().length <= 200

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => datMo(true)}>
        <Undo2 />
        Trả về hàng chờ
      </Button>
      <Dialog open={mo} onOpenChange={datMo}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Trả hội thoại về hàng chờ</DialogTitle>
            <DialogDescription>
              Hệ thống sẽ tự giao cho người khác đang trực (không giao lại cho bạn). Lý do giúp quản trị viên biết vì
              sao hội thoại bị trả.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            rows={3}
            maxLength={200}
            placeholder="Ví dụ: hết ca làm việc, khách cần bộ phận kỹ thuật…"
            aria-label="Lý do trả về hàng chờ"
            value={lyDo}
            onChange={(e) => datLyDo(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => datMo(false)}>
              Huỷ
            </Button>
            <Button
              disabled={!hopLe || ketQua.isLoading}
              onClick={async () => {
                try {
                  const kq = await traVe({ id: idHoiThoai, reason: lyDo.trim() }).unwrap()
                  toast.success(
                    kq.assignedUserName ? `Đã trả về — tự giao cho ${kq.assignedUserName}.` : 'Đã trả về hàng chờ.',
                  )
                  datMo(false)
                  datLyDo('')
                  onXong?.()
                } catch (loi) {
                  toast.error(laLoiTruyVan(loi) ? loi.message : 'Không trả về được.')
                }
              }}
            >
              {ketQua.isLoading ? 'Đang trả…' : 'Trả về hàng chờ'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
