import { Check, Copy, MessageCircle, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import {
  useCauHinhWidgetQuery,
  useLuuCauHinhWidgetMutation,
  useMaNhungWidgetQuery,
} from '@/api/channels'
import { SettingsPage } from '@/components/layout/SettingsPage'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { StatusChip } from '@/components/ui/status-chip'
import { Textarea } from '@/components/ui/textarea'
import type { CauHinhWidget } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * SCR018 — cấu hình Web Widget. Mẫu M4, cộng một khung xem trước.
 *
 * Xem trước dựng bằng chính CSS của dashboard chứ **không** nhúng `web-widget` thật: widget thật
 * là TypeScript thuần trong Shadow DOM, kéo nó vào đây là kéo theo cả một bản build khác. Đổi lại,
 * đây chỉ là ước lượng — hình dáng cuối cùng vẫn phải xem trên site thật.
 */
export function WidgetConfigPage() {
  const truyVan = useCauHinhWidgetQuery()
  const maNhung = useMaNhungWidgetQuery()
  const [luu, ketQua] = useLuuCauHinhWidgetMutation()
  const [nhap, datNhap] = useState<CauHinhWidget | null>(null)
  const [daChep, datDaChep] = useState(false)

  useEffect(() => {
    if (truyVan.data) datNhap(truyVan.data)
  }, [truyVan.data])

  const goc = truyVan.data
  const coThayDoi = Boolean(nhap && goc && JSON.stringify(nhap) !== JSON.stringify(goc))
  const dat = <K extends keyof CauHinhWidget>(k: K, v: CauHinhWidget[K]) =>
    datNhap((cu) => (cu ? { ...cu, [k]: v } : cu))

  return (
    <SettingsPage
      tieuDe="Web Widget"
      moTa="Khung chat nhúng trên website của bạn. Đổi ở đây là đổi trên mọi trang đã nhúng."
      dangTai={truyVan.isLoading || !nhap}
      coThayDoi={coThayDoi}
      dangLuu={ketQua.isLoading}
      loi={ketQua.error}
      onHuy={() => goc && datNhap(goc)}
      onLuu={async () => {
        if (!nhap) return
        await luu(nhap).unwrap()
        toast.success('Đã lưu. Website nhận cấu hình mới trong vòng một phút.')
      }}
      muc={[
        {
          tieuDe: 'Giao diện',
          noiDung: nhap && (
            <div className="flex flex-col gap-4 lg:flex-row">
              <div className="flex flex-1 flex-col gap-4">
                <Field>
                  <FieldLabel htmlFor="wg-mau">Màu chủ đạo</FieldLabel>
                  <div className="flex items-center gap-2">
                    <input
                      id="wg-mau"
                      type="color"
                      className="border-input size-9 shrink-0 cursor-pointer rounded-lg border bg-transparent p-1"
                      value={nhap.primaryColor ?? '#2a78d6'}
                      onChange={(e) => dat('primaryColor', e.target.value)}
                    />
                    <Input
                      className="max-w-28 font-mono"
                      value={nhap.primaryColor ?? ''}
                      onChange={(e) => dat('primaryColor', e.target.value)}
                    />
                  </div>
                </Field>

                <Field>
                  <FieldLabel htmlFor="wg-vitri">Vị trí</FieldLabel>
                  <Select
                    value={nhap.position}
                    onValueChange={(v) => dat('position', v as CauHinhWidget['position'])}
                  >
                    <SelectTrigger id="wg-vitri">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="BOTTOM_RIGHT">Góc dưới bên phải</SelectItem>
                      <SelectItem value="BOTTOM_LEFT">Góc dưới bên trái</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>

                <Field>
                  <FieldLabel htmlFor="wg-chao">Lời chào</FieldLabel>
                  <Textarea
                    id="wg-chao"
                    rows={2}
                    className="resize-none"
                    value={nhap.greetingMessage ?? ''}
                    onChange={(e) => dat('greetingMessage', e.target.value)}
                  />
                  <FieldDescription>
                    Hiện ngay khi khách mở khung chat, trước cả khi họ gõ gì.
                  </FieldDescription>
                </Field>
              </div>

              <XemTruoc cauHinh={nhap} />
            </div>
          ),
        },
        {
          tieuDe: 'Tên miền cho phép',
          moTa:
            'Khoá công khai nằm lộ trong mã nguồn trang web — ai cũng đọc được. Danh sách này mới ' +
            'là thứ chặn người khác nhúng widget của bạn lên site của họ.',
          noiDung: nhap && (
            <Field>
              <FieldLabel htmlFor="wg-mien">Mỗi dòng một tên miền</FieldLabel>
              <Textarea
                id="wg-mien"
                rows={4}
                className="resize-none font-mono text-[13px]"
                value={nhap.allowedDomains.join('\n')}
                onChange={(e) =>
                  dat(
                    'allowedDomains',
                    e.target.value.split('\n').map((d) => d.trim()).filter(Boolean),
                  )
                }
              />
              <FieldDescription>
                Không dùng ký tự đại diện. Cần cả <code>cattuong.vn</code> lẫn{' '}
                <code>www.cattuong.vn</code> nếu site chạy cả hai.
              </FieldDescription>
            </Field>
          ),
        },
        {
          tieuDe: 'Mã nhúng',
          moTa: 'Dán ngay trước thẻ đóng </body> của mọi trang muốn có khung chat.',
          noiDung: (
            <div className="flex flex-col gap-2">
              <pre className="bg-muted overflow-x-auto rounded-lg p-3 font-mono text-xs leading-relaxed">
                {maNhung.data?.snippet ?? 'Đang tải…'}
              </pre>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!maNhung.data}
                  onClick={async () => {
                    await navigator.clipboard.writeText(maNhung.data!.snippet)
                    datDaChep(true)
                    toast.success('Đã chép mã nhúng.')
                    setTimeout(() => datDaChep(false), 2000)
                  }}
                >
                  {daChep ? <Check /> : <Copy />}
                  {daChep ? 'Đã chép' : 'Chép mã'}
                </Button>
                <span className="text-muted-foreground text-xs">
                  Mã nhúng đổi theo cấu hình ở trên — chép lại sau khi lưu.
                </span>
              </div>
            </div>
          ),
        },
      ]}
    />
  )
}

