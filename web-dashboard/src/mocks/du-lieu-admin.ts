/**
 * Dữ liệu mẫu cho Cổng Quản trị Nền tảng (Platform Admin Portal).
 *
 * Tuân thủ 100% lược đồ CSDL thật:
 * - `platform.tenants` (V101): trạng thái TRIAL/ACTIVE/SUSPENDED/EXPIRED, suspended_reason
 * - `platform.subscription_plans` (V102): gói TRIAL/STARTER/GROWTH/PRO
 * - `ai.ai_interactions`: thống kê token
 */

// ── Kiểu dữ liệu ────────────────────────────────────────────────────────────

export type TrangThaiDoanhNghiepAdmin =
  | 'TRIAL'
  | 'ACTIVE'
  | 'SUSPENDED'
  | 'EXPIRED'

export interface DoanhNghiepAdmin {
  id: string
  companyName: string
  slug: string
  contactEmail: string
  phone: string | null
  industry: string | null
  planCode: string
  planName: string
  status: TrangThaiDoanhNghiepAdmin
  suspendedReason: string | null
  userCount: number
  conversationCount: number
  tokenUsed: number
  documentCount: number
  createdAt: string
  trialEndsAt: string | null
}

export interface GoiDichVuAdmin {
  code: string
  name: string
  monthlyPriceVnd: number
  maxUsers: number
  maxConversationsPerMonth: number
  maxTokensPerMonth: number
  maxDocuments: number
  maxChannels: number
  tenantCount: number
  description: string
}

export interface TaiNguyenAiTenant {
  tenantId: string
  companyName: string
  tokensUsed: number
  tokensLimit: number
  costUsd: number
  avgLatencyMs: number
  interactionCount: number
}

export interface ThongKeNenTang {
  tongDoanhNghiep: number
  doanhNghiepHoatDong: number
  doanhNghiepDungThu: number
  doanhNghiepBiKhoa: number
  doanhNghiepHetHan: number
  mrrVnd: number
  tongHoiThoaiThang: number
  tongTokenAiThang: number
  phanBoTheoGoi: { goi: string; soLuong: number }[]
  tangTruongThang: { thang: string; soDoanhNghiep: number; mrr: number }[]
}

export interface DuLieuPhanTichNenTang {
  kpis: {
    mrrVnd: number
    mrrTangTruongPhanTram: number
    arrVnd: number
    tongDoanhNghiep: number
    doanhNghiepMoiThang: number
    tiLeChuyenDoiDungThu: number
    tiLeRoiBo: number
    tongTokensAi: number
    chiPhiAiUsd: number
    bienLoiNhuanGop: number
    tiLeAiTuXuLy: number
    tiLeNhanVienTiepNhan: number
    tongHoiThoai: number
    doTreTrungBinhMs: number
  }
  tangTruongDoanhThuVaTenant: {
    thang: string
    mrr: number
    chiPhiAiCost: number
    soTenant: number
    tenantMoi: number
  }[]
  tieuThuTokenTheoNgay: {
    ngay: string
    promptTokens: number
    completionTokens: number
    tongTokens: number
    chiPhiUsd: number
  }[]
  phanBoKenh: {
    kenh: string
    soLuong: number
    phanTram: number
    color: string
  }[]
  tiLeXuLyAi: {
    name: string
    value: number
    fill: string
  }[]
  phanBoMoHinhAi: {
    moHinh: string
    nhaCungCap: string
    soLuotGoi: number
    tokens: number
    chiPhiUsd: number
    phanTram: number
  }[]
  topTenantSuDung: {
    tenantId: string
    companyName: string
    planCode: string
    planName: string
    doanhThuThangVnd: number
    tokensUsed: number
    tokensLimit: number
    chiPhiAiVnd: number
    bienLoiNhuanPhanTram: number
    tiLeAiXuLy: number
  }[]
}

// ── Dữ liệu mẫu: 8 doanh nghiệp Việt Nam ──────────────────────────────────

