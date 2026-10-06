import { defineConfig } from 'vite'

// Widget được nhúng vào website của khách hàng bằng một thẻ <script>.
// Vì vậy build ra thư viện IIFE một file, không phụ thuộc framework — giữ kích thước nhỏ
// và không xung đột với thứ mà trang chủ nhà đang dùng.
export default defineConfig({
  build: {
    lib: {
      // Đường dẫn tương đối tính từ thư mục gốc dự án — không cần node:path/@types/node
      entry: 'src/main.ts',
      name: 'CrmAiWidget',
      formats: ['iife'],
      fileName: () => 'widget.js',
    },
    cssCodeSplit: false,
    sourcemap: true,
  },
  server: {
    port: 5174,
    host: true,
  },
})
