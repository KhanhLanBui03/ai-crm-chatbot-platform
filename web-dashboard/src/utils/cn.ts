import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Gộp class Tailwind: `clsx` xử lý điều kiện, `tailwind-merge` khử class chồng nhau
 * (`px-2 px-4` → `px-4`). Rule frontend: không nối chuỗi class bằng tay.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
