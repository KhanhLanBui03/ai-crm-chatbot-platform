import { Check, Sparkles } from 'lucide-react'

const DIEM_BAN = [
  'Web Widget, Zalo OA và Messenger trong một hộp thư',
  'Dữ liệu mỗi doanh nghiệp cô lập ở tầng cơ sở dữ liệu',
  'Tuân thủ Nghị định 13/2023/NĐ-CP về dữ liệu cá nhân',
]

/**
 * Khung chung của bốn màn ngoài phạm vi đăng nhập: SCR001 đăng ký, SCR003 đăng nhập,
 * SCR004 quên mật khẩu, SCR005 đặt lại mật khẩu.
 *
 * Bảng thương hiệu bên trái ẩn dưới `lg`. Trên màn hình hẹp nó chiếm gần trọn chiều cao và đẩy
 * biểu mẫu xuống dưới nếp gấp — người vào để đăng nhập lại phải cuộn qua một đoạn quảng cáo.
 */
export function AuthLayout({
  tieuDe,
  phuDe,
  chanTrang,
  children,
}: {
  tieuDe: string
  phuDe?: React.ReactNode
  chanTrang?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="bg-background text-foreground flex min-h-screen">
      {/* Bảng thương hiệu — nền phẳng pha màu chủ đạo, không dùng chuyển sắc */}
      <div className="bg-primary/6 hidden w-[560px] shrink-0 flex-col justify-between border-r p-12 lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-md">
            <Sparkles className="size-[18px]" />
          </div>
          <span className="text-base font-semibold">CRM AI</span>
        </div>

        <div className="flex flex-col gap-6">
          <h1 className="text-[34px] leading-tight font-semibold tracking-tight text-pretty">
            Trả lời khách hàng suốt ngày đêm, và biến câu hỏi thành cơ hội bán hàng.
          </h1>
          <p className="text-muted-foreground max-w-[420px] text-[15px] leading-relaxed text-pretty">
            Tác tử AI trả lời dựa trên tài liệu của chính doanh nghiệp bạn, chuyển giao cho nhân
            viên khi gặp việc ngoài khả năng, và tự chấm điểm khách hàng tiềm năng.
          </p>
        </div>

        <ul className="flex list-none flex-col gap-3 p-0">
          {DIEM_BAN.map((d) => (
            <li key={d} className="flex items-center gap-2.5 text-sm">
              <Check className="text-success size-4 shrink-0" />
              {d}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-1 items-center justify-center p-6 sm:p-12">
        <div className="flex w-full max-w-md flex-col gap-6">
          <div className="flex flex-col gap-1.5">
            <h2 className="text-2xl font-semibold tracking-tight">{tieuDe}</h2>
            {phuDe && <div className="text-muted-foreground text-sm">{phuDe}</div>}
          </div>

          {children}

          {chanTrang && (
            <p className="text-muted-foreground text-xs leading-relaxed">{chanTrang}</p>
          )}
        </div>
      </div>
    </div>
  )
}
