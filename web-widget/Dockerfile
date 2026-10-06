# syntax=docker/dockerfile:1
# [PRODUCTION] Phục vụ widget.js ĐÃ BUILD — đúng file doanh nghiệp nhúng bằng một thẻ <script>
# (UC009 hậu điều kiện: "khung chat hoạt động trên các tên miền đã khai báo").
# Trước đây image chạy `npm run dev`: chỉ phục vụ mã nguồn /src/main.ts, không có /widget.js →
# mã nhúng sinh từ dashboard trỏ vào một file không tồn tại.
#
# Hai tầng: tầng build cần Node + devDependencies; tầng chạy chỉ là nginx + một file ~12 kB.

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts ./
COPY src ./src
RUN npm run build

FROM nginx:1.27-alpine
# Chỉ chép widget.js — không chép sourcemap (lộ mã nguồn và vô ích với khách hàng)
COPY --from=build /app/dist/widget.js /usr/share/nginx/widget/widget.js
COPY nginx/widget.conf /etc/nginx/conf.d/default.conf
COPY demo/index.html /usr/share/nginx/demo/index.template.html
COPY demo/40-dien-ma-nhung.sh /docker-entrypoint.d/40-dien-ma-nhung.sh
RUN chmod +x /docker-entrypoint.d/40-dien-ma-nhung.sh

# 5174: nơi phục vụ widget.js (vai CDN) · 3000: trang "Cửa hàng Demo" (vai website doanh nghiệp)
EXPOSE 5174 3000
