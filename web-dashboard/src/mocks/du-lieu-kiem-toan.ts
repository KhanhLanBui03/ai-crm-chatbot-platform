import { danhSachKhachHang } from '@/mocks/du-lieu-khach-hang'
import type { BanGhiKiemToan, MucXoa, YeuCauXoaChiTiet } from '@/types/schema'

/**
 * Dữ liệu giả cho nhóm Kiểm toán — SCR054–SCR058. Nghị định 13/2023/NĐ-CP.
 *
 * Hai chỗ dựng có chủ đích:
 *
 * 1. **Bản ghi có dữ liệu cá nhân đều ở trạng thái đã che** (`masked: true`). Xem đầy đủ phải gọi
 *    `/reveal` kèm lý do, và chính lần xem đó lại sinh ra một dòng nhật ký mới. Nếu mock trả sẵn
 *    `before`/`after` đầy đủ thì cả cơ chế này biến mất khỏi màn hình.
 * 2. **Một yêu cầu xoá ở trạng thái `PARTIALLY_FAILED`.** Đây là tình huống mà bảng tiến độ theo
 *    từng bảng của SCR057 sinh ra để xử lý: xoá xong một nửa rồi hỏng thì phải biết chính xác chỗ
 *    nào đã xong mới chạy lại được phần dở dang.
 */

const gio = (s: string) => `${s}+07:00`

const kh = (i: number) => danhSachKhachHang[i]

