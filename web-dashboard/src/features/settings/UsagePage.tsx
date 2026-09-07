import { format } from 'date-fns'
import { vi } from 'date-fns/locale'
import { AlertTriangle, ArrowRight, FileText, MessagesSquare, Users, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useHanMucHienTaiQuery } from '@/api/platform'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import type { MotHanMuc } from '@/types/schema'
import { cn } from '@/utils/cn'

const so = (v: number) => new Intl.NumberFormat('vi-VN').format(v)
const tien = (v: number) => new Intl.NumberFormat('vi-VN').format(Math.round(v)) + ' ₫'
const ngay = (s: string) => format(new Date(s), 'dd/MM', { locale: vi })

/**
 * SCR014 — hạn mức sử dụng của chu kỳ hiện tại. Màn chữ ký.
 *
 * **Bốn hạn mức, không phải năm.** Mô tả SCR014 ban đầu nêu cả hạn mức dung lượng lưu trữ, nhưng
 * ERD không có cột nào cho nó (ADR-0011). Bốn cái thật là hội thoại, token, người dùng, tài liệu.
 *
 * Điểm của màn này là **thứ tự**: ô nào sắp chạm ngưỡng thì lên trước, vì đó mới là thứ sắp làm
 * hệ thống ngừng phục vụ. Sắp theo tên cố định thì người dùng phải tự quét để tìm ra cái nguy.
 */
export function UsagePage() {
  const { data: hanMuc, isLoading } = useHanMucHienTaiQuery()

  if (isLoading || !hanMuc) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Skeleton className="h-7 w-56" />
        <div className="grid max-w-4xl gap-3 sm:grid-cols-2">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      </div>
    )
  }

  const o = [
    {
      khoa: 'conversations',
      nhan: 'Hội thoại',
      BieuTuong: MessagesSquare,
      moTa: 'Trục thu phí của gói. Một hội thoại tính một lần dù kéo dài bao lâu.',
      hanMuc: hanMuc.conversations,
      dinhDang: so,
    },
    {
      khoa: 'tokens',
      nhan: 'Token',
      BieuTuong: Zap,
      moTa: 'Cộng cả token vào và ra. Tài liệu dài làm phần token vào tăng nhanh nhất.',
      hanMuc: hanMuc.tokens,
      dinhDang: so,
    },
    {
      khoa: 'users',
      nhan: 'Người dùng',
      BieuTuong: Users,
      moTa: 'Tính cả người đang chờ kích hoạt — chỗ đã giữ là chỗ đã dùng.',
      hanMuc: hanMuc.users,
      dinhDang: so,
    },
    {
      khoa: 'documents',
      nhan: 'Tài liệu',
      BieuTuong: FileText,
      moTa: 'Tài liệu đã nạp vào kho tri thức, không tính tệp đính kèm của khách.',
      hanMuc: hanMuc.documents,
      dinhDang: so,
    },
  ].sort((a, b) => tyLe(b.hanMuc) - tyLe(a.hanMuc))

  const canhBao = o.find((x) => tyLe(x.hanMuc) >= 80)

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="flex max-w-4xl flex-col gap-5 p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight">Hạn mức sử dụng</h1>
            <p className="text-muted-foreground text-[13px] tabular-nums">
              Chu kỳ {ngay(hanMuc.periodStart)} – {ngay(hanMuc.periodEnd)} · chi phí AI đến giờ{' '}
              {tien(hanMuc.costVnd ?? 0)}
            </p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link to="/cai-dat/muc-su-dung">
              Xem theo ngày
              <ArrowRight />
            </Link>
          </Button>
        </div>

        {hanMuc.blockedAt ? (
          <Alert variant="destructive">
            <AlertTriangle />
            <AlertDescription>
              Đã chạm hạn mức ngày {format(new Date(hanMuc.blockedAt), 'dd/MM HH:mm')}. Tác tử AI
              ngừng trả lời khách; tin nhắn đến vẫn được ghi lại đầy đủ và nhân viên vẫn trả lời
              tay được.
            </AlertDescription>
          </Alert>
        ) : canhBao ? (
          <Alert>
            <AlertTriangle />
            <AlertDescription>
              <strong>{canhBao.nhan}</strong> đã dùng {tyLe(canhBao.hanMuc)}% hạn mức
              {hanMuc.warnedAt && ` (cảnh báo gửi ngày ${format(new Date(hanMuc.warnedAt), 'dd/MM')})`}
              . Chạm trần thì tác tử AI ngừng trả lời cho tới hết chu kỳ.
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-2">
          {o.map((x) => (
            <TheHanMuc key={x.khoa} {...x} />
          ))}
        </div>
      </div>
    </div>
  )
}

function tyLe(h: MotHanMuc): number {
  if (h.percent !== undefined) return Math.round(h.percent)
  return h.quota > 0 ? Math.round((h.used / h.quota) * 100) : 0
}

function TheHanMuc({
  nhan,
  BieuTuong,
  moTa,
  hanMuc,
  dinhDang,
}: {
  nhan: string
  BieuTuong: typeof Users
  moTa: string
  hanMuc: MotHanMuc
  dinhDang: (v: number) => string
}) {
  const phanTram = tyLe(hanMuc)
  const nguy = phanTram >= 95
  const gan = phanTram >= 80

  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-lg border p-4',
        nguy && 'border-destructive/40',
      )}
    >
      <div className="flex items-start gap-2.5">
        <div
          className={cn(
            'flex size-8 shrink-0 items-center justify-center rounded-lg',
            gan ? 'bg-destructive/10 text-destructive' : 'bg-muted text-muted-foreground',
          )}
        >
          <BieuTuong className="size-4" />
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="text-sm font-medium">{nhan}</span>
          <span className="text-muted-foreground text-xs leading-relaxed">{moTa}</span>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-lg font-semibold tabular-nums">{dinhDang(hanMuc.used)}</span>
          <span className="text-muted-foreground text-[13px] tabular-nums">
            / {dinhDang(hanMuc.quota)} · {phanTram}%
          </span>
        </div>
        <Progress
          value={Math.min(phanTram, 100)}
          className={gan ? '[&>div]:bg-destructive' : undefined}
        />
      </div>
    </div>
  )
}
