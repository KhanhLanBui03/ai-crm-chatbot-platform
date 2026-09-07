import { createListenerMiddleware, createSlice, isAnyOf, type PayloadAction } from '@reduxjs/toolkit'

import type { NguoiDungHienTai } from '@/types/schema'

/**
 * Hồ sơ người đang đăng nhập — chính là `NguoiDungHienTai` của giao ước OpenAPI.
 * Giữ tên ngắn ở đây vì nó xuất hiện dày trong tầng giao diện.
 */
export type NguoiDung = NguoiDungHienTai

export interface TrangThaiAuth {
  accessToken: string | null
  nguoiDung: NguoiDung | null
}

const KHOA_LUU = 'crm-ai-phien'

/**
 * Khôi phục phiên từ lần mở trước.
 *
 * Chỉ `accessToken` và hồ sơ người dùng nằm ở đây. Mã làm mới nằm ở cookie `HttpOnly` do máy chủ
 * đặt, không đi qua JavaScript — nên `localStorage` bị đọc trộm cũng chỉ mất một token ngắn hạn.
 */
function khoiPhucPhien(): TrangThaiAuth {
  const rong: TrangThaiAuth = { accessToken: null, nguoiDung: null }
  try {
    const thoRaw = localStorage.getItem(KHOA_LUU)
    if (!thoRaw) return rong
    const tho = JSON.parse(thoRaw) as Partial<TrangThaiAuth>
    if (typeof tho.accessToken !== 'string' || !tho.nguoiDung) return rong
    return { accessToken: tho.accessToken, nguoiDung: tho.nguoiDung }
  } catch {
    // Dữ liệu cũ hỏng hoặc lệch phiên bản — bỏ qua, coi như chưa đăng nhập
    return rong
  }
}

const authSlice = createSlice({
  name: 'auth',
  initialState: khoiPhucPhien(),
  reducers: {
    dangNhap(state, action: PayloadAction<{ accessToken: string; nguoiDung: NguoiDung }>) {
      state.accessToken = action.payload.accessToken
      state.nguoiDung = action.payload.nguoiDung
    },
    dangXuat(state) {
      state.accessToken = null
      state.nguoiDung = null
    },
    /** Sau mỗi lượt làm mới token. Hồ sơ người dùng giữ nguyên. */
    datAccessToken(state, action: PayloadAction<string | null>) {
      state.accessToken = action.payload
    },
  },
})

export const { dangNhap, dangXuat, datAccessToken } = authSlice.actions
export const authReducer = authSlice.reducer

/**
 * Ghi phiên xuống `localStorage` sau mỗi hành động chạm tới nó.
 *
 * Dùng listener của RTK thay vì kéo thêm `redux-persist`: chỉ có hai trường cần lưu, và
 * `redux-persist` bắt phải bọc thêm `PersistGate` cùng một loạt action nội bộ mà `serializableCheck`
 * phải bỏ qua — không đáng cho một object hai trường.
 */
export const luuPhienListener = createListenerMiddleware()

luuPhienListener.startListening({
  matcher: isAnyOf(dangNhap, dangXuat, datAccessToken),
  effect: (_hanhDong, api) => {
    const { auth } = api.getState() as { auth: TrangThaiAuth }
    if (!auth.accessToken) {
      localStorage.removeItem(KHOA_LUU)
      return
    }
    localStorage.setItem(KHOA_LUU, JSON.stringify(auth))
  },
})
