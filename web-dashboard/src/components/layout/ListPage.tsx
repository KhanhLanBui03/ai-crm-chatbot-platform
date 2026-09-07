import type { RowData, RowSelectionState, SortingState } from '@tanstack/react-table'
import { Plus, Search, SearchX, X, type LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { DataTable, type CotBang } from '@/components/ui/data-table'
import { EmptyState } from '@/components/ui/empty-state'
import { Input } from '@/components/ui/input'
import { Pagination } from '@/components/ui/pagination'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTriHoan } from '@/hooks/useTriHoan'
import type { Page } from '@/types/api'

export interface BoLocChon {
  khoa: string
  nhan: string
  luaChon: { giaTri: string; nhan: string }[]
}

export interface ThaoTac {
  nhan: string
  BieuTuong?: LucideIcon
  onClick: () => void
  bienThe?: 'default' | 'outline' | 'destructive'
}

export interface ListPageProps<T extends RowData> {
  tieuDe: string
  moTa?: string

  cot: CotBang<T>[]
  trang: Page<T> | undefined
  dangTai: boolean
  layId?: (dong: T) => string
  onChonDong?: (dong: T) => void

  /** Bỏ trống là ẩn ô tìm kiếm — vài màn danh sách ngắn không cần. */
  timKiem?: { goiY: string; giaTri: string; onDoi: (v: string) => void }
  boLoc?: BoLocChon[]
  giaTriBoLoc?: Record<string, string | undefined>
  onDoiBoLoc?: (khoa: string, giaTri: string | undefined) => void
  onGoHetBoLoc?: () => void

  sapXep?: { trangThai: SortingState; onDoiSapXep: (s: SortingState) => void }
  onDoiTrang: (trangMoi: number) => void

  thaoTacChinh?: ThaoTac
  thaoTacPhu?: ThaoTac[]
  /** Bỏ trống là tắt cột hộp kiểm. Nhãn nhận vào danh sách id đang chọn. */
  thaoTacHangLoat?: { nhan: string; onClick: (ids: string[]) => void; nguyHiem?: boolean }[]

  /** Trạng thái **chưa có dữ liệu nào** — khác hẳn rỗng vì bộ lọc, xem `EmptyState`. */
  khiChuaCoDuLieu: { BieuTuong: LucideIcon; tieuDe: string; moTa?: string }
}

/**
 * Mẫu M1 — trang danh sách. Phủ 19 trong 58 màn hình (ADR-0011).
 *
 * Mọi thứ riêng của từng màn nằm ở `cot` và ở các nhãn truyền vào; component này không biết gì về
 * nghiệp vụ. Một màn tầng hai vì vậy chỉ còn là **một object cấu hình cộng một route**.
 *
 * Ô tìm kiếm được trì hoãn ở đây, không phải ở phía gọi — nếu để mỗi màn tự lo thì 19 màn có 19
 * cơ hội quên.
 */
