import { format } from 'date-fns'
import { Plus, ShieldCheck, TriangleAlert, UserX } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { useDanhSachYeuCauXoaQuery, useXacMinhDanhTinhMutation } from '@/api/audit'
import { laLoiTruyVan } from '@/api/baseQuery'
import { ListPage } from '@/components/layout/ListPage'
import { Button } from '@/components/ui/button'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { CreateErasureDialog } from '@/features/audit/CreateErasureDialog'
import { NHAN_NGUON_YEU_CAU, NHAN_TRANG_THAI_XOA } from '@/features/audit/nhan'
import type { TrangThaiYeuCauXoa, YeuCauXoa } from '@/types/schema'

/**
 * SCR056 — yêu cầu xoá dữ liệu cá nhân. Mẫu M1.
 *
 * Cột **xác minh danh tính** đứng ngay cạnh tên khách, không nằm cuối bảng: xoá theo một yêu cầu
 * chưa xác minh là tự tay xoá dữ liệu của khách theo lời một người lạ. Nghị định 13 buộc phải xác
 * minh chủ thể dữ liệu trước khi thực hiện quyền xoá, và cột này là chỗ chứng minh đã làm.
 */
export function ErasureRequestsPage() {
  const dieuHuong = useNavigate()
  const [boLoc, datBoLoc] = useState<{ trangThai?: TrangThaiYeuCauXoa; trang?: number }>({
    trang: 0,
  })

  const truyVan = useDanhSachYeuCauXoaQuery(boLoc)
  const [moTao, datMoTao] = useState(false)
  const [xacMinh, ketQuaXacMinh] = useXacMinhDanhTinhMutation()

  const cot = useMemo<CotBang<YeuCauXoa>[]>(
    () => [
      {
        id: 'contactName',
        accessorKey: 'contactName',
        header: 'Khách hàng',
        cell: ({ row }) => {
          const y = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="truncate font-medium">{y.contactName ?? 'Không rõ tên'}</span>
              <span className="text-muted-foreground truncate text-xs">
                <span className="font-mono">{y.contactId.slice(0, 8)}</span>
                {y.requestedBy && ` · ${NHAN_NGUON_YEU_CAU[y.requestedBy]}`}
              </span>
            </div>
          )
        },
      },
      {
        id: 'identityVerifiedByName',
        accessorKey: 'identityVerifiedByName',
        header: 'Xác minh danh tính',
        cell: ({ row }) => {
          const y = row.original
          if (!y.identityVerifiedByName) {
            return (
              <div className="flex flex-col items-start gap-1">
                <span className="text-destructive flex items-center gap-1 text-[13px]">
                  <TriangleAlert className="size-3.5" />
                  Chưa xác minh
                </span>
                {/* UC041 bước 3 — xác minh ngay trên dòng; chặn lan lên dòng (mở trang chi tiết) */}
                {y.status === 'PENDING' && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={ketQuaXacMinh.isLoading}
                    onClick={(e) => {
                      e.stopPropagation()
                      xacMinh(y.id)
                        .unwrap()
                        .then(() => toast.success('Đã ghi nhận xác minh danh tính.'))
                        .catch((loi: unknown) =>
                          toast.error(
                            laLoiTruyVan(loi) && loi.message ? loi.message : 'Chưa xác minh được.',
                          ),
                        )
                    }}
                  >
                    <ShieldCheck />
                    Xác minh danh tính
                  </Button>
                )}
              </div>
            )
          }
          return (
            <div className="flex min-w-0 flex-col">
              <span className="text-success flex items-center gap-1 text-[13px]">
                <ShieldCheck className="size-3.5" />
                {y.identityVerifiedByName}
              </span>
              <span className="text-muted-foreground text-xs tabular-nums">
                {y.identityVerifiedAt
                  ? format(new Date(y.identityVerifiedAt), 'HH:mm dd/MM/yyyy')
                  : ''}
              </span>
            </div>
          )
        },
      },
      {
        id: 'legalBasis',
        accessorKey: 'legalBasis',
        header: 'Căn cứ pháp lý',
        cell: ({ row }) => (
          <span className="text-muted-foreground max-w-72 text-[13px]">
            {row.original.legalBasis ?? '—'}
          </span>
        ),
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const t = NHAN_TRANG_THAI_XOA[row.original.status]
          return <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
        },
      },
      {
        id: 'requestedAt',
        accessorKey: 'requestedAt',
        header: 'Khách yêu cầu lúc',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {format(new Date(row.original.requestedAt), 'HH:mm dd/MM/yyyy')}
          </span>
        ),
      },
      {
        id: 'completedAt',
        accessorKey: 'completedAt',
        header: 'Hoàn tất lúc',
        cell: ({ row }) => {
          const c = row.original.completedAt
          return (
            <span className="text-muted-foreground tabular-nums">
              {c ? format(new Date(c), 'HH:mm dd/MM/yyyy') : '—'}
            </span>
          )
        },
      },
    ],
    [xacMinh, ketQuaXacMinh.isLoading],
  )

  return (
    <>
      <ListPage
        tieuDe="Yêu cầu xoá dữ liệu cá nhân"
        moTa="Quyền xoá theo Điều 16 Nghị định 13/2023/NĐ-CP. Mỗi yêu cầu phải xác minh danh tính trước khi thực thi."
        cot={cot}
        trang={truyVan.data}
        dangTai={truyVan.isLoading}
        onChonDong={(y) => dieuHuong(`/kiem-toan/yeu-cau-xoa/${y.id}`)}
        boLoc={[
          {
            khoa: 'trangThai',
            nhan: 'Trạng thái',
            luaChon: Object.entries(NHAN_TRANG_THAI_XOA).map(([giaTri, v]) => ({
              giaTri,
              nhan: v.nhan,
            })),
          },
        ]}
        giaTriBoLoc={{ trangThai: boLoc.trangThai }}
        onDoiBoLoc={(_khoa, giaTri) =>
          datBoLoc({ trang: 0, trangThai: giaTri as TrangThaiYeuCauXoa | undefined })
        }
        onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
        onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
        thaoTacChinh={{ nhan: 'Tạo yêu cầu', BieuTuong: Plus, onClick: () => datMoTao(true) }}
        thaoTacPhu={[
          { nhan: 'Xem trước phạm vi xoá', onClick: () => dieuHuong('/kiem-toan/xem-truoc-xoa') },
          { nhan: 'Nhật ký kiểm toán', onClick: () => dieuHuong('/kiem-toan/nhat-ky') },
        ]}
        khiChuaCoDuLieu={{
          BieuTuong: UserX,
          tieuDe: 'Chưa có yêu cầu xoá nào',
          moTa: 'Yêu cầu được tạo khi khách hàng thực hiện quyền xoá dữ liệu cá nhân của mình.',
        }}
      />
      <CreateErasureDialog mo={moTao} onDoiMo={datMoTao} />
    </>
  )
}
