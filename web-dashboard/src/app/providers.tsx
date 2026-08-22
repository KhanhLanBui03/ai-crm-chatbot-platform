import { Provider } from 'react-redux'

import { store } from '@/app/store'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'

/**
 * Không có tuỳ chọn cache nào ở đây — chúng nằm cạnh chỗ khai báo: `keepUnusedDataFor` và
 * `refetchOnReconnect` trong `apiSlice`, thời gian sống riêng của từng endpoint trong file
 * `src/api/*.ts` tương ứng. RTK Query mặc định không thử lại request hỏng, nên cũng không cần
 * luật "bỏ qua 4xx" như khi dùng thư viện có retry sẵn.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Provider store={store}>
      <TooltipProvider delayDuration={300}>
        {children}
        <Toaster position="bottom-right" />
      </TooltipProvider>
    </Provider>
  )
}
