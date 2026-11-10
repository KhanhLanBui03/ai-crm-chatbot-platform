import { zodResolver } from '@hookform/resolvers/zod'
import { ThumbsDown, ThumbsUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useDanhGiaLuotXuLyMutation } from '@/api/ai-agent'
import { FormDialog } from '@/components/layout/FormDialog'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field'
import { Textarea } from '@/components/ui/textarea'
import type { DanhGiaAi, LyDoDanhGia } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * Bốn lý do chê của đặc tả UC027 — đặt ở đây (không ở `features/ai-agent/nhan.ts`) vì hộp thoại dùng
 * chung cho hai feature: Giám sát lượt xử lý và Hộp thư. `nhan.ts` xuất lại bảng này.
 */
export const NHAN_LY_DO_DANH_GIA: Record<LyDoDanhGia, string> = {
  WRONG_INFO: 'Thông tin sai',
  IRRELEVANT: 'Trả lời lạc đề',
  INCOMPLETE: 'Trả lời thiếu',
  BAD_TONE: 'Giọng điệu không phù hợp',
}

const CAC_LY_DO = Object.keys(NHAN_LY_DO_DANH_GIA) as LyDoDanhGia[]

// Cùng giới hạn với java-core (`DanhGiaAiRequest`) và ai-service (`FeedbackRequest`)
const luocDo = z.object({
  reasonCode: z.enum(['WRONG_INFO', 'IRRELEVANT', 'INCOMPLETE', 'BAD_TONE'], {
    message: 'Chọn một lý do.',
  }),
  comment: z.string().max(2000, 'Nhận xét tối đa 2.000 ký tự.'),
  correctedAnswer: z.string().max(4000, 'Câu trả lời đúng tối đa 4.000 ký tự.'),
})

type GiaTri = z.infer<typeof luocDo>

/**
 * UC027 bước 2–4 — nhân viên chê một câu trả lời của tác tử AI. Mẫu M3.
 *
 * Bắt chọn **một trong bốn** lý do (bước 3); nhận xét và **câu trả lời đúng** không bắt buộc. Câu trả
 * lời đúng là thứ chỉ nhân viên nhập được — nó là nguồn phát hiện khoảng trống tri thức. Khen không mở
 * hộp thoại này: bắt chọn lý do khi khen chỉ làm người dùng bỏ giữa chừng (luồng phụ 3.1).
 *
 * Đánh giá lại cùng lượt thì máy chủ cập nhật dòng cũ của chính người đó (2.1) — hộp thoại nạp sẵn
 * đánh giá trước của mình nếu có.
 */
