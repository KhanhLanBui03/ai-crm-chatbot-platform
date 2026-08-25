import type {
  DiemSuDungNgay,
  DoanhNghiep,
  GoiDichVu,
  HanMucSuDung,
  NguoiDung,
  ThueBao,
  VaiTro,
} from '@/types/schema'
import { daySoNgay } from '@/mocks/tienIch'

/**
 * Dữ liệu giả cho miền nền tảng — SCR007–SCR015.
 *
 * Kiểu lấy từ `@/types/schema`, tức là từ `docs/openapi/dashboard-api.yaml`. Mọi giá trị enum
 * lấy đúng ràng buộc CHECK trong ERD; đừng bịa trạng thái không có trong `CHECK`.
 */

const U = (n: number) => `u1000000-0000-4000-8000-00000000000${n}`
const gio = (ngay: string, hhmm: string) => `${ngay}T${hhmm}:00+07:00`

// ── SCR008 người dùng ─────────────────────────────────────────────────────────

export const danhSachNguoiDung: NguoiDung[] = [
  {
    id: U(1),
    fullName: 'Phạm Hoài An',
    email: 'an.pham@cattuong.vn',
    roleCode: 'TENANT_ADMIN',
    roleName: 'Quản trị doanh nghiệp',
    status: 'ACTIVE',
    emailVerifiedAt: gio('2026-05-12', '09:20'),
    lastLoginAt: gio('2026-08-21', '08:02'),
    assignedConversationCount: 4,
    createdAt: gio('2026-05-12', '09:12'),
  },
  {
    id: U(2),
    fullName: 'Lê Minh Tuấn',
    email: 'tuan.le@cattuong.vn',
    roleCode: 'AGENT',
    roleName: 'Nhân viên chăm sóc',
    status: 'ACTIVE',
    emailVerifiedAt: gio('2026-05-14', '14:05'),
    lastLoginAt: gio('2026-08-21', '07:41'),
    assignedConversationCount: 11,
    createdAt: gio('2026-05-14', '13:58'),
  },
  {
    id: U(3),
    fullName: 'Võ Thị Kim Ngân',
    email: 'ngan.vo@cattuong.vn',
    roleCode: 'AGENT',
    roleName: 'Nhân viên chăm sóc',
    status: 'ACTIVE',
    emailVerifiedAt: gio('2026-06-02', '10:31'),
    lastLoginAt: gio('2026-08-20', '17:55'),
    assignedConversationCount: 9,
    createdAt: gio('2026-06-02', '10:22'),
  },
  {
    id: U(4),
    fullName: 'Trịnh Bảo Long',
    email: 'long.trinh@cattuong.vn',
    roleCode: 'AGENT',
    roleName: 'Nhân viên chăm sóc',
    status: 'ACTIVE',
    emailVerifiedAt: gio('2026-06-18', '08:47'),
    lastLoginAt: gio('2026-08-19', '16:12'),
    assignedConversationCount: 6,
    createdAt: gio('2026-06-18', '08:40'),
  },
  {
    id: U(5),
    fullName: null,
    email: 'huy.nguyen@cattuong.vn',
    roleCode: 'AGENT',
    roleName: 'Nhân viên chăm sóc',
    status: 'PENDING',
    // Chưa xác thực thư nên chưa có tên — đây là trạng thái thật sau khi mời, không phải dữ liệu thiếu
    emailVerifiedAt: null,
    lastLoginAt: null,
    assignedConversationCount: 0,
    createdAt: gio('2026-08-18', '11:03'),
  },
  {
    id: U(6),
    fullName: 'Đỗ Thanh Hằng',
    email: 'hang.do@cattuong.vn',
    roleCode: 'AGENT',
    roleName: 'Nhân viên chăm sóc',
    status: 'DISABLED',
    emailVerifiedAt: gio('2026-05-20', '09:15'),
    lastLoginAt: gio('2026-07-30', '18:22'),
    // Vô hiệu hoá mà vẫn còn hội thoại phụ trách — chính là thứ SCR008 phải cảnh báo
    assignedConversationCount: 3,
    createdAt: gio('2026-05-20', '09:08'),
  },
]

// ── SCR010 vai trò ────────────────────────────────────────────────────────────

/**
 * ERD chỉ có **hai** vai trò. Mô tả SCR010 nêu bốn (Admin/Manager/Agent/Sales) — chỗ lệch này đã
 * chốt theo ERD (ADR-0011): hiển thị theo `roles.permissions` chứ không theo bốn vai trò cứng.
 */
export const danhSachVaiTro: VaiTro[] = [
  {
    code: 'TENANT_ADMIN',
    name: 'Quản trị doanh nghiệp',
    description: 'Toàn quyền trên dữ liệu của doanh nghiệp, kể cả cấu hình và kiểm toán.',
    permissions: {
      conversations: 'FULL',
      contacts: 'FULL',
      knowledge: 'FULL',
      sales: 'FULL',
      analytics: 'FULL',
      settings: 'FULL',
      audit: 'FULL',
      billing: 'FULL',
    },
    userCount: 1,
  },
  {
    code: 'AGENT',
    name: 'Nhân viên chăm sóc',
    description: 'Xử lý hội thoại và khách hàng; không đụng tới cấu hình hay hoá đơn.',
    permissions: {
      conversations: 'READ_WRITE',
      contacts: 'READ_WRITE',
      knowledge: 'READ',
      sales: 'READ_WRITE',
      analytics: 'READ',
      settings: 'NONE',
      audit: 'NONE',
      billing: 'NONE',
    },
    userCount: 5,
  },
]

