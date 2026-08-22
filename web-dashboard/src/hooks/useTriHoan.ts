import { useEffect, useState } from 'react'

/**
 * Trì hoãn một giá trị đang đổi liên tục.
 *
 * Dùng cho ô tìm kiếm: gõ "báo giá" là 7 lần đổi state, và nếu mỗi lần đều thành một tham số truy
 * vấn mới thì RTK Query tạo 7 mục cache cùng lúc — trong đó 6 mục vô dụng ngay khi vừa về.
 */
export function useTriHoan<T>(giaTri: T, msTriHoan = 300): T {
  const [daTriHoan, datDaTriHoan] = useState(giaTri)

  useEffect(() => {
    const hen = setTimeout(() => datDaTriHoan(giaTri), msTriHoan)
    return () => clearTimeout(hen)
  }, [giaTri, msTriHoan])

  return daTriHoan
}
