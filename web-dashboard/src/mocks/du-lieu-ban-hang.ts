import { danhSachKhachHang } from '@/mocks/du-lieu-khach-hang'
import { daySoNgay } from '@/mocks/tienIch'
import type {
  BacPheu,
  Deal,
  DealChiTiet,
  HoatDong,
  Lead,
  LeadChiTiet,
  Pheu,
  TepBaoCao,
  ThongKeChuDe,
  TongQuan,
  DiemHoiThoaiNgay,
} from '@/types/schema'

/**
 * Dữ liệu giả cho C4 — bán hàng và phân tích (SCR041–SCR053).
 *
 * Số liệu cố ý **nhất quán với nhau**: số lead sinh ra trong bảng phễu phải khớp số dòng của
 * danh sách lead, tổng giá trị deal của Kanban phải khớp thẻ KPI. Bịa từng chỗ một cho đẹp mắt
 * là biến màn phân tích thành một bức tranh, và bức tranh đó không phát hiện được lỗi cộng dồn.
 */

const U = (n: number) => `u1000000-0000-4000-8000-00000000000${n}`
const NGAY_MOC = new Date('2026-08-21')
const gio = (ngay: string, hhmm = '09:00') => `${ngay}T${hhmm}:00+07:00`

// ── Phễu bán hàng ─────────────────────────────────────────────────────────────

const GIAI_DOAN = [
  { id: 'gd-1', name: 'Mới tiếp nhận', position: 0, probability: 10, isWon: false, isLost: false },
  { id: 'gd-2', name: 'Đã báo giá', position: 1, probability: 35, isWon: false, isLost: false },
  { id: 'gd-3', name: 'Đang thương lượng', position: 2, probability: 60, isWon: false, isLost: false },
  { id: 'gd-4', name: 'Thắng', position: 3, probability: 100, isWon: true, isLost: false },
  { id: 'gd-5', name: 'Thua', position: 4, probability: 0, isWon: false, isLost: true },
]

const PHEU_ID = 'ph-mac-dinh'

// ── SCR041 cơ hội tiềm năng ───────────────────────────────────────────────────

interface ThoLead {
  i: number
  sp: string
  min: number | null
  max: number | null
  diem: number | null
  trangThai: Lead['status']
  nguon: Lead['source']
  chu: number | null
  ngay: string
}

const THO_LEAD: ThoLead[] = [
  { i: 1, sp: 'Máy lọc nước RO 10 lõi', min: 8_000_000, max: 12_000_000, diem: 87, trangThai: 'QUALIFIED', nguon: 'AI_AUTO', chu: 2, ngay: '2026-08-21' },
  { i: 2, sp: '200 bộ ấm siêu tốc', min: 90_000_000, max: 120_000_000, diem: 94, trangThai: 'QUALIFIED', nguon: 'AI_AUTO', chu: 3, ngay: '2026-08-21' },
  { i: 3, sp: 'Bếp từ đôi', min: 6_000_000, max: 9_000_000, diem: 61, trangThai: 'CONTACTED', nguon: 'AI_AUTO', chu: 2, ngay: '2026-08-20' },
  { i: 4, sp: 'Nồi chiên không dầu', min: null, max: null, diem: 44, trangThai: 'NEW', nguon: 'AI_AUTO', chu: null, ngay: '2026-08-20' },
  { i: 6, sp: 'Máy pha cà phê cho quán', min: 25_000_000, max: 40_000_000, diem: 79, trangThai: 'CONVERTED', nguon: 'AI_AUTO', chu: 3, ngay: '2026-08-18' },
  { i: 7, sp: 'Combo gia dụng khai trương', min: 15_000_000, max: 22_000_000, diem: 72, trangThai: 'CONTACTED', nguon: 'MANUAL', chu: 2, ngay: '2026-08-17' },
  { i: 8, sp: '50 bình giữ nhiệt in logo', min: 18_000_000, max: 25_000_000, diem: 68, trangThai: 'QUALIFIED', nguon: 'AI_AUTO', chu: 4, ngay: '2026-08-16' },
  { i: 10, sp: 'Hệ thống lọc tổng cho toà nhà', min: 120_000_000, max: 180_000_000, diem: 91, trangThai: 'CONVERTED', nguon: 'MANUAL', chu: 3, ngay: '2026-08-14' },
  { i: 11, sp: 'Máy hút bụi công nghiệp', min: null, max: null, diem: 38, trangThai: 'DISQUALIFIED', nguon: 'AI_AUTO', chu: null, ngay: '2026-08-13' },
  { i: 13, sp: 'Tủ mát trưng bày', min: 30_000_000, max: 45_000_000, diem: 83, trangThai: 'QUALIFIED', nguon: 'AI_AUTO', chu: 2, ngay: '2026-08-12' },
  { i: 14, sp: 'Lò vi sóng gia đình', min: 3_000_000, max: 5_000_000, diem: 52, trangThai: 'CONTACTED', nguon: 'MANUAL', chu: 4, ngay: '2026-08-11' },
  { i: 15, sp: 'Máy rửa bát 14 bộ', min: 14_000_000, max: 20_000_000, diem: 76, trangThai: 'NEW', nguon: 'AI_AUTO', chu: null, ngay: '2026-08-10' },
]

