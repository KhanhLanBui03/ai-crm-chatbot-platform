import { Workflow } from 'lucide-react'

/**
 * "Cách hoạt động" — luồng thật từ tin nhắn đầu tiên tới doanh thu, mỗi bước MỘT ẢNH CHỤP từ lần chạy hệ
 * thống (docs/report/*, chép sang public/landing/). Không có số liệu nào ở đây: chỉ là những gì người xem
 * sẽ thấy khi dùng thử.
 */
const BUOC = [
  {
    anh: '/landing/1-khach-nhan-widget.png',
    tieuDe: 'Khách nhắn trên website',
    moTa: 'Khung chat nhúng bằng một thẻ script. Khách hỏi bất cứ lúc nào, tự để lại tên và số điện thoại kèm đồng ý lưu dữ liệu.',
  },
  {
    anh: '/landing/2-hop-thu-chuyen-giao.png',
    tieuDe: 'AI trả lời — hoặc chuyển cho người',
    moTa: 'Trợ lý AI trả lời theo tài liệu. Khách xin gặp người hoặc AI không chắc thì hội thoại vào Hộp thư, giao cho nhân viên đang trực.',
  },
  {
    anh: '/landing/3-lead.png',
    tieuDe: 'Ghi nhận thành lead',
    moTa: 'Nhân viên tạo lead ngay từ hội thoại. Một khách chỉ một lead đang mở; loại lead phải chọn lý do để sau này biết vì sao mất khách.',
  },
  {
    anh: '/landing/4-pheu-deal.png',
    tieuDe: 'Chuyển thành deal, kéo trên phễu',
    moTa: 'Deal đi qua Mới tiếp nhận → Đã báo giá → Thương lượng → Thắng/Thua. Thiếu giá trị thì không qua được "Đã báo giá".',
  },
  {
    anh: '/landing/5-viec-cua-toi.png',
    tieuDe: 'Chăm sóc, không bỏ sót',
    moTa: 'Ghi cuộc gọi, báo giá và đặt giờ nhắc. "Việc của tôi" đưa việc quá hạn lên đầu, số đỏ trên menu nhắc mỗi khi mở hệ thống.',
  },
]

export function HowItWorksSection() {
  return (
    <section id="cach-hoat-dong" className="py-24">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3 border border-primary/20">
            <Workflow className="size-3.5" />
            <span>Cách Hoạt Động</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Từ Tin Nhắn Đầu Tiên <span className="text-primary">Tới Hợp Đồng</span>
          </h2>
          <p className="mt-3 text-base text-muted-foreground">
            Năm bước, năm màn hình chụp từ hệ thống đang chạy.
          </p>
        </div>

        <ol className="flex flex-col gap-14">
          {BUOC.map((b, i) => (
            <li key={b.anh} className="grid items-center gap-6 md:grid-cols-5">
              <div className={`md:col-span-2 ${i % 2 === 1 ? 'md:order-2' : ''}`}>
                <span className="text-sm font-bold text-primary">Bước {i + 1}</span>
                <h3 className="mt-1 text-xl font-bold text-foreground">{b.tieuDe}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{b.moTa}</p>
              </div>
              <div className={`md:col-span-3 ${i % 2 === 1 ? 'md:order-1' : ''}`}>
                <img
                  src={b.anh}
                  alt={b.tieuDe}
                  loading="lazy"
                  className="w-full rounded-xl border border-border shadow-lg"
                />
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
