import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from '@/app/App'

import '@/styles/index.css'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Không tìm thấy phần tử #root — kiểm tra lại index.html')
}

/**
 * Bật tầng mock TRƯỚC khi render, nếu không vài request đầu sẽ lọt qua Service Worker.
 *
 * MSW chặn ở tầng mạng nên `axiosClient` không biết gì về nó: cùng đường dẫn, cùng interceptor,
 * cùng chỗ bóc `ApiResponse`. Đặt `VITE_USE_MOCK=false` là chạy backend thật, không sửa
 * component nào.
 */
async function batMockNeuCan() {
  if (import.meta.env.VITE_USE_MOCK !== 'true') return
  const { worker } = await import('@/mocks/browser')
  await worker.start({
    // Request nào không có handler vẫn đi tiếp qua Vite proxy tới gateway
    onUnhandledRequest: 'bypass',
    quiet: true,
  })
}

batMockNeuCan().then(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
