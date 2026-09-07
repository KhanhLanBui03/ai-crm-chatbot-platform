import { formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { Filter, Search, SearchX } from 'lucide-react'

import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { NHAN_KENH, NHAN_TRANG_THAI } from '@/features/conversations/nhan'
import { chuCaiDau } from '@/utils/ten'
import type { BoLocHoiThoai } from '@/api/conversations'
import type { HoiThoaiTomTat } from '@/types/schema'
import { cn } from '@/utils/cn'

interface Props {
  danhSach: HoiThoaiTomTat[] | undefined
  dangTai: boolean
  idDangChon: string | null
  onChon: (id: string) => void
  boLoc: BoLocHoiThoai
  onDoiBoLoc: (bo: BoLocHoiThoai) => void
}

export function ConversationList({
  danhSach,
  dangTai,
  idDangChon,
  onChon,
  boLoc,
  onDoiBoLoc,
}: Props) {
  return (
    <div className="flex w-80 shrink-0 flex-col border-r">
      <div className="flex flex-col gap-2.5 border-b p-3">
        <div className="flex items-center gap-2">
          <span className="flex-1 text-base font-semibold">Hộp thư</span>
          <Button variant="outline" size="sm">
            <Filter />
            Lọc
          </Button>
        </div>

        <div className="relative">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
          <Input
            className="pl-8"
            placeholder="Tìm trong hội thoại…"
            value={boLoc.tuKhoa ?? ''}
            onChange={(e) => onDoiBoLoc({ ...boLoc, tuKhoa: e.target.value })}
          />
        </div>

        <Tabs
          value={boLoc.phamVi ?? 'all'}
          onValueChange={(v) => onDoiBoLoc({ ...boLoc, phamVi: v as BoLocHoiThoai['phamVi'] })}
        >
          <TabsList className="w-full">
            <TabsTrigger value="all">Tất cả</TabsTrigger>
            <TabsTrigger value="unassigned">Chờ tôi</TabsTrigger>
            <TabsTrigger value="mine">Của tôi</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {dangTai && !danhSach ? (
          <XuongDanhSach />
        ) : danhSach && danhSach.length > 0 ? (
          danhSach.map((ht) => (
            <MucHoiThoai
              key={ht.id}
              hoiThoai={ht}
              dangChon={ht.id === idDangChon}
              onChon={() => onChon(ht.id)}
            />
          ))
        ) : (
          <RongVIBoLoc onGoLoc={() => onDoiBoLoc({ phamVi: 'all', tuKhoa: '' })} />
        )}
      </div>
    </div>
  )
}

function MucHoiThoai({
  hoiThoai,
  dangChon,
  onChon,
}: {
  hoiThoai: HoiThoaiTomTat
  dangChon: boolean
  onChon: () => void
}) {
  const trangThai = NHAN_TRANG_THAI[hoiThoai.status]
  const chuaDoc = hoiThoai.unreadCount > 0

  return (
    <button
      type="button"
      onClick={onChon}
      aria-current={dangChon}
      className={cn(
        'flex w-full gap-2.5 border-b p-3 text-left transition-colors',
        dangChon ? 'bg-muted shadow-[inset_3px_0_0_0_var(--primary)]' : 'hover:bg-muted/50',
      )}
    >
      <div className="bg-secondary text-secondary-foreground flex size-8 shrink-0 items-center justify-center rounded-full text-[13px] font-medium">
        {chuCaiDau(hoiThoai.contactName)}
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex items-baseline gap-1.5">
          <span
            className={cn('flex-1 truncate text-sm', chuaDoc ? 'font-semibold' : 'font-medium')}
          >
            {hoiThoai.contactName}
          </span>
          <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
            {formatDistanceToNowStrict(new Date(hoiThoai.lastMessageAt), { locale: vi })}
          </span>
        </div>

        <span
          className={cn('truncate text-[13px]', chuaDoc ? 'text-foreground' : 'text-muted-foreground')}
        >
          {hoiThoai.lastMessagePreview}
        </span>

        <div className="flex items-center gap-1.5">
          <StatusChip sacThai={trangThai.sacThai} BieuTuong={trangThai.BieuTuong}>
            {trangThai.nhan}
          </StatusChip>
          <span className="text-muted-foreground text-xs">{NHAN_KENH[hoiThoai.channelType]}</span>
          <span className="flex-1" />
          {chuaDoc && (
            <span className="bg-primary text-primary-foreground flex h-[18px] min-w-[18px] items-center justify-center rounded-full px-1.5 text-[11px] font-medium tabular-nums">
              {hoiThoai.unreadCount}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

/** Skeleton dựng theo đúng hình dạng dòng sắp hiện, không phải một vòng xoay giữa màn. */
function XuongDanhSach() {
  return (
    <div className="flex flex-col">
      {[1, 0.7, 0.4].map((mo, i) => (
        <div key={i} className="flex gap-2.5 border-b p-3" style={{ opacity: mo }}>
          <Skeleton className="size-8 rounded-full" />
          <div className="flex flex-1 flex-col gap-1.5">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-52" />
            <Skeleton className="h-5 w-24 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

/** Rỗng vì bộ lọc — khác hẳn rỗng vì chưa có dữ liệu: lối thoát ở đây là gỡ bộ lọc. */
function RongVIBoLoc({ onGoLoc }: { onGoLoc: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <div className="bg-muted text-muted-foreground flex size-11 items-center justify-center rounded-full">
        <SearchX className="size-5" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-base font-medium">Không có hội thoại nào khớp</span>
        <span className="text-muted-foreground text-[13px]">
          Thử gỡ bớt bộ lọc hoặc đổi từ khoá tìm kiếm.
        </span>
      </div>
      <Button variant="outline" size="sm" onClick={onGoLoc}>
        Gỡ bộ lọc
      </Button>
    </div>
  )
}