export const danhSachKiemToan: BanGhiKiemToan[] = [
  {
    id: 41_208,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000001',
    actorEmail: 'an.pham@cattuong.vn',
    action: 'ERASURE_EXECUTED',
    entityType: 'contact',
    entityId: kh(21).id,
    before: { fullName: '***', phone: '***', email: '***' },
    after: { fullName: 'Khách đã ẩn danh', phone: null, email: null },
    reason: 'Khách yêu cầu xoá dữ liệu theo Điều 16 Nghị định 13/2023/NĐ-CP.',
    severity: 'CRITICAL',
    containsPersonalData: true,
    masked: true,
    ipAddress: '113.161.42.18',
    traceId: 'c0ffee12-3456-4789-abcd-0123456789ab',
    occurredAt: gio('2026-08-21T15:42:10'),
  },
  {
    id: 41_207,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000002',
    actorEmail: 'vy.ngo@cattuong.vn',
    action: 'ROLE_CHANGED',
    entityType: 'user',
    entityId: 'u1000000-0000-4000-8000-000000000004',
    before: { roleCode: 'AGENT' },
    after: { roleCode: 'SUPERVISOR' },
    reason: null,
    severity: 'WARNING',
    containsPersonalData: false,
    masked: false,
    ipAddress: '113.161.42.19',
    traceId: '11112222-3333-4444-5555-666677778888',
    occurredAt: gio('2026-08-21T10:18:44'),
  },
  {
    id: 41_206,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000001',
    actorEmail: 'an.pham@cattuong.vn',
    action: 'CONTACT_MERGED',
    entityType: 'contact',
    entityId: kh(0).id,
    before: { mergedFrom: '***', phone: '***' },
    after: { survivingContact: '***' },
    reason: 'Hai hồ sơ cùng số điện thoại sau khi khách nhắn từ Zalo.',
    severity: 'WARNING',
    containsPersonalData: true,
    masked: true,
    ipAddress: '113.161.42.18',
    traceId: '22223333-4444-5555-6666-777788889999',
    occurredAt: gio('2026-08-20T16:05:12'),
  },
  {
    id: 41_205,
    actorType: 'AI_AGENT',
    actorId: null,
    actorEmail: null,
    action: 'TOOL_CALL_BLOCKED',
    entityType: 'tool_call_log',
    entityId: null,
    before: null,
    after: { toolName: 'tra_cuu_don_hang', blockedReason: 'CROSS_TENANT_IDENTIFIER' },
    reason: 'Định danh đơn hàng không thuộc doanh nghiệp hiện tại.',
    severity: 'CRITICAL',
    containsPersonalData: false,
    masked: false,
    ipAddress: null,
    traceId: '33334444-5555-6666-7777-888899990000',
    occurredAt: gio('2026-08-22T08:33:51'),
  },
  {
    id: 41_204,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000003',
    actorEmail: 'tuan.le@cattuong.vn',
    action: 'LOGIN_FAILED',
    entityType: 'user',
    entityId: 'u1000000-0000-4000-8000-000000000003',
    before: null,
    after: { attempt: 4, lockedUntil: gio('2026-08-22T07:15:00') },
    reason: 'Sai mật khẩu bốn lần liên tiếp — khoá tạm thời 15 phút.',
    severity: 'WARNING',
    containsPersonalData: false,
    masked: false,
    ipAddress: '203.113.88.7',
    traceId: '44445555-6666-7777-8888-999900001111',
    occurredAt: gio('2026-08-22T07:00:22'),
  },
  {
    id: 41_203,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000001',
    actorEmail: 'an.pham@cattuong.vn',
    action: 'LOGIN_SUCCESS',
    entityType: 'user',
    entityId: 'u1000000-0000-4000-8000-000000000001',
    before: null,
    after: { userAgent: 'Chrome 151 trên macOS' },
    reason: null,
    severity: 'INFO',
    containsPersonalData: false,
    masked: false,
    ipAddress: '113.161.42.18',
    traceId: '55556666-7777-8888-9999-000011112222',
    occurredAt: gio('2026-08-22T06:41:03'),
  },
  {
    id: 41_202,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000002',
    actorEmail: 'vy.ngo@cattuong.vn',
    action: 'EXPORT_REQUESTED',
    entityType: 'report_file',
    entityId: null,
    before: null,
    after: { reportType: 'AUDIT_LOG', format: 'XLSX', containsPersonalData: true },
    reason: 'Chuẩn bị hồ sơ cho đợt rà soát nội bộ quý III.',
    severity: 'WARNING',
    containsPersonalData: true,
    masked: true,
    ipAddress: '113.161.42.19',
    traceId: '66667777-8888-9999-0000-111122223333',
    occurredAt: gio('2026-08-20T09:12:38'),
  },
  {
    id: 41_201,
    actorType: 'SYSTEM',
    actorId: null,
    actorEmail: null,
    action: 'RETENTION_PURGE',
    entityType: 'message',
    entityId: null,
    before: null,
    after: { purgedRows: 14_820, olderThan: '2024-08-20' },
    reason: 'Chính sách lưu trữ 24 tháng.',
    severity: 'INFO',
    containsPersonalData: false,
    masked: false,
    ipAddress: null,
    traceId: '77778888-9999-0000-1111-222233334444',
    occurredAt: gio('2026-08-20T02:00:00'),
  },
  {
    id: 41_200,
    actorType: 'PLATFORM_ADMIN',
    actorId: null,
    actorEmail: 'ops@crm-ai.vn',
    action: 'PLAN_CHANGED',
    entityType: 'subscription',
    entityId: null,
    before: { planCode: 'STARTER' },
    after: { planCode: 'GROWTH' },
    reason: 'Doanh nghiệp nâng gói theo yêu cầu qua kênh hỗ trợ.',
    severity: 'INFO',
    containsPersonalData: false,
    masked: false,
    ipAddress: '14.161.20.4',
    traceId: '88889999-0000-1111-2222-333344445555',
    occurredAt: gio('2026-08-18T11:27:19'),
  },
  {
    id: 41_199,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000001',
    actorEmail: 'an.pham@cattuong.vn',
    action: 'CONSENT_WITHDRAWN',
    entityType: 'contact',
    entityId: kh(4).id,
    before: { consentGranted: true },
    after: { consentGranted: false },
    reason: 'Khách rút đồng ý qua tổng đài.',
    severity: 'WARNING',
    containsPersonalData: true,
    masked: true,
    ipAddress: '113.161.42.18',
    traceId: '99990000-1111-2222-3333-444455556666',
    occurredAt: gio('2026-08-17T14:50:41'),
  },
  {
    id: 41_198,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000001',
    actorEmail: 'an.pham@cattuong.vn',
    action: 'MCP_SERVER_ADDED',
    entityType: 'mcp_server',
    entityId: null,
    before: null,
    after: { name: 'Kho vận Cát Tường', specVersion: '2025-06-18' },
    reason: null,
    severity: 'WARNING',
    containsPersonalData: false,
    masked: false,
    ipAddress: '113.161.42.18',
    traceId: 'aaaa0000-1111-2222-3333-444455556666',
    occurredAt: gio('2026-06-12T09:18:02'),
  },
  {
    id: 41_197,
    actorType: 'USER',
    actorId: 'u1000000-0000-4000-8000-000000000002',
    actorEmail: 'vy.ngo@cattuong.vn',
    action: 'DOCUMENT_DELETED',
    entityType: 'document',
    entityId: null,
    before: { title: 'Bảng giá bán lẻ tháng 06/2026' },
    after: null,
    reason: 'Đã có bản tháng 08 thay thế.',
    severity: 'INFO',
    containsPersonalData: false,
    masked: false,
    ipAddress: '113.161.42.19',
    traceId: 'bbbb0000-1111-2222-3333-444455556666',
    occurredAt: gio('2026-08-01T08:44:55'),
  },
]

