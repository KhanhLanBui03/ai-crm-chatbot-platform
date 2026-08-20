# ai-service — Track B

Khối AI: RAG, điều phối LangGraph, MCP Client, chấm điểm Lead, phân nhóm chủ đề, khung đánh giá.
Python 3.11 + FastAPI. Cổng **8000**.

```
api/            router FastAPI — bề mặt HTTP, không chứa logic AI
orchestrator/   đồ thị LangGraph, định tuyến đa nhánh
rag/            ingest · retrieve · rerank · generate  (11 chặng, mục 7.1)
mcp_client/     khám phá + gọi tool, lớp bảo vệ, kiểm toán
scoring/        chấm điểm Lead
clustering/     K-Means, Elbow
migration/      Flyway dải V2xx
eval/           golden_set · adversarial · configs · reports
common/         log JSON có Trace ID, ngoại lệ, số liệu Prometheus
tests/
```

## Ba ranh giới không được vượt

1. **Không chạm DB nghiệp vụ của Track A.** Mọi thao tác đi qua API nội bộ
   (`docs/openapi/java-core-to-ai-service.yaml`). Đây là phòng thủ chính chống rò rỉ chéo
   tenant khi bị tấn công tiêm chỉ thị — ADR-0002.
2. **Chỉ ghi dải V2xx** trong `migration/`, chỉ đụng schema `knowledge`, `ai`, `integration`.
3. **Mọi truy vấn vector lọc `tenant_id`** — ADR-0007, bề mặt T6.

## Hai cái bẫy đã biết trước

**Eureka.** FastAPI không tự đăng ký. Dùng `py-eureka-client`: đăng ký lúc khởi động, gửi nhịp
tim định kỳ, **hủy đăng ký lúc tắt**. Quên hủy thì Eureka vẫn định tuyến tới tiến trình đã chết
trong ~90 giây. Bật `prefer-ip-address` (kế hoạch mục 4.4).

**Kafka.** Chạy consumer trong **tác vụ nền theo vòng đời ứng dụng** (lifespan), không chạy trong
luồng xử lý request. Đặt `enable.auto.commit = false` và xác nhận offset **sau khi** xử lý xong —
để tự động thì offset có thể được ghi trước khi xử lý xong và sự kiện bị mất khi tiến trình chết
(kế hoạch mục 4.3).

## Chạy cục bộ

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # điền ANTHROPIC_API_KEY
uvicorn api.main:app --reload --port 8000
```

## TODO

- [ ] `api/main.py` — FastAPI app + lifespan (đăng ký Eureka, khởi động consumer Kafka)
- [ ] `common/config.py` — đọc cấu hình bằng pydantic-settings
- [ ] `common/logging.py` — log JSON có Trace ID, **làm từ Sprint 0**
- [ ] Migration V201–V210 (xem `migration/README.md`)
- [ ] Hàm chuẩn hóa văn bản dùng chung cho cả lúc nạp và lúc truy vấn
- [ ] `eval/golden_set.jsonl` — 150 câu, mốc M4 hạn 12/10
