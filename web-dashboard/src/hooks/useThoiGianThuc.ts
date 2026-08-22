import { useEffect } from 'react'

import { ketNoiThoiGianThuc } from '@/api/realtime/ketNoi'
import { useAppSelector } from '@/app/store/hooks'

/**
 * Mở kết nối thời gian thực theo phiên đăng nhập.
 *
 * Gọi **một lần** trong `AppShell` — không phải trong từng màn cần dữ liệu sống. `AppShell`
 * dựng đúng khi đã đăng nhập và tháo khi đăng xuất, nên vòng đời của nó chính là vòng đời cần
 * có của socket. Việc "màn nào cần nhận gì" đã do `onCacheEntryAdded` của từng endpoint lo.
 */
export function useKetNoiThoiGianThuc() {
  const accessToken = useAppSelector((s) => s.auth.accessToken)

  useEffect(() => {
    if (!accessToken) return
    ketNoiThoiGianThuc.moKetNoi(accessToken)
    return () => ketNoiThoiGianThuc.dongKetNoi()
  }, [accessToken])
}

/** Trạng thái đường truyền cho chỉ báo trên thanh trên. */
export function useTrangThaiThoiGianThuc() {
  return useAppSelector((s) => s.realtime)
}
