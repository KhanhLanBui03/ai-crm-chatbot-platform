import type {
  DanhTinhKenh,
  GhiChu,
  KenhChinh,
  KhachHang,
  KhachHangChiTiet,
  The,
  TrangThaiKhachHang,
} from '@/types/schema'

/**
 * Danh bạ giả cho SCR026.
 *
 * Đủ 23 bản ghi để phân trang có nghĩa (cỡ trang 25 thì một trang là chưa đủ để thấy phân trang
 * sai chỗ nào — ở đây cỡ trang mock đặt 10).
 */

const THE: Record<string, The> = {
  muaSi: { id: 't-03', name: 'Mua sỉ', color: '#2a78d6' },
  doanhNghiep: { id: 't-04', name: 'Doanh nghiệp', color: '#2a78d6' },
  baoHanh: { id: 't-01', name: 'Bảo hành', color: '#eda100' },
  khachQuayLai: { id: 't-02', name: 'Khách quay lại', color: '#1baf7a' },
  giaoHang: { id: 't-05', name: 'Giao hàng', color: '#eb6834' },
  vip: { id: 't-09', name: 'VIP', color: '#e87ba4' },
}

interface Tho {
  ten: string
  dt: string
  mail: string | null
  kenh: KenhChinh
  dongY: boolean
  the: The[]
  ngay: string
  trangThai?: TrangThaiKhachHang
}

