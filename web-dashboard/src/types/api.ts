import type { Schemas } from '@/types/schema'

/**
 * Vỏ phản hồi chung của java-core, đã gắn kiểu cho `data`.
 *
 * Bản sinh từ OpenAPI để `data: unknown` — đúng với đặc tả (một schema, nhiều kiểu dữ liệu) nhưng
 * không dùng trực tiếp được. Ở đây thay `data` bằng tham số kiểu.
 */
export type ApiResponse<T> = Omit<Schemas['ApiResponse'], 'data'> & { data: T }

/** Vỏ phân trang dùng chung cho mọi endpoint danh sách. */
export type Page<T> = Omit<Schemas['Page'], 'items'> & { items: T[] }

/** Phân trang bằng con trỏ — chỉ dùng cho tin nhắn của một hội thoại. */
export type CursorPage<T> = Omit<Schemas['CursorPage'], 'items'> & { items: T[] }

/**
 * Lỗi đã bóc vỏ, do `axiosClient` ném ra.
 *
 * Không sinh được từ OpenAPI vì đây là một lớp có mặt lúc chạy, không phải hình dạng dữ liệu.
 * Giữ `traceId` để màn hình lỗi hiện được mã theo dõi cho người dùng gửi quản trị viên.
 */
export class ApiError extends Error {
  readonly status: number
  readonly traceId: string | null

  constructor(message: string, status: number, traceId: string | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.traceId = traceId
  }
}