/** Giá trị đầy đủ, chỉ trả về sau khi gọi `/reveal` kèm lý do. */
export const banGhiDayDu: Record<number, { before: unknown; after: unknown }> = {
  41_208: {
    before: {
      fullName: 'Nguyen Thi Bich Huong',
      phone: '0903118274',
      email: 'huong.ntb@gmail.com',
    },
    after: { fullName: 'Khách đã ẩn danh', phone: null, email: null },
  },
  41_206: {
    before: { mergedFrom: 'Nguyen Thi Bich Huong', phone: '0903118274' },
    after: { survivingContact: 'Nguyễn Thị Bích Hường' },
  },
  41_202: {
    before: null,
    after: {
      reportType: 'AUDIT_LOG',
      format: 'XLSX',
      containsPersonalData: true,
      rowCount: 41_208,
      requestedBy: 'vy.ngo@cattuong.vn',
    },
  },
  41_199: {
    before: { consentGranted: true, contactName: 'Đặng Thu Phương', phone: '0977301558' },
    after: { consentGranted: false, contactName: 'Đặng Thu Phương', phone: '0977301558' },
  },
}

// ── Yêu cầu xoá dữ liệu cá nhân ──────────────────────────────────────────────

/**
 * Phạm vi xoá theo từng bảng.
 *
 * Ba thao tác khác nhau chứ không phải một: `DELETE` xoá hẳn, `ANONYMIZE` giữ dòng nhưng bỏ phần
 * định danh, `KEEP_AGGREGATE` giữ nguyên vì đó là số liệu tổng hợp không còn quy về cá nhân được.
 * Xoá sạch cả ba là phá luôn báo cáo doanh thu của những kỳ đã chốt.
 */
function phamVi(daXong: boolean): MucXoa[] {
  const tt = daXong ? ('DONE' as const) : ('PENDING' as const)
  const luc = daXong ? gio('2026-08-21T15:42:08') : null
  return [
    { targetSchema: 'engagement', targetTable: 'messages', action: 'DELETE', status: tt, affectedRows: 148, errorMessage: null, executedAt: luc },
    { targetSchema: 'engagement', targetTable: 'conversations', action: 'ANONYMIZE', status: tt, affectedRows: 12, errorMessage: null, executedAt: luc },
    { targetSchema: 'engagement', targetTable: 'attachments', action: 'DELETE', status: tt, affectedRows: 6, errorMessage: null, executedAt: luc },
    { targetSchema: 'platform', targetTable: 'contacts', action: 'ANONYMIZE', status: tt, affectedRows: 1, errorMessage: null, executedAt: luc },
    { targetSchema: 'platform', targetTable: 'channel_identities', action: 'DELETE', status: tt, affectedRows: 2, errorMessage: null, executedAt: luc },
    { targetSchema: 'platform', targetTable: 'contact_notes', action: 'DELETE', status: tt, affectedRows: 4, errorMessage: null, executedAt: luc },
    { targetSchema: 'sales', targetTable: 'leads', action: 'ANONYMIZE', status: tt, affectedRows: 2, errorMessage: null, executedAt: luc },
    { targetSchema: 'sales', targetTable: 'deals', action: 'ANONYMIZE', status: tt, affectedRows: 1, errorMessage: null, executedAt: luc },
    { targetSchema: 'sales', targetTable: 'activities', action: 'DELETE', status: tt, affectedRows: 9, errorMessage: null, executedAt: luc },
    { targetSchema: 'analytics', targetTable: 'conversation_stats_daily', action: 'KEEP_AGGREGATE', status: tt, affectedRows: 0, errorMessage: null, executedAt: luc },
    { targetSchema: 'analytics', targetTable: 'revenue_monthly', action: 'KEEP_AGGREGATE', status: tt, affectedRows: 0, errorMessage: null, executedAt: luc },
    { targetSchema: 'ai', targetTable: 'ai_interactions', action: 'ANONYMIZE', status: tt, affectedRows: 34, errorMessage: null, executedAt: luc },
    { targetSchema: 'ai', targetTable: 'tool_call_logs', action: 'ANONYMIZE', status: tt, affectedRows: 7, errorMessage: null, executedAt: luc },
  ]
}

