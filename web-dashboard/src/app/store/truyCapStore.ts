import type { AppStore } from '@/app/store'

let store: AppStore | undefined

/**
 * Trao store cho các module nằm ngoài React. Gọi đúng một lần, ngay sau `configureStore`.
 *
 * Đây là mẫu "inject the store" của tài liệu Redux, dùng thay cho việc `axiosClient` import thẳng
 * `@/app/store`: import thẳng sẽ tạo vòng phụ thuộc `store → apiSlice → baseQuery → axiosClient →
 * store`. Vòng đó ESM vẫn nuốt được vì interceptor chỉ chạy lúc runtime, nhưng nó là loại bug im
 * lặng chỉ lộ ra khi đổi thứ tự import — không đáng để lại trong mã.
 */
export function ganStore(s: AppStore) {
  store = s
}

/** `undefined` trước khi store dựng xong. Interceptor chỉ chạy sau đó nên trên thực tế không gặp. */
export function layStore(): AppStore | undefined {
  return store
}
