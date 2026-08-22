import type { CauHinhWidget, Kenh } from '@/types/schema'

/**
 * Dữ liệu giả cho SCR016–SCR018. Enum lấy đúng CHECK của ERD.
 *
 * Không có bản ghi `WEB_WIDGET` nào ở đây: giao ước ghi rõ `channels.channel_type` chỉ nhận
 * `ZALO` và `FACEBOOK`, còn widget có bảng cấu hình riêng (`CauHinhWidget`). Hai thứ trông
 * giống nhau trên giao diện nhưng khác nhau về bản chất — widget không có token cần gia hạn,
 * không có cửa sổ gửi tin, và không thể "hết hạn".
 */

const gio = (s: string) => `${s}+07:00`

export const danhSachKenh: Kenh[] = [
  {
    id: 'k-0002',
    channelType: 'ZALO',
    externalAccountId: '3358274190028471',
    accountName: 'Cát Tường Official',
    status: 'ACTIVE',
    // Token Zalo OA hết hạn theo chu kỳ — màn hình phải nói trước, không đợi tới lúc gãy
    tokenExpiresAt: gio('2026-09-04T00:00:00'),
    verifiedAt: gio('2026-05-19T15:41:00'),
    lastError: null,
    // Zalo chỉ cho nhắn lại trong 48 giờ kể từ tin cuối của khách
    sendWindowHours: 48,
    rateLimitPerMinute: 20,
    conversationCount: 1637,
    disconnectedAt: null,
    createdAt: gio('2026-05-19T15:30:00'),
  },
  {
    id: 'k-0003',
    channelType: 'FACEBOOK',
    externalAccountId: '102938475610293',
    accountName: 'Cát Tường Home',
    status: 'ERROR',
    tokenExpiresAt: gio('2026-08-14T00:00:00'),
    verifiedAt: gio('2026-06-01T09:12:00'),
    lastError: 'Mã truy cập Trang đã hết hạn (OAuthException 190). Cần cấp lại quyền.',
    sendWindowHours: 24,
    rateLimitPerMinute: 30,
    conversationCount: 412,
    disconnectedAt: null,
    createdAt: gio('2026-06-01T09:05:00'),
  },
  {
    id: 'k-0004',
    channelType: 'ZALO',
    externalAccountId: '3358274190099999',
    accountName: 'Cát Tường Miền Nam',
    status: 'PENDING_VERIFY',
    tokenExpiresAt: null,
    verifiedAt: null,
    lastError: null,
    sendWindowHours: 48,
    rateLimitPerMinute: 20,
    conversationCount: 0,
    disconnectedAt: null,
    createdAt: gio('2026-08-20T16:48:00'),
  },
]

export const cauHinhWidget: CauHinhWidget = {
  publicKey: 'pk_live_cattuong_9f2c41b7',
  primaryColor: '#2a78d6',
  position: 'BOTTOM_RIGHT',
  greetingMessage: 'Chào bạn! Cát Tường có thể giúp gì cho bạn hôm nay?',
  avatarUrl: null,
  // Danh sách tên miền cho phép là biện pháp chống nhúng khoá công khai lên site khác
  allowedDomains: ['cattuong.vn', 'www.cattuong.vn', 'shop.cattuong.vn'],
  isActive: true,
}
