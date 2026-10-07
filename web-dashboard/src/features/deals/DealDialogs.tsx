import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useDanhSachNguoiDungQuery } from '@/api/platform'
import { useCapNhatDealMutation } from '@/api/sales'
import { FormDialog } from '@/components/layout/FormDialog'
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
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { NHAN_LY_DO_THUA } from '@/features/leads/nhan'
import type { DealChiTiet, LyDoThuaDeal } from '@/types/schema'

/** Các hộp thoại dùng chung của bảng phễu (SCR044) và chi tiết deal (SCR045). */

/**
 * UC034 luồng 4.2 — kéo vào "Thua" bắt buộc chọn lý do trong danh sách cố định. Hộp thoại chỉ CHỌN;
 * phía gọi tự gửi lệnh kéo kèm lý do (bảng phễu và trang chi tiết dùng chung).
 */
export function LyDoThuaDialog({
  mo,
  onDoiMo,
  onChon,
  dangGui,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
  onChon: (lyDo: LyDoThuaDeal) => void
  dangGui?: boolean
}) {
  const [lyDo, datLyDo] = useState<LyDoThuaDeal | ''>('')
  useEffect(() => {
    if (mo) datLyDo('')
  }, [mo])

  return (
    <Dialog open={mo} onOpenChange={onDoiMo}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Deal thua — vì sao?</DialogTitle>
          <DialogDescription>
            Lý do thua là dữ liệu phân tích quan trọng nhất của phễu: biết mình thua vì giá hay vì đối
            thủ thì mới sửa đúng chỗ.
          </DialogDescription>
        </DialogHeader>
        <Field>
          <FieldLabel htmlFor="ly-do-thua">Lý do</FieldLabel>
          <Select value={lyDo} onValueChange={(v) => datLyDo(v as LyDoThuaDeal)}>
            <SelectTrigger id="ly-do-thua">
              <SelectValue placeholder="Chọn lý do…" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(NHAN_LY_DO_THUA).map(([ma, nhan]) => (
                <SelectItem key={ma} value={ma}>
                  {nhan}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={() => onDoiMo(false)} disabled={dangGui}>
            Huỷ
          </Button>
          <Button variant="destructive" disabled={!lyDo || dangGui} onClick={() => lyDo && onChon(lyDo)}>
            Đánh dấu thua
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const so = (v: unknown) => (v === '' || v == null || Number.isNaN(v) ? null : Number(v))

const luocDoSua = z.object({
  title: z.string().trim().min(1, 'Nhập tên deal.').max(200, 'Tối đa 200 ký tự.'),
  amount: z.number().min(0, 'Không âm.').nullable(),
  expectedCloseDate: z.string(),
})

type GiaTriSua = z.infer<typeof luocDoSua>

/**
 * Sửa tên / giá trị / ngày chốt. Dùng cả khi kéo bị từ chối vì thiếu trường bắt buộc (UC034 5.1):
 * `lyDo` nói rõ vì sao phải nhập, `onDaLuu` để phía gọi kéo lại ngay sau khi lưu.
 */
export function SuaDealDialog({
  deal,
  mo,
  onDoiMo,
  lyDo,
  onDaLuu,
}: {
  deal: Pick<DealChiTiet, 'id' | 'title' | 'amount' | 'expectedCloseDate'>
  mo: boolean
  onDoiMo: (m: boolean) => void
  lyDo?: string | null
  onDaLuu?: () => void
}) {
  const [capNhat, ketQua] = useCapNhatDealMutation()
  const form = useForm<GiaTriSua>({ resolver: zodResolver(luocDoSua) })

  useEffect(() => {
    if (!mo) return
    form.reset({
      title: deal.title,
      amount: deal.amount ?? null,
      expectedCloseDate: deal.expectedCloseDate ?? '',
    })
    ketQua.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mo])

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe={lyDo ? 'Bổ sung thông tin deal' : 'Sửa thông tin deal'}
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui={lyDo ? 'Lưu và chuyển tiếp' : 'Lưu'}
      onGui={async (g) => {
        try {
          await capNhat({
            id: deal.id,
            than: { title: g.title.trim(), amount: g.amount, expectedCloseDate: g.expectedCloseDate || null },
          }).unwrap()
          onDoiMo(false)
          if (onDaLuu) onDaLuu()
          else toast.success('Đã lưu thông tin deal.')
        } catch {
          // lỗi hiện trong hộp thoại qua `loi`
        }
      }}
    >
      {lyDo && (
        <Alert>
          <AlertDescription>{lyDo}</AlertDescription>
        </Alert>
      )}
      <Field>
        <FieldLabel htmlFor="sd-ten">Tên deal</FieldLabel>
        <Input id="sd-ten" {...form.register('title')} />
        <FieldError errors={[form.formState.errors.title]} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="sd-tien">Giá trị (VND)</FieldLabel>
          <Input
            id="sd-tien"
            type="number"
            min={0}
            step={100000}
            autoFocus={!!lyDo}
            {...form.register('amount', { setValueAs: so })}
          />
          <FieldError errors={[form.formState.errors.amount]} />
        </Field>
        <Field>
          <FieldLabel htmlFor="sd-ngay">Dự kiến chốt</FieldLabel>
          <Input id="sd-ngay" type="date" {...form.register('expectedCloseDate')} />
        </Field>
      </div>
    </FormDialog>
  )
}

/** Chỉ quản trị viên giao deal cho người khác hoặc bỏ trống (máy chủ cũng chặn). */
export function DoiPhuTrachDealDialog({
  deal,
  mo,
  onDoiMo,
}: {
  deal: Pick<DealChiTiet, 'id' | 'ownerUserId'>
  mo: boolean
  onDoiMo: (m: boolean) => void
}) {
  const [capNhat, ketQua] = useCapNhatDealMutation()
  const nguoiDung = useDanhSachNguoiDungQuery({ trangThai: 'ACTIVE' }, { skip: !mo })
  const [chon, datChon] = useState('')

  useEffect(() => {
    if (mo) datChon(deal.ownerUserId ?? 'trong')
  }, [mo, deal.ownerUserId])

  return (
    <Dialog open={mo} onOpenChange={onDoiMo}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Đổi người phụ trách deal</DialogTitle>
          <DialogDescription>Người phụ trách theo deal tới khi chốt thắng hoặc thua.</DialogDescription>
        </DialogHeader>
        <Field>
          <FieldLabel htmlFor="doi-chu-deal">Người phụ trách</FieldLabel>
          <Select value={chon} onValueChange={datChon}>
            <SelectTrigger id="doi-chu-deal">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="trong">Chưa ai nhận</SelectItem>
              {nguoiDung.data?.items.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.fullName ?? u.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={() => onDoiMo(false)} disabled={ketQua.isLoading}>
            Huỷ
          </Button>
          <Button
            disabled={ketQua.isLoading || chon === (deal.ownerUserId ?? 'trong')}
            onClick={async () => {
              try {
                await capNhat({ id: deal.id, than: { ownerUserId: chon === 'trong' ? null : chon } }).unwrap()
                toast.success('Đã đổi người phụ trách.')
                onDoiMo(false)
              } catch (loi) {
                toast.error(laLoiTruyVan(loi) ? loi.message : 'Không đổi được người phụ trách.')
              }
            }}
          >
            Lưu
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
