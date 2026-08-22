import axios, { AxiosError, type AxiosRequestConfig, type AxiosResponse } from 'axios'

import { dangXuat, datAccessToken } from '@/app/store/authSlice'
import { layStore } from '@/app/store/truyCapStore'
import { ApiError, type ApiResponse } from '@/types/api'

/**
 * Một client duy nhất cho toàn bộ dashboard. Không `axios.get(...)` rải rác trong component.
 *
 * Đường dẫn để tương đối (`/api/v1/...`) — Vite proxy chuyển tiếp sang gateway `:8080` ở môi
 * trường phát triển, và cùng origin ở môi trường thật. Không bao giờ gọi thẳng `java-core :8081`
 * hay `ai-service :8000`: đi vòng qua gateway là bỏ qua xác thực JWT, giới hạn tần suất và
 * `X-Trace-Id`.
 */
export const axiosClient = axios.create({
  timeout: 20_000,
  // Cần cho cookie HttpOnly chứa mã làm mới
  withCredentials: true,
})

/** Sinh mã theo dõi cho mỗi request để nối được với dòng log phía máy chủ. */
function sinhTraceId(): string {
  return crypto.randomUUID()
}

axiosClient.interceptors.request.use((config) => {
  const token = layStore()?.getState().auth.accessToken
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  config.headers.set('X-Trace-Id', sinhTraceId())
  return config
})

// ---- Làm mới token: gom các request bị 401 lại, chỉ gọi làm mới đúng một lần ----

let dangLamMoi = false
let hangCho: Array<(token: string | null) => void> = []

function giaiPhongHangCho(token: string | null) {
  hangCho.forEach((tiepTuc) => tiepTuc(token))
  hangCho = []
}

async function lamMoiToken(): Promise<string | null> {
  try {
    // Gọi bằng axios trần: request này không được đi qua interceptor ở trên,
    // nếu không nó sẽ tự đệ quy khi chính lời gọi làm mới trả về 401.
    const { data } = await axios.post<ApiResponse<{ accessToken: string }>>(
      '/api/v1/auth/refresh',
      null,
      { withCredentials: true, headers: { 'X-Trace-Id': sinhTraceId() } },
    )
    return data.data.accessToken
  } catch {
    return null
  }
}

function bocLoi(error: AxiosError<ApiResponse<unknown>>): ApiError {
  const status = error.response?.status ?? 0
  const than = error.response?.data
  const message =
    than?.message ??
    (status === 0 ? 'Không kết nối được máy chủ. Kiểm tra đường truyền rồi thử lại.' : error.message)
  const traceId = than?.traceId ?? (error.config?.headers?.['X-Trace-Id'] as string | undefined) ?? null
  return new ApiError(message, status, traceId)
}

axiosClient.interceptors.response.use(
  // Bóc vỏ ApiResponse ngay tại đây để phía gọi nhận thẳng T, không phải `.data.data` khắp nơi
  (response: AxiosResponse<ApiResponse<unknown>>) => {
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      response.data = response.data.data as never
    }
    return response
  },
  async (error: AxiosError<ApiResponse<unknown>>) => {
    const yeuCau = error.config as (AxiosRequestConfig & { _daThuLai?: boolean }) | undefined

    if (error.response?.status !== 401 || !yeuCau || yeuCau._daThuLai) {
      return Promise.reject(bocLoi(error))
    }

    yeuCau._daThuLai = true

    if (dangLamMoi) {
      // Chờ lượt làm mới đang chạy thay vì gọi thêm một lượt nữa
      const token = await new Promise<string | null>((resolve) => hangCho.push(resolve))
      if (!token) return Promise.reject(bocLoi(error))
      return axiosClient(yeuCau)
    }

    dangLamMoi = true
    const tokenMoi = await lamMoiToken()
    dangLamMoi = false
    giaiPhongHangCho(tokenMoi)

    if (!tokenMoi) {
      layStore()?.dispatch(dangXuat())
      return Promise.reject(bocLoi(error))
    }

    layStore()?.dispatch(datAccessToken(tokenMoi))
    return axiosClient(yeuCau)
  },
)

/** Hàm gọi ngắn gọn, đã bóc vỏ và đã gắn kiểu. */
export async function layDuLieu<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await axiosClient.get<T>(url, config)
  return data
}

export async function guiDuLieu<T>(url: string, than?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await axiosClient.post<T>(url, than, config)
  return data
}