// ── SCR007 hồ sơ doanh nghiệp ─────────────────────────────────────────────────

export const hoSoDoanhNghiep: DoanhNghiep = {
  name: 'Công ty TNHH Cát Tường',
  slug: 'cat-tuong',
  industry: 'Bán lẻ thiết bị gia dụng',
  timezone: 'Asia/Ho_Chi_Minh',
  defaultLocale: 'vi-VN',
  businessHours: {
    mon: { open: '08:00', close: '17:30' },
    tue: { open: '08:00', close: '17:30' },
    wed: { open: '08:00', close: '17:30' },
    thu: { open: '08:00', close: '17:30' },
    fri: { open: '08:00', close: '17:30' },
    sat: { open: '08:00', close: '12:00' },
    sun: null,
  },
  aiTone: 'FRIENDLY',
  leadScoreThreshold: 70,
  autoLeadCreation: true,
  autoLeadDailyLimit: 50,
  assignmentMode: 'LEAST_BUSY',
  assignmentConfig: {},
  restrictAgentScope: false,
  refusalHandoffThreshold: 2,
  summaryTurnThreshold: 8,
  messageRetentionDays: 365,
  status: 'ACTIVE',
}

// ── SCR013 gói dịch vụ ────────────────────────────────────────────────────────

export const danhSachGoi: GoiDichVu[] = [
  {
    code: 'TRIAL',
    name: 'Dùng thử',
    monthlyPriceVnd: 0,
    conversationQuota: 200,
    tokenQuota: 500_000,
    maxUsers: 2,
    maxDocuments: 20,
    maxTags: 10,
    sortOrder: 0,
    isCurrent: false,
  },
  {
    code: 'STARTER',
    name: 'Khởi đầu',
    monthlyPriceVnd: 990_000,
    conversationQuota: 1_500,
    tokenQuota: 4_000_000,
    maxUsers: 5,
    maxDocuments: 100,
    maxTags: 30,
    sortOrder: 1,
    isCurrent: false,
  },
  {
    code: 'GROWTH',
    name: 'Tăng trưởng',
    monthlyPriceVnd: 2_490_000,
    conversationQuota: 6_000,
    tokenQuota: 18_000_000,
    maxUsers: 15,
    maxDocuments: 500,
    maxTags: 100,
    sortOrder: 2,
    isCurrent: true,
  },
  {
    code: 'PRO',
    name: 'Chuyên nghiệp',
    monthlyPriceVnd: 5_900_000,
    conversationQuota: 20_000,
    tokenQuota: 60_000_000,
    maxUsers: 50,
    maxDocuments: 2_000,
    maxTags: 300,
    sortOrder: 3,
    isCurrent: false,
  },
]

// ── SCR012 thuê bao ───────────────────────────────────────────────────────────

export const thueBaoHienTai: ThueBao = {
  status: 'ACTIVE',
  plan: danhSachGoi.find((g) => g.code === 'GROWTH')!,
  periodStart: '2026-08-01',
  periodEnd: '2026-08-31',
  scheduledPlan: null,
  scheduledEffectiveAt: null,
  readOnlyMode: false,
}

// ── SCR014 hạn mức ────────────────────────────────────────────────────────────

const mot = (used: number, quota: number) => ({
  used,
  quota,
  percent: Math.round((used / quota) * 1000) / 10,
})

export const hanMucHienTai: HanMucSuDung = {
  periodStart: '2026-08-01',
  periodEnd: '2026-08-31',
  conversations: mot(4_812, 6_000),
  // Token là ô chạm ngưỡng trước tiên — mô hình thu phí neo vào hội thoại nhưng token mới là
  // thứ tăng nhanh khi tài liệu dài
  tokens: mot(16_204_500, 18_000_000),
  users: mot(6, 15),
  documents: mot(87, 500),
  costVnd: 3_284_000,
  warnedAt: '2026-08-19T09:00:00+07:00',
  blockedAt: null,
}

// ── SCR015 mức sử dụng theo ngày ──────────────────────────────────────────────

const KENH = ['WEB_WIDGET', 'ZALO', 'FACEBOOK'] as const

/** 21 ngày × 3 kênh — đủ để phân trang và sắp xếp có ý nghĩa. */
export const mucSuDungTheoNgay: DiemSuDungNgay[] = daySoNgay(21, new Date('2026-08-21')).flatMap(
  (ngay, i) =>
    KENH.map((kenh, k) => {
      const nen = [92, 54, 31][k] + ((i * 7 + k * 3) % 17)
      const promptTokens = nen * 1_180 + ((i * 53) % 900)
      const completionTokens = Math.round(promptTokens * 0.36)
      return {
        statDate: ngay,
        channelType: kenh,
        route: (['RAG', 'TOOL_CALL', 'SMALL_TALK'] as const)[(i + k) % 3],
        conversations: nen,
        promptTokens,
        completionTokens,
        costVnd: Math.round((promptTokens + completionTokens) * 0.062),
        cachedHits: Math.round(nen * 0.18),
        modelVersion: 'gpt-oss-20b@v2026.07',
      }
    }),
)

