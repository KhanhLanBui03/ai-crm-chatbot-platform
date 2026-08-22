import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  // Tailwind v4 chạy bằng plugin Vite, không qua postcss.config.js như v3
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true, // cần thiết khi chạy trong Docker
    proxy: {
      // Mọi lời gọi API đi qua gateway, không gọi thẳng java-core/ai-service
      '/api': {
        target: process.env.VITE_GATEWAY_URL ?? 'http://localhost:8080',
        changeOrigin: true,
      },
      '/ai': {
        target: process.env.VITE_GATEWAY_URL ?? 'http://localhost:8080',
        changeOrigin: true,
      },
      '/ws': {
        target: process.env.VITE_GATEWAY_URL ?? 'http://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
