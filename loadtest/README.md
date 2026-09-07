# loadtest — k6 (Track A)

Kiểm thử chịu tải. Nguồn số liệu cho **mục hiệu năng ở chương 5** của báo cáo,
và cho thí nghiệm **E10** (chi phí và độ trễ).

## Chạy

```bash
# Cài k6: brew install k6
k6 run scenarios/<ten-kich-ban>.js

# Xuất kết quả để đưa vào báo cáo
k6 run --summary-export=results/<ten>.json scenarios/<ten>.js
```

## Kịch bản dự kiến

| File | Đo cái gì | Ngưỡng |
|---|---|---|
| `smoke.js` | Hệ thống có sống không, 1 VU | không lỗi |
| `crm-crud.js` | Đường CRM thuần (lead, deal, contact) qua gateway | p95 < 300ms |
| `chat-rag.js` | Đường hội thoại có RAG — chặng đắt nhất | p95 ghi nhận, không đặt ngưỡng cứng |
| `websocket.js` | Số kết nối WebSocket đồng thời | giữ ổn định ở mức mục tiêu |
| `multi-tenant.js` | Nhiều tenant chạy song song | **không rò rỉ chéo tenant** |

## Quy tắc

- Chạy trên môi trường **cô lập**, dữ liệu giả — không bao giờ chạy vào dữ liệu pilot thật.
- Ghi lại phiên bản mô hình và `git_sha` cùng mỗi lần chạy để tái lập được (kế hoạch mục 8.1).
- Đo **theo từng chặng**, không chỉ đo tổng: gateway → java-core → ai-service → truy hồi →
  xếp hạng lại → sinh câu trả lời. Chặng xếp hạng lại là chặng tốn thời gian nhất (ADR-0006).
- Kết quả đi vào `results/` — thư mục này **không commit** (xem `.gitignore`).

## TODO

- [ ] Viết `smoke.js` trước, ngay khi xương sống chạy (mốc M3 — 28/09)
