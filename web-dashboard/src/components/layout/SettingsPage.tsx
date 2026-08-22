import { AlertCircle } from 'lucide-react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { laLoiTruyVan } from '@/api/baseQuery'

export interface MucCaiDat {
  tieuDe: string
  moTa?: string
  noiDung: React.ReactNode
}

export interface SettingsPageProps {
  tieuDe: string
  moTa?: string
  muc: MucCaiDat[]
  /** Có thay đổi chưa lưu không. Quyết định thanh lưu có hiện hay không. */
  coThayDoi: boolean
  dangLuu?: boolean
  loi?: unknown
  onLuu: () => void
  onHuy: () => void
  dangTai?: boolean
  /** Khoá toàn bộ khi người dùng không đủ quyền, kèm lý do hiển thị ở đầu trang. */
  chiDoc?: { lyDo: string }
}

/**
 * Mẫu M4 — trang cài đặt. Phủ 3 màn hình (ADR-0011).
 *
 * Thanh lưu **dính đáy và chỉ hiện khi có thay đổi**: một thanh luôn hiện thì người dùng không
 * biết mình đã sửa gì chưa, còn nút Lưu nằm cuối trang dài thì phải cuộn xuống mới thấy.
 */
export function SettingsPage({
  tieuDe,
  moTa,
  muc,
  coThayDoi,
  dangLuu = false,
  loi,
  onLuu,
  onHuy,
  dangTai = false,
  chiDoc,
}: SettingsPageProps) {
  const thongDiepLoi = laLoiTruyVan(loi) ? loi.message : null

  if (dangTai) {
    return (
      <div className="flex flex-col gap-6 p-4">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-32 w-full max-w-3xl" />
        <Skeleton className="h-40 w-full max-w-3xl" />
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="flex max-w-3xl flex-col gap-6 p-4 pb-8">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight">{tieuDe}</h1>
            {moTa && <p className="text-muted-foreground text-[13px]">{moTa}</p>}
          </div>

          {chiDoc && (
            <Alert>
              <AlertCircle />
              <AlertDescription>{chiDoc.lyDo}</AlertDescription>
            </Alert>
          )}

          {muc.map((m, i) => (
            <section key={m.tieuDe} className="flex flex-col gap-3">
              {i > 0 && <Separator className="mb-3" />}
              <div className="flex flex-col gap-0.5">
                <h2 className="text-[15px] font-medium">{m.tieuDe}</h2>
                {m.moTa && (
                  <p className="text-muted-foreground text-[13px] leading-relaxed">{m.moTa}</p>
                )}
              </div>
              <fieldset disabled={Boolean(chiDoc)} className="flex flex-col gap-4">
                {m.noiDung}
              </fieldset>
            </section>
          ))}
        </div>
      </div>

      {coThayDoi && !chiDoc && (
        <div className="bg-background flex shrink-0 items-center gap-3 border-t px-4 py-2.5">
          {thongDiepLoi ? (
            <span className="text-destructive flex-1 text-[13px]">{thongDiepLoi}</span>
          ) : (
            <span className="text-muted-foreground flex-1 text-[13px]">Có thay đổi chưa lưu</span>
          )}
          <Button variant="outline" size="sm" onClick={onHuy} disabled={dangLuu}>
            Huỷ
          </Button>
          <Button size="sm" onClick={onLuu} disabled={dangLuu}>
            {dangLuu ? 'Đang lưu…' : 'Lưu thay đổi'}
          </Button>
        </div>
      )}
    </div>
  )
}
