import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { useCapNhatDoanhNghiepMutation, useHoSoDoanhNghiepQuery } from '@/api/platform'
import { SettingsPage } from '@/components/layout/SettingsPage'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAppSelector } from '@/app/store/hooks'
import type { CheDoPhanCong, DoanhNghiep, GiongDieuAi } from '@/types/schema'

const GIONG_DIEU: Record<GiongDieuAi, { nhan: string; moTa: string }> = {
  PROFESSIONAL: { nhan: 'Chuyên nghiệp', moTa: 'Xưng hô trang trọng, câu đầy đủ chủ vị.' },
  FRIENDLY: { nhan: 'Thân thiện', moTa: 'Gần gũi, dùng "mình" và "bạn".' },
  CONCISE: { nhan: 'Ngắn gọn', moTa: 'Trả lời thẳng, ít câu xã giao.' },
}

const CHE_DO_PHAN_CONG: Record<CheDoPhanCong, { nhan: string; moTa: string }> = {
  LEAST_BUSY: {
    nhan: 'Người ít việc nhất',
    moTa: 'Giao cho nhân viên đang phụ trách ít hội thoại đang mở nhất. Không cần cấu hình gì thêm.',
  },
  ROUND_ROBIN: {
    nhan: 'Luân phiên',
    moTa: 'Chia đều theo vòng, không nhìn tải hiện tại. Công bằng về số lượng, không công bằng về công sức.',
  },
  MANUAL: {
    nhan: 'Thủ công',
    moTa: 'Hội thoại vào hàng chờ chung, nhân viên tự nhận. Chọn khi đội nhỏ và ai cũng thấy hết hàng chờ.',
  },
}

const MUI_GIO = ['Asia/Ho_Chi_Minh', 'Asia/Bangkok', 'Asia/Singapore', 'UTC']

/**
 * SCR007 — hồ sơ doanh nghiệp. Mẫu M4.
 *
 * Chỉ `TENANT_ADMIN` sửa được. Nhân viên vẫn xem được (họ cần biết giờ làm việc và giọng điệu
 * mà tác tử AI đang dùng), nhưng ở chế độ chỉ đọc — ẩn hẳn trang thì họ lại đi hỏi quản trị viên.
 */
