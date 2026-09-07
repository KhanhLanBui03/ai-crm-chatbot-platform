import {
  flexRender,
  rowSelectionFeature,
  rowSortingFeature,
  tableFeatures,
  useTable,
  type ColumnDef,
  type RowSelectionState,
  type RowData,
  type SortingState,
  type Updater,
} from '@tanstack/react-table'
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import { useMemo } from 'react'

import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/utils/cn'

/**
 * Đặc tính bảng, khai **tĩnh ở ngoài component** theo đúng yêu cầu của TanStack Table v9 — v9 bỏ
 * cách nhập cả thư viện của v8 để chỉ gói phần thật sự dùng vào bản build.
 *
 * Chỉ hai đặc tính: sắp xếp và chọn dòng. Lọc và phân trang chạy ở **máy chủ** nên không đăng ký
 * `columnFilteringFeature` / `rowPaginationFeature` — đăng ký vào là mời gọi ai đó lọc trên 25
 * dòng của trang hiện tại rồi tưởng đã lọc cả tập dữ liệu.
 */
export const dacTinhBang = tableFeatures({
  rowSortingFeature,
  rowSelectionFeature,
})

export type DacTinhBang = typeof dacTinhBang

/** Định nghĩa cột đã ghim sẵn đặc tính — màn hình chỉ cần viết `CotBang<KhachHang>[]`. */
export type CotBang<T extends RowData> = ColumnDef<DacTinhBang, T, unknown>

export interface DataTableProps<T extends RowData> {
  cot: CotBang<T>[]
  duLieu: T[]
  /** Khoá dòng — dùng cho chọn nhiều dòng. Mặc định lấy trường `id`. */
  layId?: (dong: T) => string
  dangTai?: boolean
  /** Số dòng xương lúc tải lần đầu. Đặt bằng cỡ trang để bảng không nhảy khi dữ liệu về. */
  soDongXuong?: number
  onChonDong?: (dong: T) => void
  /** Bỏ trống là tắt hẳn cột hộp kiểm — không phải màn danh sách nào cũng cần chọn nhiều. */
  chonNhieu?: {
    daChon: RowSelectionState
    onDoiChon: (chon: RowSelectionState) => void
  }
  sapXep?: {
    trangThai: SortingState
    onDoiSapXep: (s: SortingState) => void
  }
  /** Hiện khi không có dòng nào. Trạng thái rỗng là một màn hình, không phải một dòng chữ. */
  khiRong?: React.ReactNode
}

function apDung<T>(capNhat: Updater<T>, hienTai: T): T {
  return typeof capNhat === 'function' ? (capNhat as (cu: T) => T)(hienTai) : capNhat
}

/**
 * Bảng dữ liệu dùng chung, **không biết nghiệp vụ** — mọi thứ riêng của từng màn nằm ở `cot`.
 *
 * Sắp xếp và phân trang chạy ở máy chủ: bảng chỉ báo ra ngoài rằng người dùng vừa bấm gì
 * (`onDoiSapXep`), không tự sắp mảng.
 */
