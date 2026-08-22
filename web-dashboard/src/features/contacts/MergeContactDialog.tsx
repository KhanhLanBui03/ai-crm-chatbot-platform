import { AlertTriangle, ArrowRight, Search } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { useNavigate } from 'react-router-dom'

import { laLoiTruyVan } from '@/api/baseQuery'
import { useDanhSachKhachHangQuery, useHopNhatKhachHangMutation } from '@/api/contacts'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { useTriHoan } from '@/hooks/useTriHoan'
import type { KhachHang, KhachHangChiTiet } from '@/types/schema'
import { chuCaiDau } from '@/utils/ten'
import { cn } from '@/utils/cn'

/** Các trường có thể chọn giữ lại khi hai bản ghi khác nhau. */
const TRUONG: { khoa: keyof KhachHang; nhan: string }[] = [
  { khoa: 'fullName', nhan: 'Họ tên' },
  { khoa: 'phone', nhan: 'Điện thoại' },
  { khoa: 'email', nhan: 'Thư điện tử' },
]

/**
 * SCR025 — hợp nhất hai hồ sơ khách hàng. Màn chữ ký, dạng hộp thoại rộng.
 *
 * Không dùng mẫu M3 được: đây không phải một biểu mẫu điền vào ô trống mà là một **bảng so sánh
 * hai cột** để người dùng chọn từng trường giữ lại. Bố cục quyết định giá trị của màn — nhìn hai
 * giá trị cạnh nhau mới chọn được, còn một danh sách ô nhập thì phải nhớ bên kia đang có gì.
 *
 * Bản bị hợp nhất **không bị xoá**: nó chuyển sang `MERGED` và trỏ về bản giữ lại, vì mọi hội
 * thoại, cơ hội và hoạt động cũ vẫn đang trỏ tới nó.
 */