export function DanhGiaDialog({
  luotId,
  mo,
  onDoiMo,
  cauTraLoi,
  danhGiaCu,
}: {
  luotId: string
  mo: boolean
  onDoiMo: (m: boolean) => void
  /** Câu tác tử đã trả lời — nhắc lại trong hộp thoại để người chê không phải nhớ. */
  cauTraLoi?: string | null
  /** Đánh giá chê trước đó của chính mình, để sửa lại thay vì gõ lại từ đầu. */
  danhGiaCu?: DanhGiaAi | null
}) {
  const [danhGia, ketQua] = useDanhGiaLuotXuLyMutation()
  const form = useForm<GiaTri>({
    resolver: zodResolver(luocDo),
    defaultValues: giaTriDau(danhGiaCu),
  })
  const lyDo = form.watch('reasonCode')

  useEffect(() => {
    if (mo) {
      form.reset(giaTriDau(danhGiaCu))
      ketQua.reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mo, luotId])

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Câu trả lời này chưa ổn ở đâu?"
      moTa="Lý do giúp sửa kho tri thức và hiệu chỉnh tác tử. Câu trả lời đúng (nếu có) được dùng để tìm chỗ kho còn thiếu."
      form={form}
      loi={ketQua.error}
      dangGui={ketQua.isLoading}
      nhanGui="Gửi đánh giá"
      onGui={async (g) => {
        try {
          await danhGia({
            id: luotId,
            rating: 'NEGATIVE',
            reasonCode: g.reasonCode,
            comment: g.comment.trim() || null,
            correctedAnswer: g.correctedAnswer.trim() || null,
          }).unwrap()
        } catch {
          return // câu lỗi hiện trong hộp thoại qua `loi`; hộp thoại giữ nguyên
        }
        toast.success('Đã ghi nhận đánh giá chưa ổn.')
        onDoiMo(false)
      }}
    >
      {cauTraLoi && (
        <blockquote className="text-muted-foreground border-l-2 pl-3 text-[13px] leading-relaxed line-clamp-4">
          {cauTraLoi}
        </blockquote>
      )}

      <Field>
        <FieldLabel id="danh-gia-ly-do">Lý do</FieldLabel>
        <div role="radiogroup" aria-labelledby="danh-gia-ly-do" className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          {CAC_LY_DO.map((ma) => (
            <Button
              key={ma}
              type="button"
              role="radio"
              aria-checked={lyDo === ma}
              variant={lyDo === ma ? 'default' : 'outline'}
              size="sm"
              className="justify-start"
              onClick={() => form.setValue('reasonCode', ma, { shouldValidate: true })}
            >
              {NHAN_LY_DO_DANH_GIA[ma]}
            </Button>
          ))}
        </div>
        <FieldError errors={[form.formState.errors.reasonCode]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="danh-gia-nhan-xet">Nhận xét</FieldLabel>
        <Textarea id="danh-gia-nhan-xet" rows={2} {...form.register('comment')} />
        <FieldError errors={[form.formState.errors.comment]} />
      </Field>

      <Field>
        <FieldLabel htmlFor="danh-gia-cau-dung">Câu trả lời đúng</FieldLabel>
        <Textarea id="danh-gia-cau-dung" rows={3} {...form.register('correctedAnswer')} />
        <FieldDescription>Không bắt buộc. Khách không thấy câu này.</FieldDescription>
        <FieldError errors={[form.formState.errors.correctedAnswer]} />
      </Field>
    </FormDialog>
  )
}

function giaTriDau(cu?: DanhGiaAi | null): GiaTri {
  return {
    reasonCode: (cu?.rating === 'NEGATIVE' ? cu.reasonCode : undefined) as GiaTri['reasonCode'],
    comment: cu?.rating === 'NEGATIVE' ? (cu.comment ?? '') : '',
    correctedAnswer: cu?.rating === 'NEGATIVE' ? (cu.correctedAnswer ?? '') : '',
  }
}

/**
 * Cặp nút 👍/👎 của nhân viên cho một lượt. 👍 ghi ngay (không hỏi lý do — 3.1); 👎 mở
 * {@link DanhGiaDialog}. Nút đang sáng là đánh giá hiện tại của chính mình.
 */
export function NutDanhGia({
  luotId,
  cauTraLoi,
  cuaToi,
  gon = false,
}: {
  luotId: string
  cauTraLoi?: string | null
  /** Đánh giá hiện tại của người đang đăng nhập cho lượt này (nếu đã đánh giá). */
  cuaToi?: DanhGiaAi | null
  /** Dạng nhỏ dưới bong bóng tin ở hộp thư. */
  gon?: boolean
}) {
  const [danhGia, ketQua] = useDanhGiaLuotXuLyMutation()
  const [moChe, datMoChe] = useState(false)

  async function khen() {
    try {
      await danhGia({ id: luotId, rating: 'POSITIVE' }).unwrap()
      toast.success('Đã ghi nhận đánh giá tốt.')
    } catch (loi) {
      toast.error(laLoiTruyVan(loi) ? loi.message : 'Chưa ghi được đánh giá.')
    }
  }

  return (
    <>
      <span className="flex items-center gap-1">
        <Button
          variant={cuaToi?.rating === 'POSITIVE' ? 'secondary' : 'ghost'}
          size={gon ? 'icon-xs' : 'sm'}
          disabled={ketQua.isLoading}
          aria-label="Câu trả lời ổn"
          aria-pressed={cuaToi?.rating === 'POSITIVE'}
          onClick={() => void khen()}
        >
          <ThumbsUp className={cn(cuaToi?.rating === 'POSITIVE' && 'text-success')} />
          {!gon && 'Ổn'}
        </Button>
        <Button
          variant={cuaToi?.rating === 'NEGATIVE' ? 'secondary' : 'ghost'}
          size={gon ? 'icon-xs' : 'sm'}
          aria-label="Câu trả lời chưa ổn"
          aria-pressed={cuaToi?.rating === 'NEGATIVE'}
          onClick={() => datMoChe(true)}
        >
          <ThumbsDown className={cn(cuaToi?.rating === 'NEGATIVE' && 'text-destructive')} />
          {!gon && 'Chưa ổn'}
        </Button>
      </span>
      <DanhGiaDialog
        luotId={luotId}
        mo={moChe}
        onDoiMo={datMoChe}
        cauTraLoi={cauTraLoi}
        danhGiaCu={cuaToi}
      />
    </>
  )
}

/** Các đánh giá của người cho một lượt: ai đánh giá, lý do, nhận xét và câu trả lời đúng (bước 8). */
export function DanhSachDanhGia({ danhGia }: { danhGia: DanhGiaAi[] }) {
  if (danhGia.length === 0) return null
  return (
    <ul className="flex flex-col gap-1.5">
      {danhGia.map((d) => (
        <li key={d.id} className="flex flex-col gap-0.5 text-xs">
          <span className="text-muted-foreground flex flex-wrap items-center gap-1.5">
            {d.rating === 'POSITIVE' ? (
              <ThumbsUp className="text-success size-3.5" aria-label="Tốt" />
            ) : (
              <ThumbsDown className="text-destructive size-3.5" aria-label="Chưa ổn" />
            )}
            <span className="text-foreground font-medium">
              {d.ratedByType === 'CUSTOMER' ? 'Khách hàng' : (d.ratedByName ?? 'Nhân viên')}
            </span>
            {d.reasonCode && <span>· {NHAN_LY_DO_DANH_GIA[d.reasonCode]}</span>}
            {d.comment && <span>· “{d.comment}”</span>}
          </span>
          {d.correctedAnswer && (
            <span className="bg-success/8 rounded-md px-2 py-1 leading-relaxed">
              <span className="text-success font-medium">Câu trả lời đúng: </span>
              {d.correctedAnswer}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}
