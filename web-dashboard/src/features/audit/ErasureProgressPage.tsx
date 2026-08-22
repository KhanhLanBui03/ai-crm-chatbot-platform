import { format } from 'date-fns'
import { Download, FileCheck2, Play, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { useChiTietYeuCauXoaQuery } from '@/api/audit'
import { DetailPage, HangThongTin } from '@/components/layout/DetailPage'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { StatusChip } from '@/components/ui/status-chip'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ExecuteErasureDialog } from '@/features/audit/ExecuteErasureDialog'
import {
  NHAN_THAO_TAC_XOA,
  NHAN_TRANG_THAI_MUC,
  NHAN_TRANG_THAI_XOA,
} from '@/features/audit/nhan'
import type { MucXoa } from '@/types/schema'

/**
 * SCR057 — tiến độ xoá theo từng bảng. Mẫu M2.
 *
 * Bảng này là lý do `erasure_items` tồn tại thành một bảng riêng thay vì một cờ trên yêu cầu:
 * khi xoá hỏng giữa chừng, nó là thứ duy nhất cho biết chính xác chỗ nào đã xong, để chạy lại
 * đúng phần dở dang thay vì để dữ liệu ở trạng thái nửa vời — hoặc tệ hơn, chạy lại từ đầu và xoá
 * chồng lên những gì đã xoá.
 *
 * Dùng `currentData` chứ không phải `data`: đổi sang một yêu cầu khác mà hiện tiến độ của yêu cầu
 * trước là hiển thị dữ liệu của **khách khác** dưới tên khách này, ở đúng màn hình mà nhầm lẫn ấy
 * nguy hiểm nhất.
 */
