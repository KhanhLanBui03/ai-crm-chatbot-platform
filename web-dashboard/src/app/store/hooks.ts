import { useDispatch, useSelector } from 'react-redux'

import type { AppDispatch, RootState } from '@/app/store'

/**
 * Bản đã gắn kiểu của `useDispatch` / `useSelector`.
 *
 * Dùng hai hook này ở mọi component — `useSelector` trần bắt phải chú thích `RootState` bằng tay ở
 * từng chỗ gọi, và chỉ cần quên một lần là mất luôn kiểm tra kiểu cho nhánh state đó.
 */
export const useAppDispatch = useDispatch.withTypes<AppDispatch>()
export const useAppSelector = useSelector.withTypes<RootState>()