export function TenantProfilePage() {
  const laQuanTri = useAppSelector((s) => s.auth.nguoiDung?.roleCode === 'TENANT_ADMIN')
  const truyVan = useHoSoDoanhNghiepQuery()
  const [luu, ketQua] = useCapNhatDoanhNghiepMutation()

  const [nhap, datNhap] = useState<DoanhNghiep | null>(null)

  // Đồng bộ một chiều: dữ liệu máy chủ về thì nạp vào form, nhưng không ghi đè khi người dùng
  // đang gõ dở — `truyVan.data` chỉ đổi tham chiếu khi thật sự có dữ liệu mới.
  useEffect(() => {
    if (truyVan.data) datNhap(truyVan.data)
  }, [truyVan.data])

  const goc = truyVan.data
  const coThayDoi = Boolean(nhap && goc && JSON.stringify(nhap) !== JSON.stringify(goc))
  const dat = <K extends keyof DoanhNghiep>(khoa: K, giaTri: DoanhNghiep[K]) =>
    datNhap((cu) => (cu ? { ...cu, [khoa]: giaTri } : cu))

  return (
    <SettingsPage
      tieuDe="Hồ sơ doanh nghiệp"
      moTa="Thông tin dùng chung cho mọi kênh và cho cách tác tử AI xưng hô với khách."
      dangTai={truyVan.isLoading || !nhap}
      coThayDoi={coThayDoi}
      dangLuu={ketQua.isLoading}
      loi={ketQua.error}
      chiDoc={
        laQuanTri
          ? undefined
          : { lyDo: 'Chỉ quản trị doanh nghiệp sửa được hồ sơ. Bạn đang xem ở chế độ chỉ đọc.' }
      }
      onHuy={() => goc && datNhap(goc)}
      onLuu={async () => {
        if (!nhap) return
        await luu(nhap).unwrap()
        toast.success('Đã lưu hồ sơ doanh nghiệp.')
      }}
      muc={[
        {
          tieuDe: 'Thông tin chung',
          noiDung: nhap && (
            <>
              <Field>
                <FieldLabel htmlFor="dn-ten">Tên doanh nghiệp</FieldLabel>
                <Input
                  id="dn-ten"
                  value={nhap.name}
                  onChange={(e) => dat('name', e.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="dn-nganh">Ngành hàng</FieldLabel>
                <Input
                  id="dn-nganh"
                  value={nhap.industry ?? ''}
                  onChange={(e) => dat('industry', e.target.value || null)}
                />
                <FieldDescription>
                  Tác tử AI dùng thông tin này để chọn cách diễn đạt phù hợp với lĩnh vực.
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="dn-mui-gio">Múi giờ</FieldLabel>
                <Select value={nhap.timezone} onValueChange={(v) => dat('timezone', v)}>
                  <SelectTrigger id="dn-mui-gio">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MUI_GIO.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Mọi mốc thời gian trên báo cáo và giờ làm việc đều tính theo múi giờ này.
                </FieldDescription>
              </Field>
            </>
          ),
        },
        {
          tieuDe: 'Tác tử AI',
          moTa: 'Cách tác tử trả lời khách, và khi nào thì nó phải nhường lại cho người.',
          noiDung: nhap && (
            <>
              <Field>
                <FieldLabel htmlFor="dn-giong">Giọng điệu</FieldLabel>
                <Select
                  value={nhap.aiTone ?? 'FRIENDLY'}
                  onValueChange={(v) => dat('aiTone', v as GiongDieuAi)}
                >
                  <SelectTrigger id="dn-giong">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(GIONG_DIEU).map(([ma, g]) => (
                      <SelectItem key={ma} value={ma}>
                        {g.nhan}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldDescription>
                  {GIONG_DIEU[nhap.aiTone ?? 'FRIENDLY'].moTa}
                </FieldDescription>
              </Field>

              <Field>
                <FieldLabel htmlFor="dn-tu-choi">
                  Số lần từ chối liên tiếp trước khi chuyển cho người
                </FieldLabel>
                <Input
                  id="dn-tu-choi"
                  type="number"
                  min={1}
                  className="max-w-28"
                  value={nhap.refusalHandoffThreshold ?? 2}
                  onChange={(e) => dat('refusalHandoffThreshold', Number(e.target.value))}
                />
                <FieldDescription>
                  Tác tử từ chối liên tiếp nghĩa là kho tri thức chưa phủ câu hỏi này — để nó thử
                  thêm lần nữa chỉ làm khách bực thêm.
                </FieldDescription>
              </Field>
            </>
          ),
        },
        {
          tieuDe: 'Cơ hội tiềm năng',
          moTa: 'Khi nào một hội thoại tự trở thành cơ hội tiềm năng trong CRM.',
          noiDung: nhap && (
            <>
              <Field>
                <FieldLabel htmlFor="dn-nguong">Ngưỡng điểm tự tạo</FieldLabel>
                <Input
                  id="dn-nguong"
                  type="number"
                  min={0}
                  max={100}
                  className="max-w-28"
                  value={nhap.leadScoreThreshold ?? 70}
                  onChange={(e) => dat('leadScoreThreshold', Number(e.target.value))}
                />
                <FieldDescription>
                  Từ 0 đến 100. Hạ ngưỡng xuống quá thấp là ngập CRM bằng cơ hội không có thật.
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="dn-gioi-han">Giới hạn mỗi ngày</FieldLabel>
                <Input
                  id="dn-gioi-han"
                  type="number"
                  min={0}
                  className="max-w-28"
                  value={nhap.autoLeadDailyLimit ?? 50}
                  onChange={(e) => dat('autoLeadDailyLimit', Number(e.target.value))}
                />
                <FieldDescription>
                  Chốt chặn cuối: một đợt tin nhắn bất thường không thể sinh ra hàng nghìn cơ hội.
                </FieldDescription>
              </Field>
            </>
          ),
        },
        {
          tieuDe: 'Phân công',
          moTa: 'Cách chọn nhân viên khi tác tử AI chuyển giao hội thoại hoặc khi có cơ hội tiềm năng mới.',
          noiDung: nhap && (
            <Field>
              <FieldLabel htmlFor="dn-phan-cong">Chế độ phân công</FieldLabel>
              <Select
                value={nhap.assignmentMode ?? 'LEAST_BUSY'}
                onValueChange={(v) => dat('assignmentMode', v as CheDoPhanCong)}
              >
                <SelectTrigger id="dn-phan-cong" className="max-w-64">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CHE_DO_PHAN_CONG).map(([ma, { nhan }]) => (
                    <SelectItem key={ma} value={ma}>
                      {nhan}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FieldDescription>
                {CHE_DO_PHAN_CONG[nhap.assignmentMode ?? 'LEAST_BUSY'].moTa}
              </FieldDescription>
            </Field>
          ),
        },
        {
          tieuDe: 'Lưu trữ dữ liệu',
          moTa: 'Nghị định 13/2023/NĐ-CP — dữ liệu cá nhân chỉ được giữ trong thời hạn cần thiết.',
          noiDung: nhap && (
            <Field>
              <FieldLabel htmlFor="dn-luu-tru">Giữ tin nhắn trong (ngày)</FieldLabel>
              <Input
                id="dn-luu-tru"
                type="number"
                min={1}
                className="max-w-28"
                value={nhap.messageRetentionDays ?? ''}
                placeholder="Vô thời hạn"
                onChange={(e) =>
                  dat('messageRetentionDays', e.target.value ? Number(e.target.value) : null)
                }
              />
              <FieldDescription>
                Bỏ trống là giữ vô thời hạn. Quá hạn thì tin nhắn bị xoá tự động, không phục hồi
                được — và số liệu thống kê đã tổng hợp thì vẫn giữ.
              </FieldDescription>
            </Field>
          ),
        },
      ]}
    />
  )
}