export function ErasureProgressPage() {
  const { id = '' } = useParams()
  const [tab, datTab] = useState('tien-do')
  const [moThucThi, datMoThucThi] = useState(false)

  const truyVan = useChiTietYeuCauXoaQuery(id, { skip: !id })
  const y = truyVan.currentData

  const muc = y?.items ?? []
  const xong = muc.filter((m) => m.status === 'DONE').length
  const hong = muc.filter((m) => m.status === 'FAILED')
  const tyLe = muc.length > 0 ? (xong / muc.length) * 100 : 0
  const daHoanTat = y?.status === 'COMPLETED'

  return (
    <>
      <DetailPage
        dangTai={truyVan.isLoading || !y}
        quayLai={{ duongDan: '/kiem-toan/yeu-cau-xoa', nhan: 'Yêu cầu xoá dữ liệu cá nhân' }}
        tieuDe={y?.contactName ?? 'Yêu cầu xoá'}
        phuDe={y?.legalBasis ?? undefined}
        chip={
          y ? (
            <StatusChip sacThai={NHAN_TRANG_THAI_XOA[y.status].sacThai}>
              {NHAN_TRANG_THAI_XOA[y.status].nhan}
            </StatusChip>
          ) : undefined
        }
        thaoTacChinh={
          daHoanTat
            ? { nhan: 'Tải biên bản xác nhận', BieuTuong: Download, onClick: () => {} }
            : {
                nhan: y?.status === 'PARTIALLY_FAILED' ? 'Chạy lại phần còn lại' : 'Thực thi xoá',
                BieuTuong: Play,
                bienThe: 'destructive',
                onClick: () => datMoThucThi(true),
              }
        }
        tab={[
          {
            khoa: 'tien-do',
            nhan: 'Tiến độ theo bảng',
            soLuong: muc.length,
            noiDung: (
              <div className="flex flex-col gap-3">
                {hong.length > 0 && (
                  <Alert variant="destructive">
                    <TriangleAlert />
                    <AlertTitle>
                      Xoá dừng lại ở {hong.length} bảng — dữ liệu đang ở trạng thái nửa vời
                    </AlertTitle>
                    <AlertDescription>
                      {hong[0].errorMessage ??
                        'Không rõ nguyên nhân. Xem nhật ký kiểm toán để tra vết.'}
                    </AlertDescription>
                  </Alert>
                )}

                <Card>
                  <CardContent className="flex flex-col gap-2">
                    <div className="flex items-baseline justify-between">
                      <span className="text-[13px] font-medium">
                        {xong}/{muc.length} bảng đã xử lý xong
                      </span>
                      <span className="text-muted-foreground text-xs tabular-nums">
                        {tyLe.toFixed(0)}%
                      </span>
                    </div>
                    <Progress value={tyLe} className="h-1.5" />
                  </CardContent>
                </Card>

                <Card className="p-0">
                  <CardContent className="p-0">
                    <div className="min-w-0 overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Bảng</TableHead>
                            <TableHead>Thao tác</TableHead>
                            <TableHead>Số dòng</TableHead>
                            <TableHead>Trạng thái</TableHead>
                            <TableHead>Thực hiện lúc</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {muc.map((m) => (
                            <HangMuc key={`${m.targetSchema}.${m.targetTable}`} muc={m} />
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              </div>
            ),
          },
          {
            khoa: 'ho-so',
            nhan: 'Hồ sơ pháp lý',
            noiDung: (
              <div className="flex max-w-2xl flex-col gap-3">
                <Alert>
                  <TriangleAlert />
                  <AlertTitle>Phạm vi xoá dừng ở hệ thống này</AlertTitle>
                  <AlertDescription>
                    {y?.externalSystemsNote ??
                      'Không ghi nhận hệ thống bên ngoài nào đã nhận dữ liệu của khách hàng này.'}
                  </AlertDescription>
                </Alert>

                <Card>
                  <CardContent className="flex flex-col">
                    <HangThongTin nhan="Căn cứ pháp lý">{y?.legalBasis ?? '—'}</HangThongTin>
                    <HangThongTin nhan="Người xác minh danh tính">
                      {y?.identityVerifiedByName ?? 'Chưa xác minh'}
                    </HangThongTin>
                    <HangThongTin nhan="Xác minh lúc">
                      {y?.identityVerifiedAt
                        ? format(new Date(y.identityVerifiedAt), 'HH:mm dd/MM/yyyy')
                        : '—'}
                    </HangThongTin>
                    <HangThongTin nhan="Khách yêu cầu lúc">
                      {y ? format(new Date(y.requestedAt), 'HH:mm dd/MM/yyyy') : '—'}
                    </HangThongTin>
                    <HangThongTin nhan="Bắt đầu xoá">
                      {y?.startedAt ? format(new Date(y.startedAt), 'HH:mm dd/MM/yyyy') : 'Chưa chạy'}
                    </HangThongTin>
                    <HangThongTin nhan="Hoàn tất lúc">
                      {y?.completedAt
                        ? format(new Date(y.completedAt), 'HH:mm dd/MM/yyyy')
                        : 'Chưa hoàn tất'}
                    </HangThongTin>
                  </CardContent>
                </Card>

                {y?.certificateUri && (
                  <Card>
                    <CardContent className="flex items-center gap-3">
                      <FileCheck2 className="text-success size-5 shrink-0" />
                      <div className="flex min-w-0 flex-1 flex-col">
                        <span className="text-[13px] font-medium">Biên bản xác nhận đã xoá</span>
                        <span className="text-muted-foreground truncate font-mono text-xs">
                          {y.certificateUri}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            ),
          },
        ]}
        tabHienTai={tab}
        onDoiTab={datTab}
        cotPhu={
          y ? (
            <div className="flex flex-col gap-3">
              <div className="flex flex-col">
                <HangThongTin nhan="Mã yêu cầu">
                  <span className="font-mono text-xs">{y.id}</span>
                </HangThongTin>
                <HangThongTin nhan="Mã khách hàng">
                  <span className="font-mono text-xs">{y.contactId.slice(0, 8)}</span>
                </HangThongTin>
              </div>

              <Card>
                <CardContent className="flex flex-col gap-2">
                  <span className="text-muted-foreground text-xs">Phân bố thao tác</span>
                  {(['DELETE', 'ANONYMIZE', 'KEEP_AGGREGATE'] as const).map((tt) => {
                    const cua = muc.filter((m) => m.action === tt)
                    const t = NHAN_THAO_TAC_XOA[tt]
                    return (
                      <div key={tt} className="flex items-center justify-between text-xs">
                        <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
                        <span className="tabular-nums">
                          {cua.length} bảng ·{' '}
                          {cua.reduce((s, m) => s + (m.affectedRows ?? 0), 0).toLocaleString('vi-VN')}{' '}
                          dòng
                        </span>
                      </div>
                    )
                  })}
                </CardContent>
              </Card>
            </div>
          ) : undefined
        }
      />

      <ExecuteErasureDialog
        yeuCau={moThucThi ? (y ?? null) : null}
        onDong={() => datMoThucThi(false)}
      />
    </>
  )
}

function HangMuc({ muc }: { muc: MucXoa }) {
  const t = NHAN_THAO_TAC_XOA[muc.action]
  const tt = NHAN_TRANG_THAI_MUC[muc.status] ?? NHAN_TRANG_THAI_MUC.PENDING
  return (
    <TableRow>
      <TableCell>
        <span className="font-mono text-xs">
          <span className="text-muted-foreground">{muc.targetSchema}.</span>
          {muc.targetTable}
        </span>
      </TableCell>
      <TableCell>
        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
            </span>
          </TooltipTrigger>
          <TooltipContent className="max-w-64">{t.moTa}</TooltipContent>
        </Tooltip>
      </TableCell>
      <TableCell>
        <span className="tabular-nums">
          {muc.affectedRows == null ? '—' : muc.affectedRows.toLocaleString('vi-VN')}
        </span>
      </TableCell>
      <TableCell>
        <div className="flex min-w-0 flex-col gap-1">
          <StatusChip sacThai={tt.sacThai}>{tt.nhan}</StatusChip>
          {muc.errorMessage && (
            <span className="text-destructive max-w-72 text-xs">{muc.errorMessage}</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <span className="text-muted-foreground text-xs tabular-nums">
          {muc.executedAt ? format(new Date(muc.executedAt), 'HH:mm dd/MM') : '—'}
        </span>
      </TableCell>
    </TableRow>
  )
}