const khach = (i: number) => danhSachKhachHang[i - 1] ?? danhSachKhachHang[0]

export const danhSachLead: Lead[] = THO_LEAD.map((t, n) => ({
  id: `ld-${String(n + 1).padStart(3, '0')}`,
  contactId: khach(t.i).id,
  contactName: khach(t.i).fullName ?? 'Khách chưa có tên',
  contactPhone: khach(t.i).phone,
  sourceConversationId: t.nguon === 'AI_AUTO' ? `c1000000-0000-4000-8000-00000000000${(n % 5) + 1}` : null,
  source: t.nguon,
  status: t.trangThai,
  interestedProduct: t.sp,
  budgetMin: t.min,
  budgetMax: t.max,
  budgetConfidence: t.min ? (t.diem! > 80 ? 'HIGH' : 'MEDIUM') : null,
  urgency: t.diem! > 80 ? 'HIGH' : t.diem! > 60 ? 'MEDIUM' : 'LOW',
  currentScore: t.diem,
  scoreUpdatedAt: gio(t.ngay, '10:15'),
  ownerUserId: t.chu ? U(t.chu) : null,
  ownerName: t.chu ? ['', '', 'Lê Minh Tuấn', 'Võ Thị Kim Ngân', 'Trịnh Bảo Long'][t.chu] : null,
  createdAt: gio(t.ngay),
}))

export const chiTietLead: Record<string, LeadChiTiet> = Object.fromEntries(
  danhSachLead.map((l, n) => [
    l.id,
    {
      ...l,
      latestScore:
        l.currentScore == null
          ? null
          : {
              score: l.currentScore,
              modelVersion: 'lead-scoring-v0.3',
              scoringMode: l.source === 'AI_AUTO' ? 'ML' : 'RULE',
              // `LOW` nghĩa là **thiếu đặc trưng bắt buộc**, không phải "điểm thấp" — hai chuyện
              // khác hẳn nhau. Lead không nêu ngân sách thì mô hình thiếu đầu vào, điểm ra không
              // đáng tin dù nó cao hay thấp.
              confidence: l.budgetMin == null ? 'LOW' : 'NORMAL',
              computedAt: l.scoreUpdatedAt!,
              topFactors: [
                { name: 'Hỏi giá và tồn kho', contribution: 24, value: null },
                { name: 'Ngân sách nêu rõ', contribution: l.budgetMin ? 19 : 0, value: l.budgetMin ? 'có' : null },
                { name: 'Đã mua trước đây', contribution: n % 3 === 0 ? 14 : 0, value: n % 3 === 0 ? '2' : null },
                // Yếu tố âm: điểm không chỉ cộng lên, và người dùng cần thấy cái gì kéo xuống
                { name: 'Chưa để lại thư công ty', contribution: -6, value: null },
              ],
            },
      disqualifyReason: l.status === 'DISQUALIFIED' ? 'Khách hỏi sản phẩm bên mình không kinh doanh.' : null,
      convertedDealId: l.status === 'CONVERTED' ? `dl-${String(n + 1).padStart(3, '0')}` : null,
      convertedAt: l.status === 'CONVERTED' ? gio(l.createdAt.slice(0, 10), '15:20') : null,
      activityCount: (n % 4) + 1,
      closedAt: ['CONVERTED', 'DISQUALIFIED'].includes(l.status) ? gio(l.createdAt.slice(0, 10), '15:20') : null,
    } satisfies LeadChiTiet,
  ]),
)

