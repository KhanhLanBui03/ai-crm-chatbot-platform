import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

/**
 * Trạng thái **đường truyền** WebSocket. Không chứa một mẩu dữ liệu nghiệp vụ nào.
 *
 * Tin nhắn và hội thoại đến qua WebSocket đi thẳng vào cache của RTK Query bằng
 * `onCacheEntryAdded` (xem `src/api/conversations.ts`). Nếu chép thêm một bản vào slice này thì
 * một dòng dữ liệu có hai chỗ chứa, và hai chỗ chứa thì sớm muộn cũng lệch nhau.
 */

export type TrangThaiDuongTruyen =
  | 'dong'
  | 'dang-noi'
  | 'mo'
  | 'dang-noi-lai'
  | 'loi'

export interface TrangThaiThoiGianThuc {
  duongTruyen: TrangThaiDuongTruyen
  /** Thời điểm nhận khung mang dữ liệu gần nhất (ISO). Dùng cho tooltip "cập nhật lúc…". */
  nhanKhungLuc: string | null
  /** Mã đóng của lần rớt gần nhất — 4401 hiển thị khác 1006. */
  maDongCuoi: number | null
}

const banDau: TrangThaiThoiGianThuc = {
  duongTruyen: 'dong',
  nhanKhungLuc: null,
  maDongCuoi: null,
}

const realtimeSlice = createSlice({
  name: 'realtime',
  initialState: banDau,
  reducers: {
    datTrangThai(
      state,
      action: PayloadAction<{ trangThai: TrangThaiDuongTruyen; maDongCuoi?: number }>,
    ) {
      state.duongTruyen = action.payload.trangThai
      if (action.payload.maDongCuoi !== undefined) {
        state.maDongCuoi = action.payload.maDongCuoi
      }
      if (action.payload.trangThai === 'mo') {
        state.maDongCuoi = null
      }
    },
    ghiNhanKhung(state) {
      state.nhanKhungLuc = new Date().toISOString()
    },
  },
})

export const { datTrangThai, ghiNhanKhung } = realtimeSlice.actions
export const realtimeReducer = realtimeSlice.reducer
