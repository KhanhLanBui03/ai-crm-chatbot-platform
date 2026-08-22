import { useCallback, useEffect, useState } from 'react'

const KHOA = 'crm-ai-che-do'

function doc(): boolean {
  const luu = localStorage.getItem(KHOA)
  if (luu) return luu === 'toi'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/**
 * Chế độ sáng/tối. Token đổi bằng lớp `.dark` trên thẻ gốc — xem `src/styles/index.css`.
 * Đây là trạng thái giao diện thuần túy nên giữ ở component, không đưa vào TanStack Query.
 */
export function useCheDo() {
  const [toi, datToi] = useState(doc)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', toi)
    localStorage.setItem(KHOA, toi ? 'toi' : 'sang')
  }, [toi])

  const doiCheDo = useCallback(() => datToi((v) => !v), [])

  return { toi, doiCheDo }
}