// ── SCR044 cơ hội bán hàng ────────────────────────────────────────────────────

interface ThoDeal {
  i: number
  ten: string
  tien: number
  gd: string
  chu: number
  hanChot: string
  trangThai?: Deal['status']
}

const THO_DEAL: ThoDeal[] = [
  { i: 2, ten: 'Đơn 200 bộ ấm siêu tốc — Việt Phát', tien: 104_000_000, gd: 'gd-3', chu: 3, hanChot: '2026-09-15' },
  { i: 6, ten: 'Máy pha cà phê — Cà phê Đất Việt', tien: 32_000_000, gd: 'gd-2', chu: 3, hanChot: '2026-09-05' },
  { i: 10, ten: 'Lọc tổng toà nhà — Nhà Việt', tien: 156_000_000, gd: 'gd-3', chu: 3, hanChot: '2026-10-01' },
  { i: 1, ten: 'Máy lọc nước RO — chị Hường', tien: 9_800_000, gd: 'gd-1', chu: 2, hanChot: '2026-09-02' },
  { i: 8, ten: '50 bình giữ nhiệt in logo — Thiên Long', tien: 21_500_000, gd: 'gd-2', chu: 4, hanChot: '2026-09-10' },
  { i: 13, ten: 'Tủ mát trưng bày — Siêu thị Xanh', tien: 38_000_000, gd: 'gd-1', chu: 2, hanChot: '2026-09-20' },
  // Đã quá hạn chốt mà vẫn mở — chính là thứ Kanban phải bôi đỏ
  { i: 7, ten: 'Combo khai trương — anh Sơn', tien: 18_000_000, gd: 'gd-2', chu: 2, hanChot: '2026-08-10' },
  { i: 14, ten: 'Lò vi sóng — chị Trang', tien: 4_200_000, gd: 'gd-4', chu: 4, hanChot: '2026-08-15', trangThai: 'WON' },
  { i: 11, ten: 'Máy hút bụi công nghiệp — anh Tuấn', tien: 26_000_000, gd: 'gd-5', chu: 2, hanChot: '2026-08-08', trangThai: 'LOST' },
]

const TEN_CHU = ['', '', 'Lê Minh Tuấn', 'Võ Thị Kim Ngân', 'Trịnh Bảo Long']

export const danhSachDeal: Deal[] = THO_DEAL.map((t, n) => {
  const gd = GIAI_DOAN.find((g) => g.id === t.gd)!
  const trangThai = t.trangThai ?? 'OPEN'
  return {
    id: `dl-${String(n + 1).padStart(3, '0')}`,
    contactId: khach(t.i).id,
    contactName: khach(t.i).fullName ?? 'Khách chưa có tên',
    leadId: danhSachLead.find((l) => l.contactId === khach(t.i).id)?.id ?? null,
    pipelineId: PHEU_ID,
    stageId: t.gd,
    stageName: gd.name,
    title: t.ten,
    amount: t.tien,
    currency: 'VND',
    expectedCloseDate: t.hanChot,
    isOverdue: trangThai === 'OPEN' && t.hanChot < '2026-08-21',
    status: trangThai,
    source: n % 3 === 2 ? 'MANUAL' : 'AI_LEAD',
    ownerUserId: U(t.chu),
    ownerName: TEN_CHU[t.chu],
    stageChangedAt: gio('2026-08-19', '14:00'),
    createdAt: gio('2026-08-12'),
  }
})

