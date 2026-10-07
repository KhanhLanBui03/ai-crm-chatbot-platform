import { CalendarCheck, Phone, Plus } from 'lucide-react'
import { useState } from 'react'

import { useDanhSachHoatDongQuery, useSoViecCuaToiQuery } from '@/api/sales'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DongHoatDong } from '@/features/activities/ActivityTimeline'
import { GhiHoatDongDialog } from '@/features/activities/GhiHoatDongDialog'
import { NHAN_LOAI_HOAT_DONG } from '@/features/leads/nhan'
import type { LoaiHoatDong } from '@/types/schema'
import { cn } from '@/utils/cn'

/**
 * SCR047 — hoạt động chăm sóc và nhắc việc (UC035).
 *
 * Tab **Việc của tôi** là lý do màn này tồn tại: lời nhắc giao cho tôi, chia Quá hạn / Hôm nay / Sắp tới
 * (giờ Việt Nam, máy chủ chia). Việc quá hạn mà chưa ai làm là khách đang bị bỏ rơi — phải đứng đầu.
 * Chưa có thông báo đẩy: số đỏ trên menu hỏi lại mỗi phút (giảm độ sâu, ghi trong báo cáo).
 */
export function ActivitiesPage() {
  const [tab, datTab] = useState<'viec' | 'tat-ca'>('viec')
  const [moGhi, datMoGhi] = useState(false)
  const dem = useSoViecCuaToiQuery(undefined, { pollingInterval: 60_000 })

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-semibold tracking-tight">Hoạt động</h1>
          <p className="text-muted-foreground text-[13px]">
            Cuộc gọi, buổi gặp, báo giá đã làm với khách — và những việc cần làm tiếp.
          </p>
        </div>
        <Button size="sm" onClick={() => datMoGhi(true)}>
          <Plus />
          Ghi hoạt động
        </Button>
      </div>

      <Tabs value={tab} onValueChange={(v) => datTab(v as 'viec' | 'tat-ca')}>
        <TabsList>
          <TabsTrigger value="viec">
            Việc của tôi
            {dem.data && dem.data.overdue + dem.data.today > 0 && (
              <span className="bg-destructive ml-1.5 rounded-full px-1.5 text-[11px] text-white tabular-nums">
                {dem.data.overdue + dem.data.today}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="tat-ca">Tất cả</TabsTrigger>
        </TabsList>
      </Tabs>

      {tab === 'viec' ? <ViecCuaToi /> : <TatCa />}

      <GhiHoatDongDialog mo={moGhi} onDoiMo={datMoGhi} />
    </div>
  )
}

function ViecCuaToi() {
  const quaHan = useDanhSachHoatDongQuery({ cuaToi: true, nhomViec: 'OVERDUE', coTrang: 50 })
  const homNay = useDanhSachHoatDongQuery({ cuaToi: true, nhomViec: 'TODAY', coTrang: 50 })
  const sapToi = useDanhSachHoatDongQuery({ cuaToi: true, nhomViec: 'UPCOMING', coTrang: 50 })

  if (quaHan.isLoading || homNay.isLoading || sapToi.isLoading) {
    return <Skeleton className="h-40 w-full" />
  }
  const tong = (quaHan.data?.totalItems ?? 0) + (homNay.data?.totalItems ?? 0) + (sapToi.data?.totalItems ?? 0)
  if (tong === 0) {
    return (
      <EmptyState
        BieuTuong={CalendarCheck}
        tieuDe="Không có việc nào đang chờ"
        moTa="Khi ghi hoạt động, đặt giờ nhắc để việc hiện ở đây đúng lúc cần làm."
      />
    )
  }
  return (
    <div className="flex flex-col gap-5">
      <NhomViec ten="Quá hạn" nguyHiem ds={quaHan.data?.items ?? []} />
      <NhomViec ten="Hôm nay" ds={homNay.data?.items ?? []} />
      <NhomViec ten="Sắp tới" ds={sapToi.data?.items ?? []} />
    </div>
  )
}

function NhomViec({ ten, ds, nguyHiem }: { ten: string; ds: Parameters<typeof DongHoatDong>[0]['h'][]; nguyHiem?: boolean }) {
  if (ds.length === 0) return null
  return (
    <section className="flex flex-col gap-2">
      <h2 className={cn('text-[13px] font-semibold', nguyHiem && 'text-destructive')}>
        {ten} · {ds.length}
      </h2>
      {ds.map((h) => (
        <DongHoatDong key={h.id} h={h} hienKhach hienNoiGan />
      ))}
    </section>
  )
}

function TatCa() {
  const [trang, datTrang] = useState(0)
  const [loai, datLoai] = useState<LoaiHoatDong | undefined>()
  const truyVan = useDanhSachHoatDongQuery({ trang, loai, coTrang: 20 })
  const d = truyVan.data

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Select
          value={loai ?? 'tat-ca'}
          onValueChange={(v) => {
            datLoai(v === 'tat-ca' ? undefined : (v as LoaiHoatDong))
            datTrang(0)
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tat-ca">Mọi loại</SelectItem>
            {Object.entries(NHAN_LOAI_HOAT_DONG).map(([ma, nhan]) => (
              <SelectItem key={ma} value={ma}>
                {nhan}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {d && <span className="text-muted-foreground text-[13px]">{d.totalItems} hoạt động</span>}
      </div>

      {truyVan.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : d && d.items.length === 0 ? (
        <EmptyState BieuTuong={Phone} tieuDe="Chưa có hoạt động nào" moTa="Bấm “Ghi hoạt động” để bắt đầu." />
      ) : (
        d?.items.map((h) => <DongHoatDong key={h.id} h={h} hienKhach hienNoiGan />)
      )}

      {d && d.totalPages > 1 && (
        <div className="flex items-center justify-end gap-2">
          <Button size="sm" variant="outline" disabled={trang === 0} onClick={() => datTrang(trang - 1)}>
            Trước
          </Button>
          <span className="text-muted-foreground text-[13px] tabular-nums">
            {trang + 1} / {d.totalPages}
          </span>
          <Button size="sm" variant="outline" disabled={trang + 1 >= d.totalPages} onClick={() => datTrang(trang + 1)}>
            Sau
          </Button>
        </div>
      )}
    </div>
  )
}
