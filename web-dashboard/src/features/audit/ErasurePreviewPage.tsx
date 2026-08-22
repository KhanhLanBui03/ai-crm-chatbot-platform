import { Search, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useXemTruocPhamViXoaQuery } from '@/api/audit'
import { useDanhSachKhachHangQuery } from '@/api/contacts'
import { StatusPage } from '@/components/layout/StatusPage'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { StatusChip } from '@/components/ui/status-chip'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useTriHoan } from '@/hooks/useTriHoan'
import { NHAN_THAO_TAC_XOA } from '@/features/audit/nhan'
import type { MucXoa } from '@/types/schema'

/**
 * SCR055 — xem trước phạm vi ảnh hưởng trước khi xoá. Mẫu M6.
 *
 * Màn này **không xoá gì cả**, và phải nói rõ điều đó ở ngay dòng đầu: nó tồn tại để người duyệt
 * biết trước mình sắp phá vỡ những gì. Đọc bảng này rồi mới bấm thực thi ở SCR058.
 *
 * Ba thao tác hiện tách bạch chứ không gộp thành một chữ "xoá". `KEEP_AGGREGATE` giữ nguyên là
 * chỗ dễ bị hiểu nhầm nhất — người xem thấy dòng `analytics.revenue_monthly` mà tưởng nó cũng bị
 * xoá thì sẽ tưởng báo cáo doanh thu quý sẽ hụt đi.
 *
 * Ghi chú về hệ thống bên ngoài là bắt buộc, không phải phần đọc thêm: phạm vi xoá **không vươn
 * tới** dữ liệu đã gửi đi qua công cụ MCP, và im lặng về giới hạn đó là để người duyệt ký vào một
 * lời cam kết không đúng với khách.
 */
export function ErasurePreviewPage() {
  const dieuHuong = useNavigate()
  const [oTim, datOTim] = useState('')
  const [daChon, datDaChon] = useState<{ id: string; ten: string } | null>(null)
  const tuKhoa = useTriHoan(oTim)

  const khachHang = useDanhSachKhachHangQuery({ tuKhoa }, { skip: tuKhoa.length < 2 })
  const phamVi = useXemTruocPhamViXoaQuery(daChon?.id ?? '', { skip: !daChon })

  if (!daChon) {
    return (
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="flex max-w-2xl flex-col gap-4 p-4">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight">Xem trước phạm vi xoá</h1>
            <p className="text-muted-foreground text-[13px]">
              Chọn một khách hàng để xem đúng những bảng nào bị đụng tới nếu thực hiện quyền xoá.
              Màn này chỉ đọc — không xoá gì cả.
            </p>
          </div>

          <div className="relative">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
            <Input
              className="pl-8"
              placeholder="Tìm khách theo tên, số điện thoại hoặc thư…"
              value={oTim}
              onChange={(e) => datOTim(e.target.value)}
            />
          </div>

          {tuKhoa.length >= 2 && (
            <Card>
              <CardContent className="flex flex-col gap-1 p-2">
                {khachHang.data?.items.length === 0 ? (
                  <span className="text-muted-foreground px-2 py-3 text-center text-[13px]">
                    Không tìm thấy khách hàng nào khớp.
                  </span>
                ) : (
                  khachHang.data?.items.map((k) => (
                    <button
                      key={k.id}
                      type="button"
                      onClick={() =>
                        datDaChon({ id: k.id, ten: k.fullName ?? 'Khách chưa có tên' })
                      }
                      className="hover:bg-muted flex flex-col rounded-md px-2 py-1.5 text-left transition-colors"
                    >
                      <span className="text-[13px] font-medium">
                        {k.fullName ?? 'Khách chưa có tên'}
                      </span>
                      <span className="text-muted-foreground text-xs">
                        {[k.phone, k.email].filter(Boolean).join(' · ') || 'Không có thông tin liên hệ'}
                      </span>
                    </button>
                  ))
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    )
  }

  const muc = phamVi.data ?? []
  const soXoaHan = muc.filter((m) => m.action === 'DELETE').reduce((t, m) => t + (m.affectedRows ?? 0), 0)
  const soAnDanh = muc
    .filter((m) => m.action === 'ANONYMIZE')
    .reduce((t, m) => t + (m.affectedRows ?? 0), 0)
  const soGiuLai = muc.filter((m) => m.action === 'KEEP_AGGREGATE').length

  return (
    <StatusPage
      trangThai={phamVi.isLoading ? 'dang-xu-ly' : 'cho-thao-tac'}
      tieuDe={
        phamVi.isLoading
          ? 'Đang dò phạm vi ảnh hưởng…'
          : `Xoá dữ liệu của ${daChon.ten} sẽ đụng tới ${muc.length} bảng`
      }
      moTa={
        phamVi.isLoading
          ? 'Quét qua toàn bộ lược đồ để tìm những bảng có tham chiếu tới khách hàng này.'
          : `${soXoaHan.toLocaleString('vi-VN')} dòng bị xoá hẳn, ${soAnDanh.toLocaleString('vi-VN')} dòng được ẩn danh hoá, ${soGiuLai} bảng số liệu tổng hợp giữ nguyên. Chưa có gì bị xoá ở bước này.`
      }
      thaoTacChinh={{
        nhan: 'Tới danh sách yêu cầu xoá',
        onClick: () => dieuHuong('/kiem-toan/yeu-cau-xoa'),
      }}
      thaoTacPhu={{ nhan: 'Chọn khách khác', onClick: () => datDaChon(null) }}
      chiTiet={
        phamVi.isLoading ? undefined : (
          <div className="flex flex-col gap-3 text-left">
            <Alert>
              <TriangleAlert />
              <AlertTitle>Phạm vi xoá dừng ở hệ thống này</AlertTitle>
              <AlertDescription>
                Dữ liệu đã gửi sang hệ thống bên ngoài qua công cụ MCP không nằm trong phạm vi trên.
                Phải gửi yêu cầu xoá riêng cho đơn vị đó và lưu văn bản xác nhận vào hồ sơ.
              </AlertDescription>
            </Alert>

            <Card>
              <CardContent className="flex flex-col gap-2">
                {muc.map((m) => (
                  <HangBang key={`${m.targetSchema}.${m.targetTable}`} muc={m} />
                ))}
              </CardContent>
            </Card>
          </div>
        )
      }
    />
  )
}

function HangBang({ muc }: { muc: MucXoa }) {
  const t = NHAN_THAO_TAC_XOA[muc.action]
  return (
    <div className="flex items-center gap-2">
      <span className="min-w-0 flex-1 truncate font-mono text-xs">
        <span className="text-muted-foreground">{muc.targetSchema}.</span>
        {muc.targetTable}
      </span>
      <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
        {muc.affectedRows == null ? '—' : `${muc.affectedRows.toLocaleString('vi-VN')} dòng`}
      </span>
      <Tooltip>
        <TooltipTrigger asChild>
          <span>
            <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-64">{t.moTa}</TooltipContent>
      </Tooltip>
    </div>
  )
}