export const danhSachPheu: Pheu[] = [
  {
    id: PHEU_ID,
    name: 'Phễu bán hàng mặc định',
    isDefault: true,
    isActive: true,
    stages: GIAI_DOAN.map((g) => {
      const cua = danhSachDeal.filter((d) => d.stageId === g.id)
      return {
        ...g,
        requiredFields: g.position >= 1 ? ['amount'] : [],
        dealCount: cua.length,
        dealValueTotal: cua.reduce((t, d) => t + (d.amount ?? 0), 0),
      }
    }),
  },
]

export const chiTietDeal: Record<string, DealChiTiet> = Object.fromEntries(
  danhSachDeal.map((d) => [
    d.id,
    {
      ...d,
      closeReason: d.status === 'LOST' ? 'Khách chốt bên khác vì giao nhanh hơn.' : null,
      closedAt: d.status === 'OPEN' ? null : gio('2026-08-19', '16:30'),
      stageHistory: GIAI_DOAN.filter((g) => g.position <= (GIAI_DOAN.find((x) => x.id === d.stageId)?.position ?? 0)).map(
        (g, i, ds) => ({
          fromStageId: i === 0 ? null : ds[i - 1].id,
          fromStageName: i === 0 ? null : ds[i - 1].name,
          toStageId: g.id,
          toStageName: g.name,
          durationSeconds: (i + 1) * 86_400,
          changedByName: d.ownerName,
          changedAt: gio(`2026-08-${String(12 + i * 2).padStart(2, '0')}`, '10:00'),
        }),
      ),
      activities: [],
    } satisfies DealChiTiet,
  ]),
)

// ── SCR047 hoạt động ──────────────────────────────────────────────────────────

const LOAI: HoatDong['type'][] = ['CALL', 'MEETING', 'QUOTE', 'EMAIL', 'NOTE']
const KET_QUA: NonNullable<HoatDong['outcome']>[] = ['DONE', 'NO_ANSWER', 'REFUSED', 'RESCHEDULED']

export const danhSachHoatDong: HoatDong[] = Array.from({ length: 18 }, (_, n) => {
  const d = danhSachDeal[n % danhSachDeal.length]
  const loai = LOAI[n % LOAI.length]
  const coNhac = n % 4 === 0
  return {
    id: `hd-${String(n + 1).padStart(3, '0')}`,
    contactId: d.contactId,
    contactName: d.contactName,
    leadId: null,
    dealId: d.id,
    type: loai,
    subject:
      loai === 'CALL'
        ? 'Gọi xác nhận nhu cầu'
        : loai === 'MEETING'
          ? 'Hẹn khảo sát tại cửa hàng'
          : loai === 'QUOTE'
            ? 'Gửi báo giá'
            : loai === 'EMAIL'
              ? 'Gửi thư giới thiệu sản phẩm'
              : 'Ghi chú nội bộ',
    content: null,
    outcome: KET_QUA[n % KET_QUA.length],
    source: n % 5 === 0 ? 'AUTO' : 'MANUAL',
    performedBy: d.ownerUserId!,
    performedByName: d.ownerName!,
    performedAt: gio(`2026-08-${String(21 - (n % 10)).padStart(2, '0')}`, '11:30'),
    remindAt: coNhac ? gio(`2026-08-${String(22 + (n % 5)).padStart(2, '0')}`, '09:00') : null,
    remindUserId: coNhac ? d.ownerUserId : null,
    remindStatus: coNhac ? (n % 8 === 0 ? 'PENDING' : 'SENT') : 'NONE',
    createdAt: gio(`2026-08-${String(21 - (n % 10)).padStart(2, '0')}`, '11:30'),
  }
})