export const DOANH_NGHIEP_MAU: DoanhNghiepAdmin[] = [
  {
    id: 'dn-001',
    companyName: 'Công ty TNHH Cát Tường',
    slug: 'cong-ty-tnhh-cat-tuong',
    contactEmail: 'an.pham@cattuong.vn',
    phone: '028 3822 1234',
    industry: 'Bất động sản',
    planCode: 'GROWTH',
    planName: 'Growth',
    status: 'ACTIVE',
    suspendedReason: null,
    userCount: 12,
    conversationCount: 3450,
    tokenUsed: 1_250_000,
    documentCount: 45,
    createdAt: '2025-06-15T08:00:00Z',
    trialEndsAt: null,
  },
  {
    id: 'dn-002',
    companyName: 'CTCP Công nghệ Sao Việt',
    slug: 'ctcp-cong-nghe-sao-viet',
    contactEmail: 'info@saoviet.tech',
    phone: '024 3999 8877',
    industry: 'Công nghệ thông tin',
    planCode: 'PRO',
    planName: 'Pro',
    status: 'ACTIVE',
    suspendedReason: null,
    userCount: 35,
    conversationCount: 8920,
    tokenUsed: 4_800_000,
    documentCount: 120,
    createdAt: '2025-03-10T09:30:00Z',
    trialEndsAt: null,
  },
  {
    id: 'dn-003',
    companyName: 'Trung tâm Anh ngữ Phương Đông',
    slug: 'trung-tam-anh-ngu-phuong-dong',
    contactEmail: 'contact@phuongdong.edu.vn',
    phone: '0236 3888 999',
    industry: 'Giáo dục',
    planCode: 'STARTER',
    planName: 'Starter',
    status: 'ACTIVE',
    suspendedReason: null,
    userCount: 5,
    conversationCount: 1280,
    tokenUsed: 380_000,
    documentCount: 18,
    createdAt: '2025-08-20T14:00:00Z',
    trialEndsAt: null,
  },
  {
    id: 'dn-004',
    companyName: 'Công ty Cổ phần Thương mại Hải Đăng',
    slug: 'cong-ty-co-phan-thuong-mai-hai-dang',
    contactEmail: 'lien.he@haidang.com.vn',
    phone: '0258 3777 456',
    industry: 'Thương mại điện tử',
    planCode: 'GROWTH',
    planName: 'Growth',
    status: 'SUSPENDED',
    suspendedReason: 'Vi phạm điều khoản sử dụng: gửi nội dung spam qua chatbot.',
    userCount: 8,
    conversationCount: 2100,
    tokenUsed: 890_000,
    documentCount: 30,
    createdAt: '2025-05-01T10:00:00Z',
    trialEndsAt: null,
  },
  {
    id: 'dn-005',
    companyName: 'Phòng khám Đa khoa An Khang',
    slug: 'phong-kham-da-khoa-an-khang',
    contactEmail: 'admin@ankhang.clinic',
    phone: '028 3666 7890',
    industry: 'Y tế',
    planCode: 'TRIAL',
    planName: 'Dùng thử',
    status: 'TRIAL',
    suspendedReason: null,
    userCount: 3,
    conversationCount: 245,
    tokenUsed: 52_000,
    documentCount: 8,
    createdAt: '2026-09-01T07:00:00Z',
    trialEndsAt: '2026-09-30T23:59:59Z',
  },
  {
    id: 'dn-006',
    companyName: 'Nhà hàng Bếp Lửa Sài Gòn',
    slug: 'nha-hang-bep-lua-sai-gon',
    contactEmail: 'quanly@bepluasg.vn',
    phone: '028 3555 1234',
    industry: 'F&B',
    planCode: 'STARTER',
    planName: 'Starter',
    status: 'EXPIRED',
    suspendedReason: null,
    userCount: 4,
    conversationCount: 780,
    tokenUsed: 190_000,
    documentCount: 12,
    createdAt: '2025-01-15T08:30:00Z',
    trialEndsAt: null,
  },
  {
    id: 'dn-007',
    companyName: 'CTCP Du lịch Vạn Hoa',
    slug: 'ctcp-du-lich-van-hoa',
    contactEmail: 'booking@vanhoa.travel',
    phone: '0511 3444 567',
    industry: 'Du lịch & Khách sạn',
    planCode: 'TRIAL',
    planName: 'Dùng thử',
    status: 'TRIAL',
    suspendedReason: null,
    userCount: 2,
    conversationCount: 89,
    tokenUsed: 18_000,
    documentCount: 3,
    createdAt: '2026-09-10T11:00:00Z',
    trialEndsAt: '2026-10-10T23:59:59Z',
  },
  {
    id: 'dn-008',
    companyName: 'Công ty TNHH Vận tải Bình Minh',
    slug: 'cong-ty-tnhh-van-tai-binh-minh',
    contactEmail: 'vanphong@binhminh.logistics',
    phone: '0292 3888 456',
    industry: 'Logistics',
    planCode: 'PRO',
    planName: 'Pro',
    status: 'ACTIVE',
    suspendedReason: null,
    userCount: 20,
    conversationCount: 5600,
    tokenUsed: 3_200_000,
    documentCount: 85,
    createdAt: '2025-04-22T09:00:00Z',
    trialEndsAt: null,
  },
]

