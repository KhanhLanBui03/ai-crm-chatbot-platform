import { format, formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { AlertTriangle, MoreHorizontal, Pencil, Pin, PinOff, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useSuaGhiChuMutation, useXoaGhiChuMutation } from '@/api/contacts'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { StatusChip } from '@/components/ui/status-chip'
import { Textarea } from '@/components/ui/textarea'
import type { GhiChu } from '@/types/schema'

const DAI_TOI_DA = 4000

/**
 * UC017 — một ghi chú nội bộ: sửa tại chỗ, ghim, xoá (có hỏi lại).
 *
 * Nút ⋯ chỉ hiện khi máy chủ báo `canEdit` (tác giả hoặc quản trị viên) — giao diện không tự
 * suy quyền. Hồ sơ đã hợp nhất / ẩn danh hoá thì máy chủ chỉ còn cho **xoá**.
 */
export function NoteCard({
  ghiChu,
  contactId,
  chiXoa,
}: {
  ghiChu: GhiChu
  contactId: string
  chiXoa: boolean
}) {
  const [dangSua, datDangSua] = useState(false)
  const [nhap, datNhap] = useState(ghiChu.content)
  const [hoiXoa, datHoiXoa] = useState(false)
  const [suaGhiChu, ketQuaSua] = useSuaGhiChuMutation()
  const [xoaGhiChu, ketQuaXoa] = useXoaGhiChuMutation()

  const nhapGon = nhap.trim()
  const luuDuoc = nhapGon !== '' && nhapGon !== ghiChu.content && nhap.length <= DAI_TOI_DA

  async function luu() {
    try {
      await suaGhiChu({ contactId, noteId: ghiChu.id, content: nhapGon }).unwrap()
      toast.success('Đã sửa ghi chú.')
      datDangSua(false)
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không sửa được ghi chú.')
    }
  }

  async function doiGhim() {
    try {
      await suaGhiChu({ contactId, noteId: ghiChu.id, isPinned: !ghiChu.isPinned }).unwrap()
      toast.success(ghiChu.isPinned ? 'Đã bỏ ghim.' : 'Đã ghim lên đầu.')
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không đổi được trạng thái ghim.')
    }
  }

  async function xoa() {
    try {
      await xoaGhiChu({ contactId, noteId: ghiChu.id }).unwrap()
      toast.success('Đã xoá ghi chú.')
      datHoiXoa(false)
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Không xoá được ghi chú.')
    }
  }

  function batDauSua() {
    datNhap(ghiChu.content)
    datDangSua(true)
  }

  return (
    <div className="flex flex-col gap-1.5 rounded-lg border p-3">
      <div className="flex flex-wrap items-center gap-2">
        {ghiChu.isPinned && (
          <Pin aria-label="Đã ghim" className="text-muted-foreground size-3.5 shrink-0" />
        )}
        <span className="text-[13px] font-medium">{ghiChu.authorName}</span>
        <span className="text-muted-foreground text-xs">
          {formatDistanceToNowStrict(new Date(ghiChu.createdAt), { locale: vi, addSuffix: true })}
          {ghiChu.editedAt && (
            <span title={`Sửa lúc ${format(new Date(ghiChu.editedAt), 'dd/MM/yyyy HH:mm')}`}>
              {' '}
              (đã sửa)
            </span>
          )}
        </span>
        {/* Máy chủ tự đánh dấu ghi chú chứa dữ liệu cá nhân. Hiện ra chứ không giấu — nhân viên
            cần biết dòng nào sẽ bị che khi xuất dữ liệu và bị xoá khi khách yêu cầu (SCR056). */}
        {ghiChu.flaggedSensitive && (
          <StatusChip sacThai="warning" BieuTuong={AlertTriangle}>
            Có dữ liệu cá nhân
          </StatusChip>
        )}

        {ghiChu.canEdit && !dangSua && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-xs" className="ml-auto" aria-label="Thao tác ghi chú">
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {!chiXoa && (
                <>
                  <DropdownMenuItem onSelect={batDauSua}>
                    <Pencil />
                    Sửa
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={doiGhim}>
                    {ghiChu.isPinned ? <PinOff /> : <Pin />}
                    {ghiChu.isPinned ? 'Bỏ ghim' : 'Ghim'}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem variant="destructive" onSelect={() => datHoiXoa(true)}>
                <Trash2 />
                Xoá
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {dangSua ? (
        <div className="flex flex-col gap-1.5">
          <Textarea
            value={nhap}
            onChange={(e) => datNhap(e.target.value)}
            rows={4}
            aria-label="Nội dung ghi chú"
            autoFocus
          />
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground mr-auto text-xs tabular-nums">
              {nhap.length.toLocaleString('vi-VN')}/{DAI_TOI_DA.toLocaleString('vi-VN')}
            </span>
            <Button variant="outline" size="sm" onClick={() => datDangSua(false)}>
              Huỷ
            </Button>
            <Button size="sm" disabled={!luuDuoc || ketQuaSua.isLoading} onClick={luu}>
              {ketQuaSua.isLoading ? 'Đang lưu…' : 'Lưu'}
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-[13px] leading-relaxed whitespace-pre-line">{ghiChu.content}</p>
      )}

      <Dialog open={hoiXoa} onOpenChange={datHoiXoa}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Xoá ghi chú này?</DialogTitle>
            <DialogDescription>
              Ghi chú biến mất khỏi hồ sơ với mọi nhân viên. Nhật ký kiểm toán vẫn giữ dấu vết
              thao tác xoá.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => datHoiXoa(false)}>
              Huỷ
            </Button>
            <Button variant="destructive" disabled={ketQuaXoa.isLoading} onClick={xoa}>
              {ketQuaXoa.isLoading ? 'Đang xoá…' : 'Xoá ghi chú'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