const GHI_CHU_NGOAI =
  'Dữ liệu đã gửi sang hệ thống kho vận qua công cụ MCP nằm ngoài phạm vi xoá này. Phải gửi yêu cầu xoá riêng cho đơn vị đó và lưu văn bản xác nhận vào hồ sơ.'

export const danhSachYeuCauXoa: YeuCauXoaChiTiet[] = [
  {
    id: 'yc-0001',
    contactId: kh(21).id,
    contactName: kh(21).fullName,
    legalBasis: 'Điều 16 Nghị định 13/2023/NĐ-CP — quyền xoá dữ liệu',
    status: 'COMPLETED',
    identityVerifiedByName: 'Phạm Hoài An',
    identityVerifiedAt: gio('2026-08-21T15:20:00'),
    requestedAt: gio('2026-08-20T09:40:00'),
    completedAt: gio('2026-08-21T15:42:10'),
    items: phamVi(true),
    externalSystemsNote: GHI_CHU_NGOAI,
    certificateUri: '/api/v1/erasure-requests/yc-0001/certificate.pdf',
    startedAt: gio('2026-08-21T15:41:52'),
  },
  {
    id: 'yc-0002',
    contactId: kh(4).id,
    contactName: kh(4).fullName,
    legalBasis: 'Điều 16 Nghị định 13/2023/NĐ-CP — khách rút đồng ý xử lý dữ liệu',
    status: 'PENDING',
    identityVerifiedByName: 'Ngô Thanh Vy',
    identityVerifiedAt: gio('2026-08-22T08:10:00'),
    requestedAt: gio('2026-08-22T07:55:00'),
    completedAt: null,
    items: phamVi(false),
    externalSystemsNote: GHI_CHU_NGOAI,
    certificateUri: null,
    startedAt: null,
  },
  {
    id: 'yc-0003',
    contactId: kh(11).id,
    contactName: kh(11).fullName,
    legalBasis: 'Điều 16 Nghị định 13/2023/NĐ-CP — quyền xoá dữ liệu',
    // Xoá hỏng giữa chừng: đây chính là tình huống bảng tiến độ theo từng bảng sinh ra để xử lý
    status: 'PARTIALLY_FAILED',
    identityVerifiedByName: 'Phạm Hoài An',
    identityVerifiedAt: gio('2026-08-19T10:05:00'),
    requestedAt: gio('2026-08-19T09:30:00'),
    completedAt: null,
    items: phamVi(true).map((m, i) =>
      i < 8
        ? m
        : {
            ...m,
            status: i === 8 ? ('FAILED' as const) : ('PENDING' as const),
            affectedRows: i === 8 ? 0 : null,
            errorMessage:
              i === 8
                ? 'Khoá ngoại từ sales.activities sang sales.deals chưa xoá xong — chạy lại sau khi bảng deals hoàn tất.'
                : null,
            executedAt: null,
          },
    ),
    externalSystemsNote: GHI_CHU_NGOAI,
    certificateUri: null,
    startedAt: gio('2026-08-19T10:12:40'),
  },
  {
    id: 'yc-0004',
    contactId: kh(16).id,
    contactName: kh(16).fullName,
    legalBasis: 'Điều 16 Nghị định 13/2023/NĐ-CP — quyền xoá dữ liệu',
    status: 'PENDING',
    identityVerifiedByName: 'Ngô Thanh Vy',
    identityVerifiedAt: gio('2026-08-22T09:02:00'),
    requestedAt: gio('2026-08-22T08:48:00'),
    completedAt: null,
    items: phamVi(false),
    externalSystemsNote: GHI_CHU_NGOAI,
    certificateUri: null,
    startedAt: null,
  },
]

/** Xem trước phạm vi cho một khách bất kỳ — chưa tạo yêu cầu nào, chưa xoá gì cả. */
export const xemTruocPhamVi = (): MucXoa[] => phamVi(false)