// ── SCR048 tổng quan ──────────────────────────────────────────────────────────

const dealThang = danhSachDeal.filter((d) => d.status === 'WON')

export const tongQuan: TongQuan = {
  updatedAt: gio('2026-08-21', '11:00'),
  conversationsStarted: 4_812,
  conversationsResolved: 4_517,
  // 0.72 nghĩa là 72% hội thoại tác tử tự đóng được — chỉ số trung tâm của đề tài
  botResolvedRate: 0.72,
  handoffs: 1_264,
  avgFirstResponseSeconds: 42,
  avgResolutionSeconds: 1_780,
  messagesIn: 18_442,
  messagesOut: 21_037,
  leadsCreated: danhSachLead.length,
  dealsWon: dealThang.length,
  dealValueTotal: dealThang.reduce((t, d) => t + (d.amount ?? 0), 0),
  costVnd: 3_284_000,
  pendingConversations: 7,
}

// ── SCR049 hội thoại theo ngày ────────────────────────────────────────────────

const KENH = ['WEB_WIDGET', 'ZALO', 'FACEBOOK']

export const hoiThoaiTheoNgay: DiemHoiThoaiNgay[] = daySoNgay(21, NGAY_MOC).flatMap((ngay, i) =>
  KENH.map((kenh, k) => {
    const batDau = [92, 54, 31][k] + ((i * 7 + k * 3) % 17)
    const botXong = Math.round(batDau * (0.68 + ((i % 5) * 0.02)))
    const daXong = botXong + Math.round(batDau * 0.2)
    return {
      statDate: ngay,
      channelType: kenh,
      assignedUserId: null,
      assignedUserName: null,
      conversationsStarted: batDau,
      conversationsResolved: daXong,
      botResolved: botXong,
      handoffs: batDau - botXong,
      messagesIn: batDau * 4,
      messagesOut: batDau * 5,
      avgFirstResponseSeconds: 30 + ((i * 5 + k * 7) % 40),
    }
  }),
)

// ── SCR050 phễu chuyển đổi ────────────────────────────────────────────────────

export const pheuChuyenDoi: BacPheu[] = daySoNgay(14, NGAY_MOC).flatMap((ngay, i) =>
  (['AI_AUTO', 'MANUAL'] as const).map((nguon) => {
    const tong = nguon === 'AI_AUTO' ? 120 + ((i * 11) % 40) : 18 + (i % 7)
    const coTinHieu = Math.round(tong * 0.31)
    const lead = Math.round(coTinHieu * 0.42)
    const deal = Math.round(lead * 0.38)
    const thang = Math.round(deal * 0.34)
    return {
      statDate: ngay,
      leadSource: nguon,
      channelType: 'WEB_WIDGET',
      conversationsTotal: tong,
      conversationsWithSignal: coTinHieu,
      leadsCreated: lead,
      dealsCreated: deal,
      dealsWon: thang,
      dealValueTotal: thang * 24_000_000,
      // Trước ngày bật chấm điểm thì cột lead không so sánh được — phải nói ra, không lặng lẽ vẽ
      scoringEnabled: i >= 4,
    }
  }),
)

// ── SCR052 chủ đề hội thoại ───────────────────────────────────────────────────

const CHU_DE = [
  'Chính sách bảo hành',
  'Tra cứu đơn hàng',
  'Giá và khuyến mãi',
  'Hướng dẫn sử dụng',
  'Giao hàng và phí ship',
  'Đổi trả sản phẩm',
  'Tồn kho và đặt hàng sỉ',
  'Xuất hoá đơn VAT',
]

