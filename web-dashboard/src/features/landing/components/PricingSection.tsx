import { ArrowRight, Check, RefreshCw, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useDanhSachGoiQuery } from '@/api/platform'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { GoiDichVu } from '@/types/schema'

/**
 * Bảng giá ĐỌC TỪ HỆ THỐNG (`GET /api/v1/plans`, công khai) — trước đây ghi tay và lệch hẳn gói thật
 * (Starter 0đ "trọn đời", Professional 499.000đ…). Quản trị nền tảng đổi giá là trang chủ đổi theo.
 *
 * Không có thanh toán theo năm: CSDL chỉ có giá tháng, nên bỏ nút "-20%" từng có ở đây.
 */
const GOI_GOI_Y = 'GROWTH'

/** Tính năng có ở MỌI gói — đều đã chạy thật. */
const CHUNG = [
  'Khung chat nhúng website',
  'Hộp thư hợp nhất, chuyển giao AI → nhân viên',
  'Lead, phễu Deal kéo thả, nhắc việc',
  'Nhật ký kiểm toán',
]

const so = (n: number) => new Intl.NumberFormat('vi-VN').format(n)

function moTa(g: GoiDichVu): string[] {
  const kenh = (g as GoiDichVu & { maxChannels?: number }).maxChannels
  return [
    `${so(g.conversationQuota)} cuộc hội thoại AI mỗi chu kỳ`,
    g.maxUsers ? `${so(g.maxUsers)} tài khoản nhân viên` : null,
    g.maxDocuments ? `${so(g.maxDocuments)} tài liệu trong kho tri thức` : null,
    kenh ? `${so(kenh)} kênh chat` : null,
  ].filter((x): x is string => x !== null)
}

export function PricingSection() {
  const goi = useDanhSachGoiQuery()

  return (
    <section id="bang-gia" className="py-24 bg-muted/20 border-y border-border/60 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <Sparkles className="size-3.5" />
            <span>Chi Phí Minh Bạch</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Bảng Giá Theo <span className="text-primary">Số Cuộc Hội Thoại</span>
          </h2>
          <p className="mt-3 text-base text-muted-foreground">
            Dùng thử 14 ngày miễn phí, sau đó chọn gói theo lượng khách bạn cần AI tiếp. Hết hạn mức thì hội thoại
            tự chuyển cho nhân viên — khách không bị bỏ lơ.
          </p>
        </div>

        <div className={goi.data ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 items-stretch' : ''}>
          {goi.isLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-96 rounded-2xl" />
              ))}
            </div>
          )}

          {goi.isError && (
            <div className="mx-auto flex max-w-md flex-col items-center gap-3 rounded-2xl border bg-card p-8 text-center">
              <p className="text-sm text-muted-foreground">Chưa tải được bảng giá. Bạn thử lại sau ít phút nhé.</p>
              <Button variant="outline" size="sm" onClick={() => void goi.refetch()}>
                <RefreshCw />
                Thử lại
              </Button>
            </div>
          )}

          {goi.data?.map((g) => {
            const goiY = g.code === GOI_GOI_Y
            const dungThu = g.code === 'TRIAL'
            return (
              <div
                key={g.code}
                className={`relative rounded-2xl p-7 flex flex-col justify-between ${
                  goiY ? 'bg-card border-2 border-primary shadow-xl shadow-primary/10' : 'bg-card border border-border shadow-sm'
                }`}
              >
                {goiY && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-xs font-bold px-3.5 py-1 rounded-full shadow-md whitespace-nowrap">
                    Gợi ý cho đa số SME
                  </div>
                )}
                <div>
                  <h3 className="text-xl font-bold text-foreground">{g.name}</h3>
                  <div className="mt-5 flex flex-wrap items-baseline gap-x-1">
                    <span className="text-2xl xl:text-3xl font-extrabold text-foreground whitespace-nowrap">
                      {so(g.monthlyPriceVnd)} đ
                    </span>
                    <span className="text-xs text-muted-foreground font-medium">
                      {dungThu ? '/ 14 ngày' : '/ tháng'}
                    </span>
                  </div>
                  <ul className="mt-6 pt-6 border-t border-border/60 space-y-2.5 text-xs">
                    {[...moTa(g), ...CHUNG].map((t) => (
                      <li key={t} className="flex items-start gap-2">
                        <Check className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                        <span className="text-foreground/90">{t}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <Button
                  asChild
                  variant={goiY ? 'default' : 'outline'}
                  size="lg"
                  className="mt-8 w-full rounded-xl font-semibold"
                >
                  <Link to="/dang-ky" className="flex items-center justify-center gap-1.5">
                    {dungThu ? 'Dùng thử miễn phí' : 'Bắt đầu dùng thử'}
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>
            )
          })}
        </div>
        {goi.data && (
          <p className="mt-6 text-center text-xs text-muted-foreground">
            Mọi doanh nghiệp bắt đầu bằng 14 ngày dùng thử, sau đó đổi sang gói phù hợp trong phần Cài đặt.
          </p>
        )}
      </div>
    </section>
  )
}
