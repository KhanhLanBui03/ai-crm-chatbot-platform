import { zodResolver } from '@hookform/resolvers/zod'
import { format } from 'date-fns'
import { Check, ShieldAlert, X } from 'lucide-react'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { useDanhSachCongCuQuery, useDuyetGoiCongCuMutation } from '@/api/ai-agent'
import { FormDialog } from '@/components/layout/FormDialog'
import { HangThongTin } from '@/components/layout/DetailPage'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { StatusChip } from '@/components/ui/status-chip'
import { Textarea } from '@/components/ui/textarea'
import { NHAN_MUC_RUI_RO, doTre } from '@/features/ai-agent/nhan'
import { cn } from '@/utils/cn'
import type { NhatKyGoiCongCu } from '@/types/schema'

const luocDo = z.object({
  decision: z.enum(['APPROVED', 'REJECTED']),
  note: z.string().max(500, 'Ghi chú tối đa 500 ký tự.').optional(),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * SCR040 — duyệt hoặc từ chối một lời gọi công cụ. Mẫu M3. Bề mặt **T4**.
 *
 * Màn này hiện **toàn bộ tham số** của lời gọi, không phải chỉ tên công cụ. Người bấm đồng ý đang
 * chịu trách nhiệm cho một thao tác ghi vào hệ thống thật; "cho phép `tao_don_hang`" mà không
 * thấy địa chỉ giao và danh sách mặt hàng thì chữ ký đó không có nội dung gì.
 *
 * Tham số đã được che dữ liệu nhạy cảm trước khi ghi vào nhật ký, nên những gì hiện ở đây đúng
 * bằng những gì được lưu — không có phiên bản đầy đủ hơn ở chỗ khác.
 */
export function ApproveToolCallDialog({
  loiGoi,
  onDong,
}: {
  loiGoi: NhatKyGoiCongCu | null
  onDong: () => void
}) {
  const [duyet, ketQua] = useDuyetGoiCongCuMutation()
  const congCu = useDanhSachCongCuQuery({}, { skip: !loiGoi })

  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: { decision: 'APPROVED', note: '' },
  })

  // Mở lại hộp thoại cho một lời gọi khác thì quyết định phải về mặc định, không kế thừa lần trước
  useEffect(() => {
    if (loiGoi) form.reset({ decision: 'APPROVED', note: '' })
  }, [loiGoi, form])

  if (!loiGoi) return null

  const cc = congCu.data?.find((c) => c.toolName === loiGoi.toolName)
  const rui = cc ? NHAN_MUC_RUI_RO[cc.riskLevel] : null
  const quyetDinh = form.watch('decision')
  const thamSo = Object.entries(loiGoi.arguments ?? {})

  return (
    <FormDialog
      mo
      onDoiMo={(m) => !m && onDong()}
      tieuDe="Duyệt lời gọi công cụ"
      moTa="Tác tử AI đang chờ quyết định của bạn. Đọc hết tham số trước khi đồng ý."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      rong="rong"
      nhanGui={quyetDinh === 'APPROVED' ? 'Đồng ý cho gọi công cụ' : 'Từ chối lời gọi này'}
      nhanHuy="Để sau"
      onGui={async (giaTri) => {
        await duyet({
          id: loiGoi.id,
          decision: giaTri.decision,
          note: giaTri.note || null,
        }).unwrap()
        toast.success(
          giaTri.decision === 'APPROVED'
            ? `Đã duyệt — ${loiGoi.toolName} được phép chạy.`
            : `Đã từ chối — ${loiGoi.toolName} không được gọi.`,
        )
        onDong()
      }}
    >
      {rui && rui.sacThai === 'destructive' && (
        <Alert variant="destructive">
          <ShieldAlert />
          <AlertTitle>Công cụ có mức rủi ro phá huỷ</AlertTitle>
          <AlertDescription>{rui.moTa}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col rounded-lg border p-3">
        <HangThongTin nhan="Công cụ">
          <span className="font-mono">{loiGoi.toolName}</span>
        </HangThongTin>
        {rui && (
          <HangThongTin nhan="Mức rủi ro">
            <StatusChip sacThai={rui.sacThai}>{rui.nhan}</StatusChip>
          </HangThongTin>
        )}
        {cc?.mcpServerName && <HangThongTin nhan="Máy chủ MCP">{cc.mcpServerName}</HangThongTin>}
        <HangThongTin nhan="Khách hàng">{loiGoi.contactName ?? 'Không rõ'}</HangThongTin>
        <HangThongTin nhan="Thời điểm gọi">
          {format(new Date(loiGoi.calledAt), 'HH:mm:ss dd/MM/yyyy')}
        </HangThongTin>
        <HangThongTin nhan="Độ trễ kiểm duyệt">{doTre(loiGoi.guardLatencyMs)}</HangThongTin>
      </div>

      <Field>
        <FieldLabel htmlFor="dl-tham-so">Tham số của lời gọi</FieldLabel>
        <div id="dl-tham-so" className="flex flex-col gap-2 rounded-lg border p-3">
          {thamSo.length === 0 ? (
            <span className="text-muted-foreground text-[13px]">Lời gọi không có tham số nào.</span>
          ) : (
            thamSo.map(([khoa, giaTri]) => (
              <div key={khoa} className="flex flex-col gap-1">
                <span className="text-muted-foreground font-mono text-xs">{khoa}</span>
                <pre className="bg-muted overflow-x-auto rounded-md p-2 font-mono text-xs leading-relaxed break-words whitespace-pre-wrap">
                  {typeof giaTri === 'string' ? giaTri : JSON.stringify(giaTri, null, 2)}
                </pre>
              </div>
            ))
          )}
        </div>
        <FieldDescription>
          Đã che dữ liệu nhạy cảm trước khi ghi nhật ký. Đây là toàn bộ những gì công cụ sẽ nhận.
        </FieldDescription>
      </Field>

      <Field>
        <FieldLabel htmlFor="dl-quyet-dinh">Quyết định</FieldLabel>
        <div id="dl-quyet-dinh" className="grid grid-cols-2 gap-2">
          <NutQuyetDinh
            dangChon={quyetDinh === 'APPROVED'}
            sacThai="success"
            BieuTuong={Check}
            nhan="Cho phép gọi"
            moTa="Công cụ chạy ngay với đúng tham số ở trên."
            onClick={() => form.setValue('decision', 'APPROVED')}
          />
          <NutQuyetDinh
            dangChon={quyetDinh === 'REJECTED'}
            sacThai="destructive"
            BieuTuong={X}
            nhan="Từ chối"
            moTa="Công cụ không chạy. Tác tử AI báo lại cho khách."
            onClick={() => form.setValue('decision', 'REJECTED')}
          />
        </div>
      </Field>

      <Field>
        <FieldLabel htmlFor="dl-ghi-chu">Ghi chú</FieldLabel>
        <Textarea
          id="dl-ghi-chu"
          rows={2}
          placeholder={
            quyetDinh === 'REJECTED'
              ? 'Vì sao từ chối — ghi lại để lần sau chỉnh quy tắc cho đúng.'
              : 'Không bắt buộc.'
          }
          {...form.register('note')}
        />
        <FieldDescription>Lưu vào nhật ký kiểm toán cùng với quyết định.</FieldDescription>
      </Field>
    </FormDialog>
  )
}

function NutQuyetDinh({
  dangChon,
  sacThai,
  BieuTuong,
  nhan,
  moTa,
  onClick,
}: {
  dangChon: boolean
  sacThai: 'success' | 'destructive'
  BieuTuong: typeof Check
  nhan: string
  moTa: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={dangChon}
      className={cn(
        'flex flex-col gap-1 rounded-lg border p-3 text-left transition-colors',
        dangChon
          ? sacThai === 'success'
            ? 'border-success bg-success/8'
            : 'border-destructive bg-destructive/8'
          : 'hover:bg-muted/50',
      )}
    >
      <span
        className={cn(
          'flex items-center gap-1.5 text-[13px] font-medium',
          dangChon && (sacThai === 'success' ? 'text-success' : 'text-destructive'),
        )}
      >
        <BieuTuong className="size-3.5" />
        {nhan}
      </span>
      <span className="text-muted-foreground text-xs">{moTa}</span>
    </button>
  )
}