export const thongKeChuDe: ThongKeChuDe[] = daySoNgay(7, NGAY_MOC).flatMap((ngay, i) =>
  CHU_DE.map((ten, k) => {
    const soHT = 40 - k * 4 + ((i * 3) % 9)
    // Chủ đề "Xuất hoá đơn VAT" có tỉ lệ từ chối cao — đúng loại tín hiệu SCR052 tồn tại để lộ ra
    const tuChoi = k === 7 ? Math.round(soHT * 0.34) : Math.round(soHT * 0.06)
    return {
      statDate: ngay,
      clusterId: `cl-${k}`,
      topicLabel: ten,
      conversationCount: soHT,
      botResolvedCount: soHT - tuChoi - 2,
      refusalCount: tuChoi,
    }
  }),
)

// ── SCR053 tệp báo cáo ────────────────────────────────────────────────────────

export const danhSachTepBaoCao: TepBaoCao[] = [
  {
    id: 'bc-001',
    reportType: 'OVERVIEW',
    format: 'XLSX',
    status: 'READY',
    rowCount: 21,
    partIndex: null,
    partTotal: null,
    fileUri: '/exports/tong-quan-2026-08.xlsx',
    fileSizeBytes: 48_213,
    containsPersonalData: false,
    expiresAt: gio('2026-08-28'),
    requestedByName: 'Phạm Hoài An',
    requestedAt: gio('2026-08-21', '08:40'),
    completedAt: gio('2026-08-21', '08:41'),
    errorMessage: null,
  },
  {
    id: 'bc-002',
    reportType: 'AUDIT_LOG',
    format: 'CSV',
    status: 'READY',
    rowCount: 1_284,
    partIndex: 1,
    partTotal: 2,
    fileUri: '/exports/kiem-toan-2026-08-p1.csv',
    fileSizeBytes: 2_104_882,
    // Có dữ liệu cá nhân → phải hiện cảnh báo và có hạn tự xoá (Nghị định 13)
    containsPersonalData: true,
    expiresAt: gio('2026-08-24'),
    requestedByName: 'Phạm Hoài An',
    requestedAt: gio('2026-08-20', '17:05'),
    completedAt: gio('2026-08-20', '17:12'),
    errorMessage: null,
  },
  {
    id: 'bc-003',
    reportType: 'FUNNEL',
    format: 'CSV',
    status: 'RUNNING',
    rowCount: null,
    partIndex: null,
    partTotal: null,
    fileUri: null,
    fileSizeBytes: null,
    containsPersonalData: false,
    expiresAt: null,
    requestedByName: 'Võ Thị Kim Ngân',
    requestedAt: gio('2026-08-21', '10:58'),
    completedAt: null,
    errorMessage: null,
  },
  {
    id: 'bc-004',
    reportType: 'AI_PERFORMANCE',
    format: 'PDF',
    status: 'FAILED',
    rowCount: null,
    partIndex: null,
    partTotal: null,
    fileUri: null,
    fileSizeBytes: null,
    containsPersonalData: false,
    expiresAt: null,
    requestedByName: 'Lê Minh Tuấn',
    requestedAt: gio('2026-08-19', '14:22'),
    completedAt: null,
    errorMessage: 'Khoảng thời gian vượt 90 ngày — vượt giới hạn của bản kết xuất PDF.',
  },
  {
    id: 'bc-005',
    reportType: 'TOPICS',
    format: 'CSV',
    status: 'EXPIRED',
    rowCount: 56,
    partIndex: null,
    partTotal: null,
    fileUri: null,
    fileSizeBytes: 12_004,
    containsPersonalData: false,
    expiresAt: gio('2026-08-15'),
    requestedByName: 'Phạm Hoài An',
    requestedAt: gio('2026-08-08', '09:30'),
    completedAt: gio('2026-08-08', '09:31'),
    errorMessage: null,
  },
]
