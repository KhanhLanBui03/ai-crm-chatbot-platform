import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowRight, Info } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useDanhSachKhachHangQuery, useTaoKhachHangMutation } from '@/api/contacts'
import { useDanhSachNguoiDungQuery } from '@/api/platform'
import { useTaoLeadMutation } from '@/api/sales'
import { useAppSelector } from '@/app/store/hooks'
import { FormDialog } from '@/components/layout/FormDialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useTriHoan } from '@/hooks/useTriHoan'
import type { LeadDangMo } from '@/types/schema'

/** Ô số để trống là "chưa rõ", không phải 0 và không phải NaN. */
const so = (v: unknown) => (v === '' || v == null || Number.isNaN(v) ? undefined : Number(v))

const luocDo = z
  .object({
    cheDoKhach: z.enum(['co-san', 'moi']),
    contactId: z.string(),
    tenKhachMoi: z.string().max(200),
    sdtKhachMoi: z.string().max(20),
    interestedProduct: z.string().max(200, 'Tối đa 200 ký tự.'),
    budgetMin: z.number().min(0, 'Không âm.').optional(),
    budgetMax: z.number().min(0, 'Không âm.').optional(),
    urgency: z.enum(['LOW', 'MEDIUM', 'HIGH']),
    ownerUserId: z.string(),
  })
  .superRefine((v, ctx) => {
    if (v.cheDoKhach === 'co-san' && !v.contactId) {
      ctx.addIssue({ code: 'custom', path: ['contactId'], message: 'Chọn khách hàng.' })
    }
    if (v.cheDoKhach === 'moi' && !v.tenKhachMoi.trim() && !v.sdtKhachMoi.trim()) {
      ctx.addIssue({ code: 'custom', path: ['tenKhachMoi'], message: 'Nhập tên hoặc số điện thoại.' })
    }
    if (v.budgetMin != null && v.budgetMax != null && v.budgetMin > v.budgetMax) {
      ctx.addIssue({
        code: 'custom',
        path: ['budgetMax'],
        message: 'Ngân sách tối đa phải lớn hơn hoặc bằng tối thiểu.',
      })
    }
  })

type GiaTri = z.infer<typeof luocDo>

const MAC_DINH: GiaTri = {
  cheDoKhach: 'co-san',
  contactId: '',
  tenKhachMoi: '',
  sdtKhachMoi: '',
  interestedProduct: '',
  urgency: 'MEDIUM',
  ownerUserId: '',
}

/** Mở từ Hộp thư: khách và hội thoại nguồn đã biết, không cho chọn lại. */
export interface NguonHoiThoai {
  contactId: string
  contactName: string
  conversationId: string
}

/**
 * SCR043 — tạo lead thủ công (UC032 luồng 1a–2a). Ba lối vào dùng chung hộp thoại này:
 * trang Lead + khách có sẵn, trang Lead + khách mới (tạo hồ sơ khách bằng API của UC016 rồi tạo
 * lead), và nút "Tạo lead" trong Hộp thư (`tuHoiThoai` — tự gắn khách và hội thoại nguồn).
 *
 * Không có ô nhập điểm: điểm do mô hình chấm (UC030). Người phụ trách mặc định là người tạo; chỉ
 * quản trị viên chọn được người khác — máy chủ cũng chặn, ô chọn ẩn đi chỉ để khỏi bấm nhầm.
 */
