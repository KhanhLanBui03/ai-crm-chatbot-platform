import { ChevronLeft, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { ThaoTac } from '@/components/layout/ListPage'

export interface TabChiTiet {
  khoa: string
  nhan: string
  /** Số nhỏ cạnh nhãn tab — ví dụ số hoạt động, số ghi chú. */
  soLuong?: number
  noiDung: React.ReactNode
}

export interface DetailPageProps {
  quayLai: { duongDan: string; nhan: string }
  tieuDe: string
  phuDe?: string
  /** Chip trạng thái đặt cạnh tiêu đề. Truyền `StatusChip` đã dựng sẵn ở phía gọi. */
  chip?: React.ReactNode
  thaoTacChinh?: ThaoTac
  thaoTacPhu?: ThaoTac[]

  tab: TabChiTiet[]
  tabHienTai: string
  onDoiTab: (khoa: string) => void

  /**
   * Cột phụ bên phải — thông tin tra cứu nhanh, không phải nội dung chính.
   * Bỏ trống là bố cục một cột.
   */
  cotPhu?: React.ReactNode
  dangTai?: boolean
}

/**
 * Mẫu M2 — trang chi tiết một bản ghi. Phủ 4 màn hình (ADR-0011).
 *
 * Bố cục cố định: đường quay lại → tiêu đề + trạng thái + thao tác → tab → hai cột. Giữ nguyên
 * thứ tự này ở mọi màn chi tiết để người dùng không phải học lại vị trí nút ở từng nơi.
 */
export function DetailPage({
  quayLai,
  tieuDe,
  phuDe,
  chip,
  thaoTacChinh,
  thaoTacPhu,
  tab,
  tabHienTai,
  onDoiTab,
  cotPhu,
  dangTai = false,
}: DetailPageProps) {
  if (dangTai) return <XuongChiTiet coCotPhu={Boolean(cotPhu)} />

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 flex-col gap-3 px-4 pt-3 pb-0">
        <Link
          to={quayLai.duongDan}
          className="text-muted-foreground hover:text-foreground -ml-1 flex w-fit items-center gap-1 text-[13px] transition-colors"
        >
          <ChevronLeft className="size-3.5" />
          {quayLai.nhan}
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight">{tieuDe}</h1>
              {chip}
            </div>
            {phuDe && <p className="text-muted-foreground text-[13px]">{phuDe}</p>}
          </div>

          <div className="flex items-center gap-1.5">
            {thaoTacPhu?.map((t) => (
              <Button key={t.nhan} variant={t.bienThe ?? 'outline'} size="sm" onClick={t.onClick}>
                {t.BieuTuong && <t.BieuTuong />}
                {t.nhan}
              </Button>
            ))}
            {thaoTacChinh && (
              <Button
                size="sm"
                variant={thaoTacChinh.bienThe ?? 'default'}
                onClick={thaoTacChinh.onClick}
              >
                {thaoTacChinh.BieuTuong && <thaoTacChinh.BieuTuong />}
                {thaoTacChinh.nhan}
              </Button>
            )}
          </div>
        </div>
      </div>

      <Tabs
        value={tabHienTai}
        onValueChange={onDoiTab}
        className="flex min-h-0 flex-1 flex-col gap-0"
      >
        <div className="shrink-0 border-b px-4">
          <TabsList>
            {tab.map((t) => (
              <TabsTrigger key={t.khoa} value={t.khoa}>
                {t.nhan}
                {t.soLuong !== undefined && (
                  <span className="text-muted-foreground ml-1 tabular-nums">{t.soLuong}</span>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <div className="flex min-h-0 flex-1">
          <div className="min-w-0 flex-1 overflow-y-auto p-4">
            {tab.map((t) => (
              <TabsContent key={t.khoa} value={t.khoa} className="mt-0">
                {t.noiDung}
              </TabsContent>
            ))}
          </div>

          {cotPhu && (
            <aside className="w-80 shrink-0 overflow-y-auto border-l p-4">{cotPhu}</aside>
          )}
        </div>
      </Tabs>
    </div>
  )
}

function XuongChiTiet({ coCotPhu }: { coCotPhu: boolean }) {
  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col gap-4 p-4">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
      {coCotPhu && (
        <div className="flex w-80 shrink-0 flex-col gap-3 border-l p-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}
    </div>
  )
}

/** Khối thông tin dạng nhãn–giá trị, dùng đi dùng lại trong cột phụ của mọi màn chi tiết. */
export function HangThongTin({
  BieuTuong,
  nhan,
  children,
}: {
  BieuTuong?: LucideIcon
  nhan: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-baseline gap-2 py-1 text-[13px]">
      <span className="text-muted-foreground flex flex-1 items-center gap-1.5">
        {BieuTuong && <BieuTuong className="size-3.5 shrink-0" />}
        {nhan}
      </span>
      <span className="min-w-0 text-right font-medium">{children}</span>
    </div>
  )
}
