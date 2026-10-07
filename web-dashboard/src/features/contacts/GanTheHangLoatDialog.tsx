import { Tag } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useDanhSachTheQuery, useGanTheMutation, useTaoTheMutation } from '@/api/contacts'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const THE_MOI = '__moi__'

/**
 * UC017 — gắn MỘT thẻ cho nhiều khách đang chọn. Chọn thẻ có sẵn hoặc gõ tên thẻ mới (trùng tên khác
 * hoa thường / dấu thì máy chủ trả thẻ cũ). Gắn lần lượt bằng API gắn thẻ có sẵn — khách đã có thẻ thì
 * máy chủ bỏ qua (ON CONFLICT), nên gắn lại không sinh trùng.
 */
export function GanTheHangLoatDialog({
  ids,
  onDoiMo,
}: {
  /** null = đóng. */
  ids: string[] | null
  onDoiMo: (m: boolean) => void
}) {
  const mo = ids !== null
  const the = useDanhSachTheQuery(undefined, { skip: !mo })
  const [taoThe] = useTaoTheMutation()
  const [ganThe] = useGanTheMutation()
  const [chon, datChon] = useState('')
  const [tenMoi, datTenMoi] = useState('')
  const [dangGan, datDangGan] = useState(false)

  useEffect(() => {
    if (!mo) return
    datChon('')
    datTenMoi('')
  }, [mo])

  const coTheMoi = chon === THE_MOI
  const hopLe = coTheMoi ? tenMoi.trim().length > 0 && tenMoi.trim().length <= 50 : chon !== ''

  async function gan() {
    if (!ids || !hopLe) return
    datDangGan(true)
    try {
      const tagId = coTheMoi ? (await taoThe({ name: tenMoi.trim() }).unwrap()).id : chon
      const tenThe = coTheMoi ? tenMoi.trim() : the.data?.find((t) => t.id === chon)?.name
      const kq = await Promise.allSettled(ids.map((contactId) => ganThe({ contactId, tagId }).unwrap()))
      const loi = kq.filter((k) => k.status === 'rejected').length
      if (loi === 0) toast.success(`Đã gắn thẻ "${tenThe}" cho ${ids.length} khách.`)
      else toast.warning(`Gắn được ${ids.length - loi}/${ids.length} khách — ${loi} khách bị lỗi, thử lại sau.`)
      onDoiMo(false)
    } catch (e) {
      toast.error(laLoiTruyVan(e) ? e.message : 'Không gắn được thẻ.')
    } finally {
      datDangGan(false)
    }
  }

  return (
    <Dialog open={mo} onOpenChange={onDoiMo}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Gắn thẻ cho {ids?.length ?? 0} khách</DialogTitle>
          <DialogDescription>
            Thẻ giúp lọc nhanh một nhóm khách, ví dụ "VIP" hay "Quan tâm gói Pro".
          </DialogDescription>
        </DialogHeader>
        <Field>
          <FieldLabel htmlFor="gan-the">Thẻ</FieldLabel>
          <Select value={chon} onValueChange={datChon}>
            <SelectTrigger id="gan-the">
              <SelectValue placeholder="Chọn thẻ…" />
            </SelectTrigger>
            <SelectContent>
              {the.data?.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
              <SelectItem value={THE_MOI}>+ Tạo thẻ mới…</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        {coTheMoi && (
          <Field>
            <FieldLabel htmlFor="ten-the-moi">Tên thẻ mới</FieldLabel>
            <Input
              id="ten-the-moi"
              maxLength={50}
              autoFocus
              placeholder="Ví dụ: VIP"
              value={tenMoi}
              onChange={(e) => datTenMoi(e.target.value)}
            />
          </Field>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onDoiMo(false)} disabled={dangGan}>
            Huỷ
          </Button>
          <Button disabled={!hopLe || dangGan} onClick={() => void gan()}>
            <Tag />
            {dangGan ? 'Đang gắn…' : 'Gắn thẻ'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