export function ListPage<T extends RowData>({
  tieuDe,
  moTa,
  cot,
  trang,
  dangTai,
  layId,
  onChonDong,
  timKiem,
  boLoc,
  giaTriBoLoc = {},
  onDoiBoLoc,
  onGoHetBoLoc,
  sapXep,
  onDoiTrang,
  thaoTacChinh,
  thaoTacPhu,
  thaoTacHangLoat,
  khiChuaCoDuLieu,
}: ListPageProps<T>) {
  const [oNhap, datONhap] = useState(timKiem?.giaTri ?? '')
  const tuKhoaTriHoan = useTriHoan(oNhap)
  const [daChon, datDaChon] = useState<RowSelectionState>({})

  useEffect(() => {
    if (timKiem && tuKhoaTriHoan !== timKiem.giaTri) timKiem.onDoi(tuKhoaTriHoan)
    // Chỉ phản ứng với giá trị đã trì hoãn; `timKiem` là object mới ở mỗi lần render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tuKhoaTriHoan])

  const idDaChon = Object.keys(daChon).filter((id) => daChon[id])
  const dangLoc = Boolean(oNhap) || Object.values(giaTriBoLoc).some(Boolean)
  const muc = trang?.items ?? []

  function goHetBoLoc() {
    datONhap('')
    onGoHetBoLoc?.()
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 flex-wrap items-start justify-between gap-3 px-4 pt-4 pb-3">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-semibold tracking-tight">{tieuDe}</h1>
          {moTa && <p className="text-muted-foreground text-[13px]">{moTa}</p>}
        </div>

        <div className="flex items-center gap-1.5">
          {thaoTacPhu?.map((t) => (
            <Button key={t.nhan} variant={t.bienThe ?? 'outline'} size="sm" onClick={t.onClick}>
              {t.BieuTuong && <t.BieuTuong />}
              {t.nhan}
            </Button>
          ))}
          {thaoTacChinh && (
            <Button size="sm" onClick={thaoTacChinh.onClick}>
              {thaoTacChinh.BieuTuong ? <thaoTacChinh.BieuTuong /> : <Plus />}
              {thaoTacChinh.nhan}
            </Button>
          )}
        </div>
      </div>

      {(timKiem || boLoc?.length) && (
        <div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-4 pb-3">
          {timKiem && (
            <div className="relative w-full max-w-72">
              <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
              <Input
                className="pl-8"
                placeholder={timKiem.goiY}
                value={oNhap}
                onChange={(e) => datONhap(e.target.value)}
              />
            </div>
          )}

          {boLoc?.map((bl) => (
            <Select
              key={bl.khoa}
              value={giaTriBoLoc[bl.khoa] ?? 'tat-ca'}
              onValueChange={(v) => onDoiBoLoc?.(bl.khoa, v === 'tat-ca' ? undefined : v)}
            >
              <SelectTrigger size="sm" className="w-auto min-w-36">
                <SelectValue placeholder={bl.nhan} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tat-ca">{bl.nhan}: tất cả</SelectItem>
                {bl.luaChon.map((lc) => (
                  <SelectItem key={lc.giaTri} value={lc.giaTri}>
                    {lc.nhan}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ))}

          {dangLoc && (
            <Button variant="ghost" size="sm" onClick={goHetBoLoc}>
              <X />
              Gỡ bộ lọc
            </Button>
          )}
        </div>
      )}

      {/* Thanh thao tác hàng loạt chỉ hiện khi có dòng được chọn — chiếm chỗ thường trực là lãng phí */}
      {thaoTacHangLoat && idDaChon.length > 0 && (
        <div className="bg-primary/8 flex shrink-0 items-center gap-2 border-b px-4 py-2">
          <span className="text-[13px] font-medium tabular-nums">
            Đã chọn {idDaChon.length.toLocaleString('vi-VN')} mục
          </span>
          <span className="flex-1" />
          {thaoTacHangLoat.map((t) => (
            <Button
              key={t.nhan}
              variant={t.nguyHiem ? 'destructive' : 'outline'}
              size="sm"
              onClick={() => t.onClick(idDaChon)}
            >
              {t.nhan}
            </Button>
          ))}
          <Button variant="ghost" size="sm" onClick={() => datDaChon({})}>
            Bỏ chọn
          </Button>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        <DataTable
          cot={cot}
          duLieu={muc}
          layId={layId}
          dangTai={dangTai}
          onChonDong={onChonDong}
          sapXep={sapXep}
          chonNhieu={
            thaoTacHangLoat ? { daChon, onDoiChon: datDaChon } : undefined
          }
          khiRong={
            dangLoc ? (
              <EmptyState
                BieuTuong={SearchX}
                tieuDe="Không có kết quả nào khớp"
                moTa="Thử gỡ bớt bộ lọc hoặc đổi từ khoá tìm kiếm."
                thaoTac={{ nhan: 'Gỡ bộ lọc', onClick: goHetBoLoc }}
              />
            ) : (
              <EmptyState
                BieuTuong={khiChuaCoDuLieu.BieuTuong}
                tieuDe={khiChuaCoDuLieu.tieuDe}
                moTa={khiChuaCoDuLieu.moTa}
                thaoTac={
                  thaoTacChinh
                    ? { nhan: thaoTacChinh.nhan, onClick: thaoTacChinh.onClick, bienThe: 'default' }
                    : undefined
                }
              />
            )
          }
        />
      </div>

      {trang && (
        <Pagination
          trang={trang.page}
          tongSoTrang={trang.totalPages}
          tongSoMuc={trang.totalItems}
          coTrang={trang.size}
          onDoiTrang={onDoiTrang}
        />
      )}
    </div>
  )
}
