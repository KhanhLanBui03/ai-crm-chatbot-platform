import {
  Building2,
  CreditCard,
  Gauge,
  KeyRound,
  MessageSquareShare,
  Puzzle,
  Route,
  ShieldCheck,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { useAppSelector } from '@/app/store/hooks'
import { StatusChip } from '@/components/ui/status-chip'

interface MucCaiDat {
  duongDan: string
  nhan: string
  moTa: string
  BieuTuong: LucideIcon
  /** Chỉ quản trị doanh nghiệp thấy. */
  chiQuanTri?: boolean
}

const MUC: { nhom: string; muc: MucCaiDat[] }[] = [
  {
    nhom: 'Doanh nghiệp',
    muc: [
      {
        duongDan: '/cai-dat/doanh-nghiep',
        nhan: 'Hồ sơ doanh nghiệp',
        moTa: 'Tên, ngành hàng, múi giờ, giọng điệu của tác tử AI, chính sách lưu trữ.',
        BieuTuong: Building2,
      },
      {
        duongDan: '/cai-dat/nguoi-dung',
        nhan: 'Người dùng',
        moTa: 'Mời đồng nghiệp, đổi vai trò, vô hiệu hoá tài khoản.',
        BieuTuong: Users,
        chiQuanTri: true,
      },
      {
        duongDan: '/cai-dat/phan-quyen',
        nhan: 'Phân quyền',
        moTa: 'Ma trận quyền của hai vai trò TENANT_ADMIN và AGENT.',
        BieuTuong: ShieldCheck,
        chiQuanTri: true,
      },
    ],
  },
  {
    nhom: 'Gói và mức dùng',
    muc: [
      {
        duongDan: '/cai-dat/thue-bao',
        nhan: 'Thuê bao và gói dịch vụ',
        moTa: 'Gói hiện tại, chu kỳ, và bảng so sánh bốn gói.',
        BieuTuong: CreditCard,
        chiQuanTri: true,
      },
      {
        duongDan: '/cai-dat/han-muc',
        nhan: 'Hạn mức sử dụng',
        moTa: 'Hội thoại, token, người dùng, tài liệu trong chu kỳ hiện tại.',
        BieuTuong: Gauge,
      },
    ],
  },
  {
    nhom: 'Kết nối',
    muc: [
      {
        duongDan: '/cai-dat/quy-tac-phan-cong',
        nhan: 'Quy tắc phân công',
        moTa: 'Hội thoại và cơ hội tiềm năng tự về tay ai, theo thứ tự ưu tiên nào.',
        BieuTuong: Route,
        chiQuanTri: true,
      },
      {
        duongDan: '/cai-dat/kenh',
        nhan: 'Kênh',
        moTa: 'Zalo OA, Facebook Messenger, Web Widget.',
        BieuTuong: MessageSquareShare,
        chiQuanTri: true,
      },
      {
        duongDan: '/cai-dat/widget',
        nhan: 'Web Widget',
        moTa: 'Màu sắc, lời chào, mã nhúng cho website.',
        BieuTuong: Puzzle,
        chiQuanTri: true,
      },
    ],
  },
  {
    nhom: 'Tài khoản của bạn',
    muc: [
      {
        duongDan: '/cai-dat/phien',
        nhan: 'Phiên đăng nhập',
        moTa: 'Thiết bị đang đăng nhập, thu hồi phiên lạ.',
        BieuTuong: KeyRound,
      },
    ],
  },
]

/**
 * Trang chủ của khu cài đặt.
 *
 * Không phải một màn hình trong danh sách SCR — nó là điều hướng. Nhét mười mục cài đặt vào
 * thanh bên là làm loãng bảy mục nghiệp vụ mà nhân viên dùng mỗi ngày; gom vào một chỗ thì thanh
 * bên giữ được đúng những gì mở thường xuyên.
 */
export function SettingsIndexPage() {
  const laQuanTri = useAppSelector((s) => s.auth.nguoiDung?.roleCode === 'TENANT_ADMIN')

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="flex max-w-3xl flex-col gap-6 p-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-semibold tracking-tight">Cài đặt</h1>
          <p className="text-muted-foreground text-[13px]">
            Cấu hình của doanh nghiệp và của riêng tài khoản bạn.
          </p>
        </div>

        {MUC.map((n) => (
          <section key={n.nhom} className="flex flex-col gap-2">
            <h2 className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
              {n.nhom}
            </h2>
            <div className="flex flex-col gap-1.5">
              {n.muc.map((m) => (
                <Link
                  key={m.duongDan}
                  to={m.duongDan}
                  className="hover:bg-muted/50 flex items-start gap-3 rounded-lg border p-3 transition-colors"
                >
                  <div className="bg-muted text-muted-foreground flex size-8 shrink-0 items-center justify-center rounded-lg">
                    <m.BieuTuong className="size-4" />
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{m.nhan}</span>
                      {m.chiQuanTri && !laQuanTri && (
                        <StatusChip sacThai="neutral">Chỉ xem</StatusChip>
                      )}
                    </div>
                    <span className="text-muted-foreground text-[13px] leading-relaxed">
                      {m.moTa}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
