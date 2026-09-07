# ai-service — Track B

Khối AI: RAG, điều phối LangGraph, MCP Client, chấm điểm Lead, phân nhóm chủ đề, khung đánh giá.
Python 3.11 + FastAPI. Cổng **8000**.

Bố cục theo chuẩn FastAPI production — **ADR-0010** giải thích vì sao lệch chữ của Phụ lục A.

## Cấu trúc

```
ai-service/
├── app/                     ← mã phục vụ request
│   ├── main.py              create_app() + lifespan (Eureka, consumer Kafka)
│   ├── api/
│   │   ├── deps.py          DI: settings · session · tenant_id · trace_id
│   │   └── v1/{router.py, endpoints/}
│   ├── core/                config · logging · exceptions · metrics · eureka
│   ├── db/{session, base, models/}      SQLAlchemy
│   ├── schemas/             Pydantic DTO — GIAO ƯỚC với java-core
│   ├── repositories/        truy cập dữ liệu
│   ├── domain/              ← capability của Phụ lục A
│   │   ├── orchestrator/    đồ thị LangGraph, định tuyến đa nhánh
│   │   ├── rag/             ingest · retrieve · rerank · generate (11 chặng, mục 7.1)
│   │   ├── mcp_client/      khám phá + gọi tool, lớp bảo vệ, kiểm toán
│   │   ├── scoring/         chấm điểm Lead
│   │   └── clustering/      K-Means, Elbow
│   ├── integrations/        java_core/ · llm/ · kafka/
│   └── workers/consumers/   tác vụ nền theo vòng đời ứng dụng
│
├── migration/               Flyway dải V2xx
├── eval/                    golden_set · adversarial · configs · reports
└── tests/{unit,integration,e2e}/
```

## Ba vùng, ba mục đích khác nhau

| Thư mục | Là gì | Chạy khi nào |
|---|---|---|
| `app/` | Mã phục vụ request | Trong sản phẩm, mọi lúc |
| `eval/` | Harness thí nghiệm E1–E11 | Chỉ khi chạy thực nghiệm |
| `migration/` | Schema (SQL) | Lúc triển khai |

`eval/` **cố ý nằm ngoài `app/`**: nó không phục vụ request. `eval/` import ngược vào
`app.domain.rag` là bình thường và đúng chiều — đó chính là lý do domain phải độc lập với HTTP.

## Chiều phụ thuộc — một hướng duy nhất

```
api ──► domain ──► repositories ──► db
 │         │
 └─────────┴──► core, schemas, integrations
```

**`app/domain/` không được import `app.api`.** Domain không cần biết mình đang chạy sau HTTP
hay sau một consumer Kafka. Kiểm tra bằng một lệnh:

```bash
grep -rn "from app.api\|import app.api" app/domain/    # phải rỗng
```

## Đặt file mới ở đâu

| Bạn đang viết | Đặt vào |
|---|---|
| Endpoint HTTP | `app/api/v1/endpoints/` |
| Pydantic DTO vào/ra | `app/schemas/` |
| Bước xử lý AI | `app/domain/<capability>/` |
| Truy vấn CSDL | `app/repositories/` |
| Bảng CSDL (ORM) | `app/db/models/` |
| Gọi HTTP/Kafka ra ngoài | `app/integrations/` |
| Tác vụ chạy nền | `app/workers/` |
| Cấu hình, log, số liệu | `app/core/` |
| Script đo đạc, thí nghiệm | `eval/` |

## Ba ranh giới không được vượt

1. **Không chạm CSDL nghiệp vụ của Track A.** Mọi thao tác đi qua `app/integrations/java_core/`
   theo `docs/openapi/java-core-to-ai-service.yaml`. Đây là phòng thủ chính chống rò rỉ chéo
   tenant khi bị tấn công tiêm chỉ thị — ADR-0002.
2. **Chỉ ghi dải V2xx** trong `migration/`, chỉ đụng schema `knowledge`, `ai`, `integration`.
3. **Mọi truy vấn vector lọc `tenant_id`** — ADR-0007, bề mặt tấn công T6.

## Hai cái bẫy đã biết trước

**Eureka.** FastAPI không tự đăng ký. Xem `app/core/eureka.py`: đăng ký lúc khởi động, gửi nhịp
tim, **hủy đăng ký lúc tắt**. Quên hủy thì Eureka vẫn định tuyến tới tiến trình đã chết trong
~90 giây. Bật `prefer-ip-address` (kế hoạch mục 4.4).

**Kafka.** Consumer chạy trong **tác vụ nền theo lifespan** (`app/workers/`), không chạy trong
luồng xử lý request. Đặt `enable.auto.commit = False` và xác nhận offset **sau khi** xử lý xong
(kế hoạch mục 4.3).

## Đường dẫn: cái nào có phiên bản, cái nào không

| Đường dẫn | Phiên bản | Vì sao |
|---|---|---|
| `/v1/answer`, `/v1/documents/…` | Có | Giao ước nghiệp vụ với java-core, sẽ tiến hóa |
| `/health`, `/metrics` | **Không** | Bề mặt vận hành — Docker Compose và Prometheus phải gọi được kể cả khi giao ước lên `v2` |

## Chạy cục bộ

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # điền ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Kiểm tra cú pháp mà không cần cài phụ thuộc nặng (torch, sentence-transformers):

```bash
python3.11 -m compileall -q app eval
```

## File mẫu đã có

`app/core/config.py` (pydantic-settings, dùng được ngay), `app/core/logging.py` (JSON + Trace ID
qua `ContextVar`), `app/core/metrics.py`, `app/core/exceptions.py`, `app/core/eureka.py`,
`app/api/deps.py`, `app/api/v1/endpoints/health.py`, `app/schemas/answer.py`, `app/main.py`.

## TODO

- [ ] `app/db/session.py` — phiên async, đặt `SET LOCAL app.tenant_id` cho mỗi transaction
- [ ] Migration V201–V210 (xem `migration/README.md`)
- [ ] Hàm chuẩn hóa văn bản dùng chung cho **cả lúc nạp và lúc truy vấn** (mục 7.1 chặng 2)
- [ ] Middleware gắn `X-Trace-Id` vào `ContextVar`
- [ ] `eval/golden_set.jsonl` — 150 câu, mốc M4 hạn 12/10
