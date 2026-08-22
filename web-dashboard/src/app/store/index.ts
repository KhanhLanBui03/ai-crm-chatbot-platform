import { configureStore } from '@reduxjs/toolkit'
import { setupListeners } from '@reduxjs/toolkit/query'

import { apiSlice } from '@/api/apiSlice'
import { authReducer, luuPhienListener } from '@/app/store/authSlice'
import { realtimeReducer } from '@/app/store/realtimeSlice'
import { ganStore } from '@/app/store/truyCapStore'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    realtime: realtimeReducer,
    [apiSlice.reducerPath]: apiSlice.reducer,
  },
  middleware: (mac) =>
    // Thứ tự quan trọng: listener lưu phiên phải chạy TRƯỚC middleware của RTK Query, nếu không
    // một request kèm token vừa đổi có thể đi trước lúc token kịp ghi xuống localStorage.
    mac({
      serializableCheck: {
        /**
         * Bỏ qua nhánh cache của RTK Query. Bộ kiểm tra này duyệt **toàn bộ** state sau mỗi
         * hành động; khi hộp thư mở vài hội thoại thì nhánh `api` đã đủ lớn để nó vượt ngưỡng
         * 32ms và tự cảnh báo trên console.
         *
         * Bỏ qua ở đây không mất gì: mọi thứ trong nhánh này đến từ `JSON.parse` của phản hồi
         * HTTP hoặc của khung WebSocket, nên đã serializable theo định nghĩa. Phần state do
         * chúng ta tự viết (`auth`, `realtime`) vẫn được kiểm đầy đủ — đó mới là chỗ có thể
         * lỡ tay nhét vào một `Date` hay một `Map`.
         */
        ignoredPaths: [apiSlice.reducerPath],
      },
    })
      .prepend(luuPhienListener.middleware)
      .concat(apiSlice.middleware),
})

// Bật refetchOnReconnect. Không truyền tuỳ chọn nào khác — refetchOnFocus giữ mặc định (tắt).
setupListeners(store.dispatch)

// Trao store cho `axiosClient`, thứ chạy ngoài cây React
ganStore(store)

// Mở store ra cho console khi chạy dev. Redux DevTools xem được state, nhưng đọc thẳng cache của
// RTK Query trong console nhanh hơn nhiều khi cần trả lời "màn hình đang giữ dữ liệu nào".
if (import.meta.env.DEV) {
  ;(window as unknown as { store?: typeof store }).store = store
}

export type AppStore = typeof store
export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