const THO: Tho[] = [
  { ten: 'Nguyễn Thị Bích Hường', dt: '0903 118 274', mail: 'huong.ntb@gmail.com', kenh: 'WEB_WIDGET', dongY: true, the: [THE.baoHanh, THE.khachQuayLai], ngay: '2026-07-14' },
  { ten: 'Trần Quốc Dũng', dt: '0912 447 903', mail: 'dung.tq@vietphat.vn', kenh: 'ZALO', dongY: true, the: [THE.muaSi, THE.doanhNghiep], ngay: '2026-08-19' },
  { ten: 'Lý Thanh Hà', dt: '0987 220 145', mail: 'ha.ly@gmail.com', kenh: 'FACEBOOK', dongY: true, the: [THE.giaoHang], ngay: '2026-06-02' },
  { ten: 'Võ Thành Trung', dt: '0935 664 812', mail: null, kenh: 'WEB_WIDGET', dongY: true, the: [], ngay: '2026-08-21' },
  { ten: 'Đặng Thu Phương', dt: '0977 301 558', mail: null, kenh: 'ZALO', dongY: false, the: [], ngay: '2026-08-19' },
  { ten: 'Hoàng Minh Khôi', dt: '0904 887 231', mail: 'khoi.hm@caphedatviet.vn', kenh: 'WEB_WIDGET', dongY: true, the: [THE.doanhNghiep], ngay: '2026-08-21' },
  { ten: 'Phan Thị Mai Anh', dt: '0918 552 470', mail: 'maianh.phan@gmail.com', kenh: 'FACEBOOK', dongY: true, the: [THE.khachQuayLai, THE.vip], ngay: '2026-05-11' },
  { ten: 'Bùi Văn Sơn', dt: '0966 118 093', mail: 'son.bui@thienlong.com.vn', kenh: 'ZALO', dongY: true, the: [THE.muaSi], ngay: '2026-07-30' },
  { ten: 'Ngô Thị Kim Chi', dt: '0908 774 216', mail: null, kenh: 'PHONE', dongY: false, the: [], ngay: '2026-08-05' },
  { ten: 'Đỗ Hoàng Long', dt: '0973 640 852', mail: 'long.do@nhaviet.vn', kenh: 'WEB_WIDGET', dongY: true, the: [THE.doanhNghiep, THE.vip], ngay: '2026-04-18' },
  { ten: 'Vũ Thị Ngọc Bích', dt: '0932 907 441', mail: 'bich.vu@gmail.com', kenh: 'FACEBOOK', dongY: true, the: [THE.baoHanh], ngay: '2026-06-27' },
  { ten: 'Trịnh Anh Tuấn', dt: '0945 223 618', mail: 'tuan.trinh@gmail.com', kenh: 'ZALO', dongY: false, the: [], ngay: '2026-08-12' },
  { ten: 'Lê Thị Hồng Nhung', dt: '0901 336 749', mail: 'nhung.le@sieuthixanh.vn', kenh: 'WEB_WIDGET', dongY: true, the: [THE.muaSi, THE.doanhNghiep], ngay: '2026-03-09' },
  { ten: 'Cao Minh Đức', dt: '0983 771 204', mail: null, kenh: 'PHONE', dongY: true, the: [THE.giaoHang], ngay: '2026-07-21' },
  { ten: 'Hà Thị Thu Trang', dt: '0917 448 260', mail: 'trang.ha@gmail.com', kenh: 'FACEBOOK', dongY: true, the: [THE.khachQuayLai], ngay: '2026-05-30' },
  { ten: 'Dương Quốc Khánh', dt: '0962 015 883', mail: 'khanh.duong@vinatek.vn', kenh: 'ZALO', dongY: true, the: [THE.doanhNghiep], ngay: '2026-08-02' },
  { ten: 'Nguyễn Hữu Phước', dt: '0938 662 117', mail: null, kenh: 'WEB_WIDGET', dongY: false, the: [], ngay: '2026-08-16' },
  { ten: 'Tạ Thị Lan Hương', dt: '0906 219 574', mail: 'lanhuong.ta@gmail.com', kenh: 'FACEBOOK', dongY: true, the: [THE.baoHanh, THE.khachQuayLai], ngay: '2026-02-14' },
  { ten: 'Lâm Chí Thành', dt: '0975 803 442', mail: 'thanh.lam@hoaphat.net', kenh: 'ZALO', dongY: true, the: [THE.muaSi], ngay: '2026-07-08' },
  { ten: 'Phạm Thị Diễm My', dt: '0929 447 106', mail: null, kenh: 'PHONE', dongY: false, the: [], ngay: '2026-08-20' },
  { ten: 'Trương Bảo Nam', dt: '0949 220 785', mail: 'nam.truong@gmail.com', kenh: 'WEB_WIDGET', dongY: true, the: [THE.giaoHang], ngay: '2026-06-13' },
  // Hai bản ghi đã hợp nhất — mặc định KHÔNG hiện trong danh bạ, chỉ tra ra khi lọc theo trạng thái
  { ten: 'Nguyen Thi Bich Huong', dt: '0903118274', mail: null, kenh: 'ZALO', dongY: true, the: [], ngay: '2026-07-01', trangThai: 'MERGED' },
  { ten: 'Khách ẩn danh #4821', dt: '—', mail: null, kenh: 'WEB_WIDGET', dongY: false, the: [], ngay: '2026-01-22', trangThai: 'ANONYMIZED' },
]

export const danhSachKhachHang: KhachHang[] = THO.map((t, i) => ({
  id: `a1000000-0000-4000-8000-${String(i + 1).padStart(12, '0')}`,
  fullName: t.ten,
  phone: t.dt === '—' ? null : t.dt,
  email: t.mail,
  primaryChannel: t.kenh,
  status: t.trangThai ?? 'ACTIVE',
  consentGranted: t.dongY,
  consentAt: t.dongY ? `${t.ngay}T09:00:00+07:00` : null,
  tags: t.the,
  // Lần tương tác gần nhất giãn ra theo thứ tự để cột này sắp xếp được có nghĩa
  lastInteractionAt: `2026-08-${String(21 - Math.min(i, 20)).padStart(2, '0')}T14:30:00+07:00`,
  createdAt: `${t.ngay}T09:00:00+07:00`,
}))

// ── SCR024 hồ sơ chi tiết ─────────────────────────────────────────────────────