// ── Dữ liệu mẫu: gói dịch vụ ───────────────────────────────────────────────

export const GOI_DICH_VU_MAU: GoiDichVuAdmin[] = [
  {
    code: 'TRIAL',
    name: 'Dùng thử',
    monthlyPriceVnd: 0,
    maxUsers: 3,
    maxConversationsPerMonth: 500,
    maxTokensPerMonth: 100_000,
    maxDocuments: 10,
    maxChannels: 1,
    tenantCount: 2,
    description: 'Miễn phí 14 ngày, trải nghiệm đầy đủ tính năng cơ bản.',
  },
  {
    code: 'STARTER',
    name: 'Starter',
    monthlyPriceVnd: 990_000,
    maxUsers: 5,
    maxConversationsPerMonth: 2_000,
    maxTokensPerMonth: 500_000,
    maxDocuments: 20,
    maxChannels: 2,
    tenantCount: 2,
    description: 'Dành cho doanh nghiệp nhỏ bắt đầu tự động hoá chăm sóc khách hàng.',
  },
  {
    code: 'GROWTH',
    name: 'Growth',
    monthlyPriceVnd: 2_990_000,
    maxUsers: 15,
    maxConversationsPerMonth: 5_000,
    maxTokensPerMonth: 2_000_000,
    maxDocuments: 50,
    maxChannels: 5,
    tenantCount: 2,
    description: 'Mở rộng quy mô với AI chatbot thông minh, đa kênh.',
  },
  {
    code: 'PRO',
    name: 'Pro',
    monthlyPriceVnd: 7_990_000,
    maxUsers: 50,
    maxConversationsPerMonth: 20_000,
    maxTokensPerMonth: 10_000_000,
    maxDocuments: 200,
    maxChannels: 10,
    tenantCount: 2,
    description: 'Toàn quyền kiểm soát, MCP server, công cụ tuỳ chỉnh, SLA ưu tiên.',
  },
]

// ── Thống kê nền tảng ────────────────────────────────────────────────────────

export const THONG_KE_NEN_TANG: ThongKeNenTang = {
  tongDoanhNghiep: 8,
  doanhNghiepHoatDong: 4,
  doanhNghiepDungThu: 2,
  doanhNghiepBiKhoa: 1,
  doanhNghiepHetHan: 1,
  mrrVnd: 22_950_000, // 2×Starter + 2×Growth + 2×Pro
  tongHoiThoaiThang: 22_464,
  tongTokenAiThang: 10_780_000,
  phanBoTheoGoi: [
    { goi: 'Dùng thử', soLuong: 2 },
    { goi: 'Starter', soLuong: 2 },
    { goi: 'Growth', soLuong: 2 },
    { goi: 'Pro', soLuong: 2 },
  ],
  tangTruongThang: [
    { thang: '04/2026', soDoanhNghiep: 4, mrr: 11_960_000 },
    { thang: '05/2026', soDoanhNghiep: 5, mrr: 14_950_000 },
    { thang: '06/2026', soDoanhNghiep: 6, mrr: 17_940_000 },
    { thang: '07/2026', soDoanhNghiep: 7, mrr: 20_930_000 },
    { thang: '08/2026', soDoanhNghiep: 7, mrr: 20_930_000 },
    { thang: '09/2026', soDoanhNghiep: 8, mrr: 22_950_000 },
  ],
}