export function MergeContactDialog({
  mo,
  onDoiMo,
  giuLai,
}: {
  mo: boolean
  onDoiMo: (m: boolean) => void
  giuLai: KhachHangChiTiet
}) {
  const dieuHuong = useNavigate()
  const [oTim, datOTim] = useState('')
  const tuKhoa = useTriHoan(oTim)
  const [chon, datChon] = useState<KhachHang | null>(null)
  const [luaChon, datLuaChon] = useState<Record<string, 'giu' | 'gop'>>({})

  const timKiem = useDanhSachKhachHangQuery({ tuKhoa }, { skip: tuKhoa.length < 2 })
  const [hopNhat, ketQua] = useHopNhatKhachHangMutation()

  function dong(moMoi: boolean) {
    onDoiMo(moMoi)
    if (!moMoi) {
      datChon(null)
      datOTim('')
      datLuaChon({})
    }
  }

  const ungVien = (timKiem.data?.items ?? []).filter((k) => k.id !== giuLai.id)

  return (
    <Dialog open={mo} onOpenChange={dong}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Hợp nhất hồ sơ khách hàng</DialogTitle>
          <DialogDescription>
            Chọn hồ sơ trùng, rồi chọn giá trị giữ lại cho từng trường.
          </DialogDescription>
        </DialogHeader>

        {laLoiTruyVan(ketQua.error) && (
          <Alert variant="destructive">
            <AlertDescription>{ketQua.error.message}</AlertDescription>
          </Alert>
        )}

        {!chon ? (
          <div className="flex flex-col gap-3">
            <div className="relative">
              <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
              <Input
                className="pl-8"
                placeholder="Tìm hồ sơ cần gộp vào — theo tên, số điện thoại, thư…"
                value={oTim}
                onChange={(e) => datOTim(e.target.value)}
                autoFocus
              />
            </div>

            <div className="flex max-h-72 flex-col gap-1.5 overflow-y-auto">
              {tuKhoa.length < 2 ? (
                <p className="text-muted-foreground px-1 py-6 text-center text-[13px]">
                  Gõ ít nhất hai ký tự để tìm.
                </p>
              ) : timKiem.isFetching ? (
                <>
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </>
              ) : ungVien.length === 0 ? (
                <p className="text-muted-foreground px-1 py-6 text-center text-[13px]">
                  Không tìm thấy hồ sơ nào khớp.
                </p>
              ) : (
                ungVien.map((k) => (
                  <button
                    key={k.id}
                    type="button"
                    onClick={() => datChon(k)}
                    className="hover:bg-muted/60 flex items-center gap-2.5 rounded-lg border p-2.5 text-left transition-colors"
                  >
                    <div className="bg-secondary text-secondary-foreground flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium">
                      {chuCaiDau(k.fullName ?? '?')}
                    </div>
                    <div className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-[13px] font-medium">
                        {k.fullName ?? 'Chưa có tên'}
                      </span>
                      <span className="text-muted-foreground truncate text-xs">
                        {[k.phone, k.email].filter(Boolean).join(' · ') || 'Không có liên hệ'}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-[13px]">
              <span className="font-medium">Giữ lại</span>
              <span />
              <span className="text-muted-foreground font-medium">Gộp vào rồi đánh dấu MERGED</span>

              <TenHoSo khach={giuLai} />
              <ArrowRight className="text-muted-foreground size-4" />
              <TenHoSo khach={chon} mo />
            </div>

            <div className="flex flex-col gap-1.5">
              {TRUONG.map(({ khoa, nhan }) => {
                const a = giuLai[khoa] as string | null
                const b = chon[khoa] as string | null
                const khac = (a ?? '') !== (b ?? '')
                const dangChon = luaChon[khoa] ?? 'giu'
                return (
                  <div key={khoa} className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                    <ONhanhChon
                      nhan={nhan}
                      giaTri={a}
                      dangChon={!khac || dangChon === 'giu'}
                      coThebam={khac}
                      onChon={() => datLuaChon((c) => ({ ...c, [khoa]: 'giu' }))}
                    />
                    <span className="text-muted-foreground text-xs">
                      {khac ? 'khác' : '='}
                    </span>
                    <ONhanhChon
                      nhan={nhan}
                      giaTri={b}
                      dangChon={khac && dangChon === 'gop'}
                      coThebam={khac}
                      onChon={() => datLuaChon((c) => ({ ...c, [khoa]: 'gop' }))}
                    />
                  </div>
                )
              })}
            </div>

            <Alert>
              <AlertTriangle />
              <AlertDescription>
                Hợp nhất <strong>không xoá</strong> hồ sơ bên phải: nó chuyển sang trạng thái đã
                hợp nhất và trỏ về hồ sơ bên trái, để {chon.fullName ?? 'hồ sơ đó'} vẫn giữ được
                liên kết với các hội thoại cũ. Thao tác này không hoàn tác được.
              </AlertDescription>
            </Alert>
          </div>
        )}

        <DialogFooter>
          {chon && (
            <Button variant="ghost" onClick={() => datChon(null)} disabled={ketQua.isLoading}>
              Chọn hồ sơ khác
            </Button>
          )}
          <Button variant="outline" onClick={() => dong(false)} disabled={ketQua.isLoading}>
            Huỷ
          </Button>
          <Button
            disabled={!chon || ketQua.isLoading}
            onClick={async () => {
              if (!chon) return
              await hopNhat({
                id: giuLai.id,
                mergedContactId: chon.id,
                fieldChoices: Object.fromEntries(
                  Object.entries(luaChon).map(([k, v]) => [k, v === 'giu' ? giuLai.id : chon.id]),
                ),
              }).unwrap()
              toast.success('Đã hợp nhất hai hồ sơ.')
              dong(false)
              dieuHuong(`/khach-hang/${giuLai.id}`)
            }}
          >
            {ketQua.isLoading ? 'Đang hợp nhất…' : 'Hợp nhất'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function TenHoSo({ khach, mo }: { khach: KhachHang; mo?: boolean }) {
  return (
    <div className={cn('flex items-center gap-2 rounded-lg border p-2', mo && 'opacity-70')}>
      <div className="bg-secondary text-secondary-foreground flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-medium">
        {chuCaiDau(khach.fullName ?? '?')}
      </div>
      <span className="truncate font-medium">{khach.fullName ?? 'Chưa có tên'}</span>
      {mo && <StatusChip sacThai="neutral">sẽ thành MERGED</StatusChip>}
    </div>
  )
}

function ONhanhChon({
  nhan,
  giaTri,
  dangChon,
  coThebam,
  onChon,
}: {
  nhan: string
  giaTri: string | null
  dangChon: boolean
  coThebam: boolean
  onChon: () => void
}) {
  return (
    <button
      type="button"
      disabled={!coThebam}
      onClick={onChon}
      className={cn(
        'flex flex-col gap-0.5 rounded-lg border p-2 text-left transition-colors',
        dangChon ? 'ring-primary bg-primary/5 ring-1' : 'opacity-60',
        coThebam ? 'hover:bg-muted/60 cursor-pointer' : 'cursor-default',
      )}
    >
      <span className="text-muted-foreground text-xs">{nhan}</span>
      <span className="truncate text-[13px]">{giaTri || '—'}</span>
    </button>
  )
}
