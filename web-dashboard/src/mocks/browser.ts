import { setupWorker } from 'msw/browser'

import { handlers } from '@/mocks/handlers'
import { wsHandlers } from '@/mocks/ws'

/**
 * Hai cơ chế chặn khác nhau nằm chung một `setupWorker`:
 *
 * - HTTP đi qua **Service Worker** (`public/mockServiceWorker.js`)
 * - WebSocket thì MSW thay thẳng lớp `WebSocket` toàn cục — Service Worker không chặn được
 *   bắt tay nâng cấp giao thức
 *
 * Khác biệt đó có hệ quả thật: `wsHandlers` chỉ có tác dụng với socket mở **sau** khi
 * `worker.start()` chạy xong. `main.tsx` bật mock trước khi render nên điều kiện luôn đúng.
 */
export const worker = setupWorker(...handlers, ...wsHandlers)