/**
 * Chi tiết dựng từ chính danh sách, cộng phần chỉ có ở màn hồ sơ.
 *
 * `channelIdentities` là lý do màn này tồn tại: một người có thể nhắn từ widget hôm nay và từ
 * Zalo tuần sau: hai `channel_identities`, một `contact`. Không nhìn thấy chúng thì không hiểu
 * vì sao hệ thống gộp hai luồng tin nhắn vào một hồ sơ.
 */
export const chiTietKhachHang: Record<string, KhachHangChiTiet> = Object.fromEntries(
  danhSachKhachHang.map((k, i) => {
    const danhTinh: DanhTinhKenh[] = []
    if (k.primaryChannel && k.primaryChannel !== 'PHONE') {
      danhTinh.push({
        id: `di-${i}-1`,
        channelType: k.primaryChannel,
        externalUserId: `${k.primaryChannel.toLowerCase()}_${1000 + i}`,
        displayName: k.fullName,
        avatarUrl: null,
        originDomain: k.primaryChannel === 'WEB_WIDGET' ? 'cattuong.vn' : null,
        lastSeenAt: k.lastInteractionAt,
      })
    }
    // Vài khách có danh tính thứ hai — đúng tình huống mà việc hợp nhất sinh ra
    if (i % 4 === 1) {
      danhTinh.push({
        id: `di-${i}-2`,
        channelType: 'ZALO',
        externalUserId: `zalo_${7000 + i}`,
        displayName: k.fullName,
        avatarUrl: null,
        originDomain: null,
        lastSeenAt: k.createdAt,
      })
    }
    return [
      k.id,
      {
        ...k,
        mergedIntoContactId: k.status === 'MERGED' ? danhSachKhachHang[0].id : null,
        channelIdentities: danhTinh,
        conversationCount: 1 + ((i * 3) % 7),
        openLeadCount: i % 3 === 0 ? 1 : 0,
        openDealCount: i % 5 === 0 ? 1 : 0,
        totalDealValue: i % 5 === 0 ? (i + 1) * 4_500_000 : 0,
        anonymizedAt: k.status === 'ANONYMIZED' ? '2026-08-01T00:00:00+07:00' : null,
      } satisfies KhachHangChiTiet,
    ]
  }),
)

// ── SCR028 ghi chú nội bộ ─────────────────────────────────────────────────────

const AN = 'u1000000-0000-4000-8000-000000000001'
const TUAN = 'u1000000-0000-4000-8000-000000000002'

export const ghiChuKhachHang: Record<string, GhiChu[]> = {
  [danhSachKhachHang[0].id]: [
    {
      id: 'gc-001',
      content: 'Khách chỉ rảnh cuối tuần, đã hẹn kỹ thuật gọi lại sáng thứ Bảy.',
      conversationId: null,
      authorUserId: TUAN,
      authorName: 'Lê Minh Tuấn',
      flaggedSensitive: false,
      canEdit: false,
      editedAt: null,
      createdAt: '2026-08-21T09:40:00+07:00',
    },
    {
      id: 'gc-002',
      // Ghi chú chứa dữ liệu cá nhân bị đánh dấu — Nghị định 13, và nó phải hiện ra được
      content: 'Khách đọc số CCCD qua điện thoại để đối chiếu bảo hành: 0790xxxxxxx.',
      conversationId: null,
      authorUserId: AN,
      authorName: 'Phạm Hoài An',
      flaggedSensitive: true,
      canEdit: true,
      editedAt: null,
      createdAt: '2026-08-20T16:12:00+07:00',
    },
  ],
  [danhSachKhachHang[1].id]: [
    {
      id: 'gc-003',
      content: 'Đơn 200 bộ cần giao trước 15/09, khách đã xác nhận bằng văn bản.',
      conversationId: null,
      authorUserId: AN,
      authorName: 'Phạm Hoài An',
      flaggedSensitive: false,
      canEdit: true,
      editedAt: null,
      createdAt: '2026-08-21T11:02:00+07:00',
    },
  ],
}

export const danhSachThe: The[] = Object.values(THE).map((t, i) => ({
  ...t,
  usageCount: 12 - i * 2,
}))
