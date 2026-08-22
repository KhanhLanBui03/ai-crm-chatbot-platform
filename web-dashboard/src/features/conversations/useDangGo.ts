import { useEffect, useState } from 'react'

import { ketNoiThoiGianThuc } from '@/api/realtime/ketNoi'

/**
 * "Khách đang gõ…" — trạng thái **phù du**, cố ý nằm ở state cục bộ của component chứ không
 * trong Redux và không trong cache RTK Query.
 *
 * Nó không phải dữ liệu: mất một khung thì không sao, và nó tự hết hạn. Cho vào cache là mời
 * một dòng chữ tạm bợ sống lâu hơn cả hội thoại sinh ra nó.
 */
export function useDangGo(idHoiThoai: string | null): boolean {
  const [dangGo, datDangGo] = useState(false)

  useEffect(() => {
    datDangGo(false)
    if (!idHoiThoai) return

    let hen: ReturnType<typeof setTimeout> | undefined
    const goBo = ketNoiThoiGianThuc.dangKy('AGENT_TYPING', (khung) => {
      if (khung.conversationId !== idHoiThoai) return
      datDangGo(true)
      // Máy chủ nói khung này hết hạn lúc nào thì tắt lúc đó. Không tự đặt một hằng số riêng:
      // hai bên đếm giờ khác nhau là chấm "đang gõ" kẹt lại vĩnh viễn trên màn hình.
      clearTimeout(hen)
      hen = setTimeout(
        () => datDangGo(false),
        Math.max(new Date(khung.expiresAt).getTime() - Date.now(), 0),
      )
    })

    return () => {
      clearTimeout(hen)
      goBo()
    }
  }, [idHoiThoai])

  return dangGo
}
