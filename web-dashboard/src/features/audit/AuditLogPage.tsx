import { format } from 'date-fns'
import { Eye, EyeOff, ScrollText, ShieldAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { useDanhSachKiemToanQuery, useXemDayDuBanGhiMutation, type BoLocKiemToan } from '@/api/audit'
import { laLoiTruyVan } from '@/api/baseQuery'
import { ListPage } from '@/components/layout/ListPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import type { CotBang } from '@/components/ui/data-table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { StatusChip } from '@/components/ui/status-chip'
import { Textarea } from '@/components/ui/textarea'
import {
  NHAN_CHU_THE,
  NHAN_HANH_DONG,
  NHAN_MUC_NGHIEM_TRONG,
} from '@/features/audit/nhan'
import type { BanGhiKiemToan } from '@/types/schema'

/**
 * SCR054 — nhật ký kiểm toán. Mẫu M1, cộng một hộp thoại xem đầy đủ.
 *
 * Bản ghi chạm dữ liệu cá nhân trả về ở trạng thái **đã che**. Muốn xem nguyên văn phải nêu lý do,
 * và chính lần xem đó lại sinh thêm một dòng nhật ký mới — người xem dữ liệu của khách cũng bị
 * ghi vết như mọi thao tác khác. Đây là yêu cầu của Nghị định 13/2023/NĐ-CP, không phải một lớp
 * bảo vệ tự nghĩ ra.
 *
 * `actorEmail` chụp lại tại thời điểm ghi chứ không nối bảng người dùng: bản ghi vẫn phải đọc
 * được sau khi tài khoản đó bị xoá, mà xoá tài khoản chính là một trong những việc nhật ký này
 * tồn tại để ghi lại.
 */
export function AuditLogPage() {
  const [boLoc, datBoLoc] = useState<BoLocKiemToan>({ trang: 0 })
  const [dangXem, datDangXem] = useState<BanGhiKiemToan | null>(null)

  const truyVan = useDanhSachKiemToanQuery(boLoc)

  const cot = useMemo<CotBang<BanGhiKiemToan>[]>(
    () => [
      {
        id: 'occurredAt',
        accessorKey: 'occurredAt',
        header: 'Thời điểm',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {format(new Date(row.original.occurredAt), 'HH:mm:ss dd/MM/yyyy')}
          </span>
        ),
      },
      {
        id: 'action',
        accessorKey: 'action',
        header: 'Hành động',
        cell: ({ row }) => {
          const b = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="font-medium">{NHAN_HANH_DONG[b.action] ?? b.action}</span>
              <span className="text-muted-foreground font-mono text-xs">{b.action}</span>
            </div>
          )
        },
      },
      {
        id: 'actorEmail',
        accessorKey: 'actorEmail',
        header: 'Người thực hiện',
        cell: ({ row }) => {
          const b = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="truncate text-[13px]">{b.actorEmail ?? '—'}</span>
              <span className="text-muted-foreground text-xs">{NHAN_CHU_THE[b.actorType]}</span>
            </div>
          )
        },
      },
      {
        id: 'entityType',
        accessorKey: 'entityType',
        header: 'Đối tượng',
        cell: ({ row }) => (
          <span className="text-muted-foreground font-mono text-xs">
            {row.original.entityType ?? '—'}
          </span>
        ),
      },
      {
        id: 'severity',
        accessorKey: 'severity',
        header: 'Mức',
        cell: ({ row }) => {
          const m = NHAN_MUC_NGHIEM_TRONG[row.original.severity]
          return <StatusChip sacThai={m.sacThai}>{m.nhan}</StatusChip>
        },
      },
      {
        id: 'containsPersonalData',
        accessorKey: 'containsPersonalData',
        header: 'Dữ liệu cá nhân',
        cell: ({ row }) => {
          const b = row.original
          if (!b.containsPersonalData) {
            return <span className="text-muted-foreground text-[13px]">Không</span>
          }
          return b.masked ? (
            <StatusChip sacThai="warning" BieuTuong={EyeOff}>
              Đang che
            </StatusChip>
          ) : (
            <StatusChip sacThai="info" BieuTuong={Eye}>
              Đã bỏ che
            </StatusChip>
          )
        },
      },
      {
        id: 'ipAddress',
        accessorKey: 'ipAddress',
        header: 'Địa chỉ IP',
        cell: ({ row }) => (
          <span className="text-muted-foreground font-mono text-xs">
            {row.original.ipAddress ?? '—'}
          </span>
        ),
      },
      {
        id: 'thaoTac',
        header: '',
        cell: ({ row }) => {
          const b = row.original
          if (!b.containsPersonalData || !b.masked) return null
          return (
            <div className="flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={(su) => {
                  su.stopPropagation()
                  datDangXem(b)
                }}
              >
                <Eye />
                Xem đầy đủ
              </Button>
            </div>
          )
        },
      },
    ],
    [],
  )

  return (
    <>
      <ListPage
        tieuDe="Nhật ký kiểm toán"
        moTa="Vết của mọi thao tác chạm tới dữ liệu. Bản ghi không sửa và không xoá được — kể cả bởi quản trị viên."
        cot={cot}
        trang={truyVan.data}
        dangTai={truyVan.isLoading}
        timKiem={{
          goiY: 'Tìm theo hành động, người thực hiện, mã theo dõi…',
          giaTri: boLoc.tuKhoa ?? '',
          onDoi: (v) => datBoLoc((cu) => ({ ...cu, tuKhoa: v, trang: 0 })),
        }}
        boLoc={[
          {
            khoa: 'mucNghiemTrong',
            nhan: 'Mức',
            luaChon: Object.entries(NHAN_MUC_NGHIEM_TRONG).map(([giaTri, v]) => ({
              giaTri,
              nhan: v.nhan,
            })),
          },
          {
            khoa: 'hanhDong',
            nhan: 'Hành động',
            luaChon: Object.entries(NHAN_HANH_DONG).map(([giaTri, nhan]) => ({ giaTri, nhan })),
          },
        ]}
        giaTriBoLoc={{ mucNghiemTrong: boLoc.mucNghiemTrong, hanhDong: boLoc.hanhDong }}
        onDoiBoLoc={(khoa, giaTri) =>
          datBoLoc((cu) => ({
            ...cu,
            trang: 0,
            ...(khoa === 'mucNghiemTrong'
              ? { mucNghiemTrong: giaTri as BoLocKiemToan['mucNghiemTrong'] }
              : { hanhDong: giaTri }),
          }))
        }
        onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
        onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
        khiChuaCoDuLieu={{
          BieuTuong: ScrollText,
          tieuDe: 'Chưa có bản ghi kiểm toán nào',
          moTa: 'Nhật ký bắt đầu ghi từ thao tác đầu tiên trên hệ thống.',
        }}
      />

      {/*
        Nạp lại **khi đóng**, không phải khi gửi: lần bỏ che vừa rồi sinh ra một dòng
        `AUDIT_LOG_REVEALED` mới, và danh sách phải có nó — nhưng chèn vào giữa lúc người dùng
        đang đọc nội dung đã bỏ che thì đẩy đúng bản ghi ấy trôi khỏi chỗ họ đang nhìn.
      */}
      <HopThoaiXemDayDu
        banGhi={dangXem}
        onDong={() => {
          datDangXem(null)
          void truyVan.refetch()
        }}
      />
    </>
  )
}