// ── Tài nguyên AI theo doanh nghiệp ─────────────────────────────────────────

export const TAI_NGUYEN_AI_MAU: TaiNguyenAiTenant[] = DOANH_NGHIEP_MAU.filter(
  (dn) => dn.status !== 'EXPIRED',
).map((dn) => ({
  tenantId: dn.id,
  companyName: dn.companyName,
  tokensUsed: dn.tokenUsed,
  tokensLimit:
    GOI_DICH_VU_MAU.find((g) => g.code === dn.planCode)?.maxTokensPerMonth ?? 0,
  costUsd: Math.round((dn.tokenUsed / 1000) * 0.003 * 100) / 100, // ~$0.003/1K token
  avgLatencyMs: Math.round(150 + Math.random() * 200),
  interactionCount: dn.conversationCount,
}))

// ── Dữ liệu phân tích chuyên sâu nền tảng ──────────────────────────────────

export const PHAN_TICH_NEN_TANG_MAU: DuLieuPhanTichNenTang = {
  kpis: {
    mrrVnd: 22_950_000,
    mrrTangTruongPhanTram: 14.2,
    arrVnd: 275_400_000,
    tongDoanhNghiep: 8,
    doanhNghiepMoiThang: 1,
    tiLeChuyenDoiDungThu: 66.7,
    tiLeRoiBo: 2.1,
    tongTokensAi: 10_780_000,
    chiPhiAiUsd: 32.34,
    bienLoiNhuanGop: 96.5,
    tiLeAiTuXuLy: 78.4,
    tiLeNhanVienTiepNhan: 21.6,
    tongHoiThoai: 22_464,
    doTreTrungBinhMs: 245,
  },
  tangTruongDoanhThuVaTenant: [
    { thang: 'T04/2026', mrr: 11_960_000, chiPhiAiCost: 420_000, soTenant: 4, tenantMoi: 2 },
    { thang: 'T05/2026', mrr: 14_950_000, chiPhiAiCost: 510_000, soTenant: 5, tenantMoi: 1 },
    { thang: 'T06/2026', mrr: 17_940_000, chiPhiAiCost: 630_000, soTenant: 6, tenantMoi: 1 },
    { thang: 'T07/2026', mrr: 20_930_000, chiPhiAiCost: 710_000, soTenant: 7, tenantMoi: 1 },
    { thang: 'T08/2026', mrr: 20_930_000, chiPhiAiCost: 740_000, soTenant: 7, tenantMoi: 0 },
    { thang: 'T09/2026', mrr: 22_950_000, chiPhiAiCost: 810_000, soTenant: 8, tenantMoi: 1 },
  ],
  tieuThuTokenTheoNgay: [
    { ngay: '14/09', promptTokens: 240_000, completionTokens: 110_000, tongTokens: 350_000, chiPhiUsd: 1.05 },
    { ngay: '15/09', promptTokens: 310_000, completionTokens: 140_000, tongTokens: 450_000, chiPhiUsd: 1.35 },
    { ngay: '16/09', promptTokens: 390_000, completionTokens: 180_000, tongTokens: 570_000, chiPhiUsd: 1.71 },
    { ngay: '17/09', promptTokens: 420_000, completionTokens: 195_000, tongTokens: 615_000, chiPhiUsd: 1.84 },
    { ngay: '18/09', promptTokens: 380_000, completionTokens: 170_000, tongTokens: 550_000, chiPhiUsd: 1.65 },
    { ngay: '19/09', promptTokens: 490_000, completionTokens: 230_000, tongTokens: 720_000, chiPhiUsd: 2.16 },
    { ngay: '20/09', promptTokens: 510_000, completionTokens: 250_000, tongTokens: 760_000, chiPhiUsd: 2.28 },
  ],
  phanBoKenh: [
    { kenh: 'Live Chat Website', soLuong: 11_230, phanTram: 50.0, color: '#6366f1' },
    { kenh: 'Facebook Messenger', soLuong: 6_290, phanTram: 28.0, color: '#3b82f6' },
    { kenh: 'Zalo OA', soLuong: 3_820, phanTram: 17.0, color: '#06b6d4' },
    { kenh: 'Telegram / Khác', soLuong: 1_124, phanTram: 5.0, color: '#a855f7' },
  ],
  tiLeXuLyAi: [
    { name: 'AI tự giải quyết 100%', value: 78.4, fill: '#10b981' },
    { name: 'Chuyển nhân viên tiếp quản', value: 21.6, fill: '#f59e0b' },
  ],
  phanBoMoHinhAi: [
    { moHinh: 'GPT-4o-mini', nhaCungCap: 'OpenAI', soLuotGoi: 15_420, tokens: 6_200_000, chiPhiUsd: 9.30, phanTram: 57.5 },
    { moHinh: 'Gemini 1.5 Flash', nhaCungCap: 'Google', soLuotGoi: 6_800, tokens: 2_800_000, chiPhiUsd: 3.50, phanTram: 26.0 },
    { moHinh: 'GPT-4o (Reasoning)', nhaCungCap: 'OpenAI', soLuotGoi: 1_240, tokens: 1_200_000, chiPhiUsd: 12.00, phanTram: 11.1 },
    { moHinh: 'Claude 3.5 Sonnet', nhaCungCap: 'Anthropic', soLuotGoi: 480, tokens: 580_000, chiPhiUsd: 7.54, phanTram: 5.4 },
  ],
  topTenantSuDung: [
    {
      tenantId: 'dn-002',
      companyName: 'CTCP Công nghệ Sao Việt',
      planCode: 'PRO',
      planName: 'Pro',
      doanhThuThangVnd: 7_990_000,
      tokensUsed: 4_800_000,
      tokensLimit: 10_000_000,
      chiPhiAiVnd: 360_000,
      bienLoiNhuanPhanTram: 95.5,
      tiLeAiXuLy: 84.2,
    },
    {
      tenantId: 'dn-008',
      companyName: 'Công ty TNHH Vận tải Bình Minh',
      planCode: 'PRO',
      planName: 'Pro',
      doanhThuThangVnd: 7_990_000,
      tokensUsed: 3_200_000,
      tokensLimit: 10_000_000,
      chiPhiAiVnd: 240_000,
      bienLoiNhuanPhanTram: 97.0,
      tiLeAiXuLy: 79.5,
    },
    {
      tenantId: 'dn-001',
      companyName: 'Công ty TNHH Cát Tường',
      planCode: 'GROWTH',
      planName: 'Growth',
      doanhThuThangVnd: 2_990_000,
      tokensUsed: 1_250_000,
      tokensLimit: 2_000_000,
      chiPhiAiVnd: 94_000,
      bienLoiNhuanPhanTram: 96.8,
      tiLeAiXuLy: 76.1,
    },
    {
      tenantId: 'dn-004',
      companyName: 'CTCP Thương mại Hải Đăng',
      planCode: 'GROWTH',
      planName: 'Growth',
      doanhThuThangVnd: 2_990_000,
      tokensUsed: 890_000,
      tokensLimit: 2_000_000,
      chiPhiAiVnd: 67_000,
      bienLoiNhuanPhanTram: 97.8,
      tiLeAiXuLy: 71.0,
    },
    {
      tenantId: 'dn-003',
      companyName: 'Trung tâm Anh ngữ Phương Đông',
      planCode: 'STARTER',
      planName: 'Starter',
      doanhThuThangVnd: 990_000,
      tokensUsed: 380_000,
      tokensLimit: 500_000,
      chiPhiAiVnd: 28_500,
      bienLoiNhuanPhanTram: 97.1,
      tiLeAiXuLy: 82.0,
    },
  ],
}
