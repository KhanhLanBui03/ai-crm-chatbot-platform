import { formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useTrangThaiThoiGianThuc } from '@/hooks/useThoiGianThuc'
import type { TrangThaiDuongTruyen } from '@/app/store/realtimeSlice'
import { cn } from '@/utils/cn'

const NHAN: Record<TrangThaiDuongTruyen, { chu: string; mau: string; nhapNhay: boolean }> = {
  dong: { chu: 'Ngoại tuyến', mau: 'bg-muted-foreground', nhapNhay: false },
  'dang-noi': { chu: 'Đang nối…', mau: 'bg-chart-3', nhapNhay: true },
  mo: { chu: 'Trực tuyến', mau: 'bg-chart-2', nhapNhay: false },
  'dang-noi-lai': { chu: 'Mất kết nối, đang thử lại…', mau: 'bg-chart-3', nhapNhay: true },
  loi: { chu: 'Không nối được', mau: 'bg-destructive', nhapNhay: false },
}

/** Vì sao mất kết nối — chỉ nói khi biết chắc, chứ không đoán từ mã đóng lạ. */
const LY_DO: Record<number, string> = {
  4401: 'Phiên đăng nhập đã hết hạn.',
  4403: 'Tài khoản không có quyền theo dõi hội thoại này.',
  4408: 'Máy chủ không nhận được khung xác thực kịp thời.',
  4429: 'Doanh nghiệp đã vượt số kết nối cho phép.',
}

/**
 * Chỉ báo đường truyền thời gian thực trên thanh trên.
 *
 * Trạng thái này **phải** hiện ra được. Một hộp thư đứng im vì mất kết nối trông y hệt một hộp
 * thư đứng im vì không có khách nhắn — và nhân viên chỉ phát hiện ra khác biệt khi khách gọi
 * điện hỏi vì sao không ai trả lời.
 */
export function ChiBaoThoiGianThuc() {
  const { duongTruyen, nhanKhungLuc, maDongCuoi } = useTrangThaiThoiGianThuc()
  const nhan = NHAN[duongTruyen]
  const binhThuong = duongTruyen === 'mo'

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={cn(
            'flex h-8 items-center gap-1.5 rounded-lg px-2 text-xs',
            binhThuong ? 'text-muted-foreground' : 'text-foreground bg-muted',
          )}
          role="status"
          aria-live="polite"
        >
          <span className={cn('size-[7px] rounded-full', nhan.mau, nhan.nhapNhay && 'animate-pulse')} />
          {/* Khi mọi thứ chạy tốt thì chấm là đủ — chỉ bung chữ ra khi có gì đó cần biết */}
          <span className={binhThuong ? 'sr-only' : undefined}>{nhan.chu}</span>
        </div>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-56">
        <p className="font-medium">{nhan.chu}</p>
        {maDongCuoi && LY_DO[maDongCuoi] ? <p>{LY_DO[maDongCuoi]}</p> : null}
        {nhanKhungLuc ? (
          <p className="opacity-80">
            Cập nhật gần nhất{' '}
            {formatDistanceToNowStrict(new Date(nhanKhungLuc), { addSuffix: true, locale: vi })}
          </p>
        ) : (
          <p className="opacity-80">Chưa nhận cập nhật nào.</p>
        )}
      </TooltipContent>
    </Tooltip>
  )
}
