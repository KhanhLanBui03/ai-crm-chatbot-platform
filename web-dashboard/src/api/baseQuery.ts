import type { BaseQueryFn } from '@reduxjs/toolkit/query'
import type { AxiosRequestConfig } from 'axios'

import { axiosClient } from '@/api/axiosClient'
import { ApiError } from '@/types/api'

export interface ThamSoTruyVan {
  url: string
  method?: AxiosRequestConfig['method']
  body?: unknown
  params?: AxiosRequestConfig['params']
}

/**
 * Lỗi RTK Query lưu vào store. Phải là object thuần — `ApiError` là một `Error`, mà Error không
 * serialize được nên `serializableCheck` của RTK sẽ cảnh báo và Redux DevTools hiện ra rỗng.
 */
export interface LoiTruyVan {
  status: number
  message: string
  traceId: string | null
}

/**
 * Thu hẹp kiểu lỗi mà hook RTK Query trả về.
 *
 * `error` của hook là `LoiTruyVan | SerializedError` — nhánh thứ hai xuất hiện khi lỗi ném ra từ
 * chính `queryFn`/`transformResponse` chứ không phải từ mạng. Màn hình cần `status` và `traceId`
 * thì phải qua hàm này trước.
 */
export function laLoiTruyVan(loi: unknown): loi is LoiTruyVan {
  return typeof loi === 'object' && loi !== null && 'status' in loi && 'message' in loi
}

/**
 * Cầu nối RTK Query ↔ `axiosClient`.
 *
 * RTK Query mặc định dùng `fetchBaseQuery` (chạy trên `fetch`). Ta thay bằng axios để giữ nguyên
 * ba thứ đã có ở `axiosClient` và không phải viết lại lần hai: gắn `Authorization`, gắn
 * `X-Trace-Id`, và luồng xếp hàng khi làm mới token sau lỗi 401.
 */
export const axiosBaseQuery: BaseQueryFn<ThamSoTruyVan, unknown, LoiTruyVan> = async ({
  url,
  method = 'GET',
  body,
  params,
}) => {
  try {
    const { data } = await axiosClient({ url, method, data: body, params })
    return { data }
  } catch (loi) {
    if (loi instanceof ApiError) {
      return { error: { status: loi.status, message: loi.message, traceId: loi.traceId } }
    }
    return {
      error: {
        status: 0,
        message: loi instanceof Error ? loi.message : 'Lỗi không xác định',
        traceId: null,
      },
    }
  }
}