export function CreateLeadDialog({
  mo,
  onDoiMo,
  tuHoiThoai,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
  tuHoiThoai?: NguonHoiThoai
}) {
  const dieuHuong = useNavigate()
  const laQuanTri = useAppSelector((s) => s.auth.nguoiDung?.roleCode === 'TENANT_ADMIN')
  const [tao, ketQua] = useTaoLeadMutation()
  const [taoKhach, ketQuaKhach] = useTaoKhachHangMutation()
  const [oTim, datOTim] = useState('')
  const [trung, datTrung] = useState<(LeadDangMo & { thongDiep: string }) | null>(null)
  // Khách vừa tạo ở thẻ "Khách mới" — tạo lead lỗi rồi bấm lại thì dùng lại, không sinh hồ sơ trùng
  const khachVuaTao = useRef<{ khoa: string; id: string } | null>(null)
  const tuKhoa = useTriHoan(oTim)
  const khachHang = useDanhSachKhachHangQuery({ tuKhoa }, { skip: !!tuHoiThoai || tuKhoa.length < 2 })
  const nguoiDung = useDanhSachNguoiDungQuery({ trangThai: 'ACTIVE' }, { skip: !laQuanTri || !mo })

  const form = useForm<GiaTri>({ resolver: zodResolver(luocDo), defaultValues: MAC_DINH })
  const cheDo = form.watch('cheDoKhach')
  const daChon = khachHang.data?.items.find((k) => k.id === form.watch('contactId'))

  // Mỗi lần mở là một lần nhập mới; mở từ Hộp thư thì gắn sẵn khách của hội thoại
  useEffect(() => {
    if (!mo) return
    form.reset({ ...MAC_DINH, contactId: tuHoiThoai?.contactId ?? '' })
    datOTim('')
    datTrung(null)
    khachVuaTao.current = null
    ketQua.reset()
    ketQuaKhach.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mo, tuHoiThoai?.contactId])

  const loiKhac = trung ? null : (ketQua.error ?? ketQuaKhach.error)

  return (
    <FormDialog
      mo={mo}
      onDoiMo={onDoiMo}
      tieuDe="Tạo lead"
      moTa={
        tuHoiThoai
          ? 'Ghi nhận khách của hội thoại này là một cơ hội — lead sẽ gắn với hội thoại để truy ngược về sau.'
          : 'Dùng khi cơ hội đến từ ngoài kênh chat — gọi điện, gặp trực tiếp, hội chợ.'
      }
      form={form}
      loi={loiKhac}
      dangGui={ketQua.isLoading || ketQuaKhach.isLoading}
      nhanGui="Tạo lead"
      onGui={async (g) => {
        datTrung(null)
        try {
          let contactId = g.contactId
          const khoaKhach = `${g.tenKhachMoi.trim()}|${g.sdtKhachMoi.trim()}`
          if (!tuHoiThoai && g.cheDoKhach === 'moi' && khachVuaTao.current?.khoa === khoaKhach) {
            contactId = khachVuaTao.current.id
          } else if (!tuHoiThoai && g.cheDoKhach === 'moi') {
            const kq = await taoKhach({
              fullName: g.tenKhachMoi.trim() || null,
              phone: g.sdtKhachMoi.trim() || null,
              primaryChannel: 'PHONE',
            }).unwrap()
            contactId = kq.contact.id
            khachVuaTao.current = { khoa: khoaKhach, id: contactId }
            if (kq.duplicateCandidates.length > 0) {
              toast.warning('Đã tạo hồ sơ khách mới, nhưng có hồ sơ trùng số điện thoại/thư — kiểm tra ở Danh bạ.')
            }
          }
          const lead = await tao({
            contactId,
            sourceConversationId: tuHoiThoai?.conversationId ?? null,
            interestedProduct: g.interestedProduct.trim() || null,
            budgetMin: g.budgetMin ?? null,
            budgetMax: g.budgetMax ?? null,
            urgency: g.urgency,
            ownerUserId: g.ownerUserId || null,
          }).unwrap()
          onDoiMo(false)
          if (tuHoiThoai) {
            toast.success('Đã tạo lead.', {
              action: { label: 'Mở lead', onClick: () => dieuHuong(`/ban-hang/co-hoi-tiem-nang/${lead.id}`) },
            })
          } else {
            toast.success('Đã tạo lead.')
            dieuHuong(`/ban-hang/co-hoi-tiem-nang/${lead.id}`)
          }
        } catch (loi) {
          // UC032: một khách một lead mở — dẫn người dùng tới lead đang có thay vì báo lỗi suông
          if (laLoiTruyVan(loi) && loi.code === 'LEAD_ALREADY_OPEN' && loi.data) {
            datTrung({ ...(loi.data as LeadDangMo), thongDiep: loi.message })
          }
        }
      }}
    >
      {trung && (
        <Alert>
          <Info />
          <AlertDescription className="flex flex-col items-start gap-2">
            <span>{trung.thongDiep} Cập nhật lead đó thay vì tạo thêm.</span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                onDoiMo(false)
                dieuHuong(`/ban-hang/co-hoi-tiem-nang/${trung.leadId}`)
              }}
            >
              Mở lead đang có <ArrowRight />
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {tuHoiThoai ? (
        <Field>
          <FieldLabel>Khách hàng</FieldLabel>
          <span className="text-[13px] font-medium">{tuHoiThoai.contactName}</span>
        </Field>
      ) : (
        <>
          <Tabs
            value={cheDo}
            onValueChange={(v) => {
              form.setValue('cheDoKhach', v as GiaTri['cheDoKhach'])
              form.clearErrors()
            }}
          >
            <TabsList>
              <TabsTrigger value="co-san">Khách có sẵn</TabsTrigger>
              <TabsTrigger value="moi">Khách mới</TabsTrigger>
            </TabsList>
          </Tabs>

          {cheDo === 'co-san' ? (
            <Field>
              <FieldLabel htmlFor="ld-khach">Khách hàng</FieldLabel>
              <Input
                id="ld-khach"
                placeholder="Gõ tên, số điện thoại hoặc thư để tìm…"
                value={daChon ? (daChon.fullName ?? daChon.phone ?? '') : oTim}
                onChange={(e) => {
                  datOTim(e.target.value)
                  form.setValue('contactId', '')
                }}
              />
              {!daChon && tuKhoa.length >= 2 && (
                <div className="flex max-h-40 flex-col gap-1 overflow-y-auto rounded-lg border p-1">
                  {khachHang.data?.items.length === 0 ? (
                    <span className="text-muted-foreground px-2 py-3 text-center text-[13px]">
                      Không tìm thấy — chuyển sang thẻ &quot;Khách mới&quot; để tạo luôn.
                    </span>
                  ) : (
                    khachHang.data?.items.map((k) => (
                      <button
                        key={k.id}
                        type="button"
                        className="hover:bg-muted flex flex-col rounded-md px-2 py-1.5 text-left"
                        onClick={() => form.setValue('contactId', k.id, { shouldValidate: true })}
                      >
                        <span className="text-[13px] font-medium">{k.fullName ?? 'Chưa có tên'}</span>
                        <span className="text-muted-foreground text-xs">
                          {[k.phone, k.email].filter(Boolean).join(' · ')}
                        </span>
                      </button>
                    ))
                  )}
                </div>
              )}
              <FieldError errors={[form.formState.errors.contactId]} />
            </Field>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="ld-ten">Tên khách</FieldLabel>
                <Input id="ld-ten" placeholder="Nguyễn Văn A" {...form.register('tenKhachMoi')} />
                <FieldError errors={[form.formState.errors.tenKhachMoi]} />
              </Field>
              <Field>
                <FieldLabel htmlFor="ld-sdt">Số điện thoại</FieldLabel>
                <Input id="ld-sdt" placeholder="0901 234 567" {...form.register('sdtKhachMoi')} />
              </Field>
            </div>
          )}
        </>
      )}

      <Field>
        <FieldLabel htmlFor="ld-sp">Sản phẩm quan tâm</FieldLabel>
        <Input id="ld-sp" placeholder="Ví dụ: Gói Chuyên nghiệp 50 người dùng" {...form.register('interestedProduct')} />
        <FieldError errors={[form.formState.errors.interestedProduct]} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field>
          <FieldLabel htmlFor="ld-min">Ngân sách từ</FieldLabel>
          <Input
            id="ld-min"
            type="number"
            min={0}
            step={100000}
            {...form.register('budgetMin', { setValueAs: so })}
          />
          <FieldError errors={[form.formState.errors.budgetMin]} />
        </Field>
        <Field>
          <FieldLabel htmlFor="ld-max">đến</FieldLabel>
          <Input
            id="ld-max"
            type="number"
            min={0}
            step={100000}
            {...form.register('budgetMax', { setValueAs: so })}
          />
          <FieldError errors={[form.formState.errors.budgetMax]} />
        </Field>
      </div>

      <Field>
        <FieldLabel htmlFor="ld-gap">Mức gấp</FieldLabel>
        <Select
          value={form.watch('urgency')}
          onValueChange={(v) => form.setValue('urgency', v as GiaTri['urgency'])}
        >
          <SelectTrigger id="ld-gap">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="HIGH">Cao</SelectItem>
            <SelectItem value="MEDIUM">Trung bình</SelectItem>
            <SelectItem value="LOW">Thấp</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      {laQuanTri && (
        <Field>
          <FieldLabel htmlFor="ld-chu">Người phụ trách</FieldLabel>
          <Select
            value={form.watch('ownerUserId') || 'toi'}
            onValueChange={(v) => form.setValue('ownerUserId', v === 'toi' ? '' : v)}
          >
            <SelectTrigger id="ld-chu">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="toi">Tôi phụ trách</SelectItem>
              {nguoiDung.data?.items.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.fullName ?? u.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )}

      <Alert>
        <AlertDescription>
          Lead nhập tay <strong>chưa có điểm tiềm năng</strong> — điểm do mô hình chấm từ tín hiệu
          hội thoại (UC030), không nhập tay.
        </AlertDescription>
      </Alert>
    </FormDialog>
  )
}