/**
 * SCR055 phụ trợ — hộp thoại nêu lý do trước khi bỏ che.
 *
 * Không dùng `FormDialog` vì hộp thoại này không phải là biểu mẫu tạo hay sửa dữ liệu: nó là một
 * cửa kiểm soát trước khi đọc, và nó phải hiện nội dung đã bỏ che **ngay tại chỗ** sau khi gửi.
 */
function HopThoaiXemDayDu({
  banGhi,
  onDong,
}: {
  banGhi: BanGhiKiemToan | null
  onDong: () => void
}) {
  const [lyDo, datLyDo] = useState('')
  const [xem, ketQua] = useXemDayDuBanGhiMutation()

  if (!banGhi) return null
  const daBoChe = ketQua.data
  const thongDiepLoi = laLoiTruyVan(ketQua.error) ? ketQua.error.message : null

  function dong() {
    datLyDo('')
    ketQua.reset()
    onDong()
  }

  return (
    <Dialog open onOpenChange={(m) => !m && dong()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {daBoChe ? 'Nội dung đầy đủ của bản ghi' : 'Xem dữ liệu cá nhân trong bản ghi'}
          </DialogTitle>
          <DialogDescription>
            {NHAN_HANH_DONG[banGhi.action] ?? banGhi.action} ·{' '}
            {format(new Date(banGhi.occurredAt), 'HH:mm:ss dd/MM/yyyy')}
          </DialogDescription>
        </DialogHeader>

        {daBoChe ? (
          <div className="flex flex-col gap-3">
            <Alert>
              <ShieldAlert />
              <AlertDescription>
                Lần xem này đã được ghi vào nhật ký kèm lý do bạn nêu, dưới hành động{' '}
                <code className="font-mono">AUDIT_LOG_REVEALED</code>.
              </AlertDescription>
            </Alert>
            <KhoiJson nhan="Trước" giaTri={daBoChe.before} />
            <KhoiJson nhan="Sau" giaTri={daBoChe.after} />
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <Alert variant="destructive">
              <ShieldAlert />
              <AlertDescription>
                Bản ghi này chứa dữ liệu cá nhân của khách hàng. Mọi lần xem đều được ghi lại kèm
                tên bạn và lý do — theo Nghị định 13/2023/NĐ-CP.
              </AlertDescription>
            </Alert>

            {thongDiepLoi && (
              <Alert variant="destructive">
                <AlertDescription>{thongDiepLoi}</AlertDescription>
              </Alert>
            )}

            <Field>
              <FieldLabel htmlFor="kt-ly-do">Lý do cần xem</FieldLabel>
              <Textarea
                id="kt-ly-do"
                rows={3}
                placeholder="Ví dụ: đối chiếu khiếu nại số KN-2026-118 của khách."
                value={lyDo}
                onChange={(e) => datLyDo(e.target.value)}
              />
              <FieldDescription>
                Tối thiểu 10 ký tự. Lý do này hiện trong nhật ký và trong hồ sơ rà soát.
              </FieldDescription>
            </Field>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={dong}>
            Đóng
          </Button>
          {!daBoChe && (
            <Button
              disabled={lyDo.trim().length < 10 || ketQua.isLoading}
              onClick={async () => {
                await xem({ id: banGhi.id, reason: lyDo.trim() }).unwrap()
                toast.success('Đã bỏ che. Lần xem này được ghi vào nhật ký.')
              }}
            >
              {ketQua.isLoading ? 'Đang mở…' : 'Xác nhận xem'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function KhoiJson({ nhan, giaTri }: { nhan: string; giaTri: unknown }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-muted-foreground text-xs">{nhan}</span>
      <pre className="bg-muted max-h-48 overflow-auto rounded-lg p-3 font-mono text-xs leading-relaxed">
        {giaTri == null ? '—' : JSON.stringify(giaTri, null, 2)}
      </pre>
    </div>
  )
}
