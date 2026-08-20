# syntax=docker/dockerfile:1
# Giai đoạn phát triển: chạy Vite dev server, có hot reload.
# Khi triển khai thật sẽ đổi sang build tĩnh + Nginx phục vụ (xem TODO ở README).
FROM node:22-alpine
WORKDIR /app
RUN apk add --no-cache curl
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