/** Ước lượng hình dáng widget bằng CSS của dashboard, không nhúng bản build thật. */
function XemTruoc({ cauHinh }: { cauHinh: CauHinhWidget }) {
  const mau = cauHinh.primaryColor ?? '#2a78d6'
  const trai = cauHinh.position === 'BOTTOM_LEFT'

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground text-xs">Xem trước</span>
        <StatusChip sacThai="neutral">Ước lượng</StatusChip>
      </div>
      <div
        className={cn(
          'bg-muted/40 relative h-64 w-64 shrink-0 overflow-hidden rounded-lg border',
          trai ? 'flex justify-start' : 'flex justify-end',
        )}
      >
        <div className="flex w-52 flex-col self-end p-3">
          <div
            className="flex items-center gap-2 rounded-t-xl px-3 py-2 text-white"
            style={{ backgroundColor: mau }}
          >
            <MessageCircle className="size-3.5" />
            <span className="flex-1 text-xs font-medium">Cát Tường</span>
            <X className="size-3 opacity-70" />
          </div>
          <div className="bg-background flex flex-col gap-2 rounded-b-xl border border-t-0 p-2.5">
            <div className="bg-muted rounded-lg px-2.5 py-1.5 text-[11px] leading-snug">
              {cauHinh.greetingMessage || 'Chào bạn!'}
            </div>
            <div className="border-input text-muted-foreground rounded-lg border px-2.5 py-1.5 text-[11px]">
              Nhập tin nhắn…
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
