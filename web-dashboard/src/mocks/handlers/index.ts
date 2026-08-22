import { xacThucHandlers } from '@/mocks/handlers/xac-thuc'
import { hopThuHandlers } from '@/mocks/handlers/hop-thu'
import { banHangHandlers } from '@/mocks/handlers/ban-hang'
import { kenhHandlers } from '@/mocks/handlers/kenh'
import { khachHangHandlers } from '@/mocks/handlers/khach-hang'
import { nenTangHandlers } from '@/mocks/handlers/nen-tang'
import { triThucHandlers } from '@/mocks/handlers/tri-thuc'
import { kiemToanHandlers } from '@/mocks/handlers/kiem-toan'

/**
 * Một file mỗi nhóm endpoint, gộp ở đây.
 *
 * Thứ tự có ý nghĩa: MSW lấy handler **khớp đầu tiên**. Đường dẫn cụ thể phải đứng trước đường
 * dẫn có tham số — `/api/v1/erasure-requests/preview` mà xếp sau
 * `/api/v1/erasure-requests/:id` thì `preview` bị hiểu thành một id.
 */
export const handlers = [
  ...xacThucHandlers,
  ...nenTangHandlers,
  ...kenhHandlers,
  ...hopThuHandlers,
  ...khachHangHandlers,
  ...banHangHandlers,
  ...triThucHandlers,
  ...kiemToanHandlers,
]
