import type { HoiThoaiTomTat, LoaiNguoiGui, TinNhan } from '@/types/schema'

/**
 * Phong bì khung tin WebSocket — giao ước ở `docs/openapi/dashboard-realtime.md`.
 *
 * Đây là **ngoại lệ duy nhất** của quy tắc "không gõ tay kiểu API": OpenAPI 3.1 chỉ mô tả được
 * cặp request/response, không mô tả được luồng máy chủ đẩy xuống. Nhưng ngoại lệ chỉ áp cho
 * phong bì — phần thân (`message`, `conversation`) dùng thẳng type sinh từ YAML, nên đổi hình
 * dạng `TinNhan` vẫn nổ lỗi ở đây lúc `tsc`.
 */

// ── Khung client → server ───────────────────────────────────────────────────────

export type KhungGui =
  /** Khung đầu tiên. Không gửi trong 10 giây thì máy chủ đóng với mã 4408. */
  | { type: 'AUTH'; accessToken: string }
  | { type: 'SUBSCRIBE'; conversationId: string }
  | { type: 'UNSUBSCRIBE'; conversationId: string }
  | { type: 'PING' }

// ── Khung server → client ───────────────────────────────────────────────────────

/** Phần chung của mọi khung mang dữ liệu. `eventId` là khoá chống trùng khi nối lại. */
interface PhongBi {
  eventId: string
  occurredAt: string
}

export type KhungNhan =
  | { type: 'READY'; connectionId: string; serverTime: string }
  | { type: 'PONG'; serverTime: string }
  | (PhongBi & { type: 'MESSAGE_CREATED'; conversationId: string; message: TinNhan })
  | (PhongBi & { type: 'CONVERSATION_UPDATED'; conversation: HoiThoaiTomTat })
  | (PhongBi & {
      type: 'HANDOFF_REQUESTED'
      conversationId: string
      reason: string
      conversation: HoiThoaiTomTat
    })
  /** Phù du: không có `eventId`, không được ghi vào cache. */
  | { type: 'AGENT_TYPING'; conversationId: string; senderType: LoaiNguoiGui; expiresAt: string }
  | { type: 'ERROR'; code: string; message: string }

export type LoaiKhungNhan = KhungNhan['type']

/** Lấy đúng nhánh của union theo `type` — dùng cho tham số của hàm nghe. */
export type Khung<L extends LoaiKhungNhan> = Extract<KhungNhan, { type: L }>

// ── Mã đóng ────────────────────────────────────────────────────────────────────

export const MA_DONG = {
  /** Đóng có chủ ý: đăng xuất, rời trang. Không nối lại. */
  BINH_THUONG: 1000,
  /** Token hết hạn hoặc chưa xác thực — làm mới token rồi nối lại. */
  CHUA_XAC_THUC: 4401,
  /** Không đủ quyền với hội thoại vừa xin nhận. Không nối lại. */
  KHONG_DU_QUYEN: 4403,
  /** Quá 10 giây không gửi `AUTH`. */
  AUTH_QUA_HAN: 4408,
  /** Vượt số kết nối cho phép của tenant — lùi lâu hơn rồi thử lại. */
  QUA_NHIEU_KET_NOI: 4429,
} as const

/** Đóng với mã nào thì đừng nối lại nữa: nối lại cũng hỏng y như vậy. */
export function dungNoiLai(ma: number): boolean {
  return ma === MA_DONG.BINH_THUONG || ma === MA_DONG.KHONG_DU_QUYEN
}