export function DataTable<T extends RowData>({
  cot,
  duLieu,
  layId,
  dangTai = false,
  soDongXuong = 8,
  onChonDong,
  chonNhieu,
  sapXep,
  khiRong,
}: DataTableProps<T>) {
  /**
   * Cột hộp kiểm dựng ở **đây**, không phải ở từng màn: bật `enableRowSelection` mà quên thêm cột
   * thì thao tác hàng loạt không bấm được, và không có gì báo lỗi — đúng loại thiếu sót chỉ lộ ra
   * khi bấm thử. Gắn liền với `chonNhieu` thì 19 màn danh sách không có cơ hội quên.
   */
  const cotDayDu = useMemo<CotBang<T>[]>(() => {
    if (!chonNhieu) return cot
    const cotChon: CotBang<T> = {
      id: 'chon-dong',
      header: ({ table }) => (
        <Checkbox
          checked={
            table.getIsAllRowsSelected()
              ? true
              : table.getIsSomeRowsSelected()
                ? 'indeterminate'
                : false
          }
          onCheckedChange={() => table.toggleAllRowsSelected()}
          aria-label="Chọn tất cả dòng trên trang này"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={() => row.toggleSelected()}
          // Chặn nổi bọt: dòng có thể đang gắn `onChonDong` để mở trang chi tiết
          onClick={(su) => su.stopPropagation()}
          aria-label="Chọn dòng này"
        />
      ),
    }
    return [cotChon, ...cot]
  }, [cot, chonNhieu])

  const bang = useTable({
    features: dacTinhBang,
    columns: cotDayDu,
    data: duLieu,
    manualSorting: true,
    enableRowSelection: Boolean(chonNhieu),
    state: {
      ...(sapXep ? { sorting: sapXep.trangThai } : {}),
      ...(chonNhieu ? { rowSelection: chonNhieu.daChon } : {}),
    },
    onSortingChange: sapXep
      ? (capNhat) => sapXep.onDoiSapXep(apDung(capNhat, sapXep.trangThai))
      : undefined,
    onRowSelectionChange: chonNhieu
      ? (capNhat) => chonNhieu.onDoiChon(apDung(capNhat, chonNhieu.daChon))
      : undefined,
    getRowId: layId
      ? (dong: T) => layId(dong)
      : (dong: T) => String((dong as { id?: unknown }).id ?? ''),
  })

  if (dangTai && duLieu.length === 0) {
    return <XuongBang soCot={cotDayDu.length} soDong={soDongXuong} />
  }

  if (duLieu.length === 0) {
    return <>{khiRong}</>
  }

  return (
    // Bảng rộng cuộn ngang trong khung của chính nó — không để cả trang cuộn ngang theo
    <div className="min-w-0 overflow-x-auto">
      <Table>
        <TableHeader>
          {bang.getHeaderGroups().map((nhom) => (
            <TableRow key={nhom.id}>
              {nhom.headers.map((o) => {
                const coSap = o.column.getCanSort()
                const huong = o.column.getIsSorted()
                return (
                  <TableHead key={o.id} className={coSap ? 'p-0' : undefined}>
                    {o.isPlaceholder ? null : coSap ? (
                      <button
                        type="button"
                        onClick={o.column.getToggleSortingHandler()}
                        className="hover:text-foreground flex h-full w-full items-center gap-1 px-3 py-2 text-left transition-colors"
                      >
                        {flexRender(o.column.columnDef.header, o.getContext())}
                        {huong === 'asc' ? (
                          <ArrowUp className="size-3" />
                        ) : huong === 'desc' ? (
                          <ArrowDown className="size-3" />
                        ) : (
                          <ChevronsUpDown className="size-3 opacity-40" />
                        )}
                      </button>
                    ) : (
                      flexRender(o.column.columnDef.header, o.getContext())
                    )}
                  </TableHead>
                )
              })}
            </TableRow>
          ))}
        </TableHeader>

        <TableBody>
          {bang.getRowModel().rows.map((dong) => (
            <TableRow
              key={dong.id}
              data-state={dong.getIsSelected() ? 'selected' : undefined}
              onClick={onChonDong ? () => onChonDong(dong.original) : undefined}
              className={cn(onChonDong && 'hover:bg-muted/50 cursor-pointer')}
            >
              {/* `getAllCells` chứ không phải `getVisibleCells`: ẩn/hiện cột là
                  `columnVisibilityFeature`, chưa đăng ký nên phương thức đó không tồn tại. */}
              {dong.getAllCells().map((o) => (
                <TableCell key={o.id}>
                  {flexRender(o.column.columnDef.cell, o.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

/** Xương dựng theo đúng hình dạng bảng sắp hiện, không phải một vòng xoay giữa màn. */
function XuongBang({ soCot, soDong }: { soCot: number; soDong: number }) {
  return (
    <div className="flex flex-col">
      {Array.from({ length: soDong }).map((_, d) => (
        <div key={d} className="flex gap-4 border-b px-3 py-3" style={{ opacity: 1 - d * 0.1 }}>
          {Array.from({ length: soCot }).map((_, c) => (
            <Skeleton key={c} className={cn('h-4', c === 0 ? 'w-40' : 'w-24')} />
          ))}
        </div>
      ))}
    </div>
  )
}
