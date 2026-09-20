# ai-service — Tầng orchestration của module AI

RAG, điều phối LangGraph, MCP Client, chấm điểm Lead, telemetry. Python 3.11 + FastAPI.
Cổng **8000**.

Bố cục `src/` theo **Master Plan §3.9.2**. **ADR-0015** giải thích vì sao thay thế ADR-0010
(vốn chọn `app/`) và ba chỗ cố ý lệch khỏi hình vẽ §3.9.2.

## Điều quan trọng nhất: service này KHÔNG nạp model

Kiến trúc hai tầng v8.0 (§3.2) đưa toàn bộ model sang `inference/`:

| | `ai-service/` (thư mục này) | `inference/` |
|---|---|---|
| Vai trò | orchestration — I/O thuần | suy luận — CPU thuần |
| ML runtime | **KHÔNG** | onnxruntime · tokenizers · numpy |
| Image | < 400 MB · pod sẵn sàng **2–5 s** | < 900 MB |
| Chọn vai trò | `RUN_MODE=api\|worker` | `MODEL_ROLE=embed\|rerank\|classify` |

Cổng chặn CI chạy mỗi build và sẽ đỏ nếu image này có ML runtime:

```bash
docker run --rm ai-service:ci pip list --format=freeze \
  | grep -Eiq "^(onnxruntime|torch|xgboost)" && exit 1
```

Đúng **ba gói** (ADR-0015 mục 4). `scikit-learn` có trong image như phụ thuộc gián tiếp của
`pyvi` và được chấp nhận có chủ đích — thêm nó vào cổng là làm đỏ mọi build. Luật đi kèm:
cấm `import sklearn` trong `src/`, CI kiểm bằng một bước grep riêng.

Lợi ích lớn nhất không phải dung lượng mà là **tách bạch bề mặt gỡ lỗi**: khi p95 xấu đi,
`ai-service` chỉ có thể chậm vì *chờ*, tầng suy luận chỉ có thể chậm vì *tính*. Không có vùng xám.

## Cấu trúc

```
ai-service/
├── Dockerfile                  một image, hai vai trò
├── requirements/{base,dev}.{in,txt}
├── migration/                  Flyway dải V2xx  ← xem ghi chú bên dưới
├── k8s/                        manifest EKS — §3.10
├── src/
│   ├── entrypoint.py           đọc RUN_MODE · GHIM workers=1 (§3.9.1)
│   ├── api/                    FastAPI — main · deps · eureka · v1/
│   ├── worker/                 Kafka consumer — GIỮ RIÊNG package
│   └── ai/
│       ├── service.py          FACADE DUY NHẤT
│       ├── schemas.py          hợp đồng §2.5 — là FILE, không phải thư mục
│       ├── config.py           exceptions.py
│       ├── inference/          client gọi sang tầng suy luận (§3.4)
│       ├── orchestrator/       LangGraph, handoff        UC014, UC022
│       ├── rag/                ingest·retrieve·rerank·generate  UC018–020, 023, 025
│       ├── mcp_client/         discover + allow-list     UC021, UC024, UC028
│       ├── extraction/         JSON Schema nghiêm ngặt   UC029
│       ├── guardrails/         regex, normalize_vi — THUẦN PYTHON
│       ├── scoring/            UC030      clustering/  UC038
│       ├── db/                 session · RLS · models/ · repositories/
│       ├── events/             Kafka producer/consumer
│       ├── telemetry/          logging · metrics         UC039, UC040
│       └── integrations/       java_core/ (ADR-0002) · llm/
└── tests/{unit, integration, eval}/
```

> **`migration/` lệch §3.9.2 có chủ ý.** Hình vẽ §3.9.2 ghi `alembic/`, nhưng ở đây vẫn là
> **Flyway dải V2xx** — đó là cơ chế chống xung đột giữa hai làn, và `scripts/migrate-ai.sh`
> cùng `docs/erd-*.md` đều bám vào nó. Lý do đầy đủ: ADR-0015.

## `src` là package thật, không phải quy ước src-layout

`src/entrypoint.py` gọi `"src.api.main:app"` nên `src` phải import được: nó có `__init__.py`,
và `pyproject.toml` khai `where = ["."]` + `include = ["src*"]` — **không** dùng `where = ["src"]`.
Docker `WORKDIR /app` với mã ở `/app/src` cũng vì lý do này.

## Ba vùng, ba mục đích khác nhau

| Thư mục | Là gì | Chạy khi nào |
|---|---|---|
| `src/` | Mã phục vụ request | Trong sản phẩm, mọi lúc |
| `tests/eval/` | Harness thí nghiệm, golden set, adversarial | Chỉ khi chạy thực nghiệm |
| `migration/` | Schema (SQL) | Lúc triển khai |

`tests/eval/` import ngược vào `src.ai` là **đúng chiều** — đó là lý do `src/ai/` phải độc lập
với HTTP.

## Chiều phụ thuộc — hai luật

```
api ──┐
      ├──► ai/service.py ──► rag · orchestrator · mcp_client · extraction · scoring
worker┘                  └──► db · events · telemetry · inference · integrations
```

1. **`src/ai/` không import `src.api` hay `src.worker`.**
2. **`api/` và `worker/` không import chéo nhau** (§3.9.1 — một image, hai vai trò độc lập).

Lệnh kiểm phải **neo vào đầu dòng**, nếu không nó tự khớp câu lệnh viết trong docstring:

```bash
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.(api|worker)\b' src/ai/   # phải rỗng
```

## Đặt file mới ở đâu

| Bạn đang viết | Đặt vào |
|---|---|
| Endpoint HTTP | `src/api/v1/endpoints/` |
| Pydantic DTO vào/ra | `src/ai/schemas.py` |
| Phương thức mới cho tầng trên gọi | `src/ai/service.py` (facade) |
| Bước xử lý RAG | `src/ai/rag/<chặng>/` |
| Đồ thị LangGraph, chính sách handoff | `src/ai/orchestrator/` |
| Gọi tool MCP, allow-list | `src/ai/mcp_client/` |
| Trích xuất theo JSON Schema | `src/ai/extraction/` |
| Regex, chuẩn hoá tiếng Việt, PII | `src/ai/guardrails/` |
| Gọi sang ai-embed/rerank/classify | `src/ai/inference/` |
| Truy vấn CSDL | `src/ai/db/repositories/` |
| Bảng CSDL (ORM) | `src/ai/db/models/` |
| Gọi java-core hoặc LLM API | `src/ai/integrations/` |
| Phát/nhận Kafka | `src/ai/events/` |
| Log, số liệu, telemetry | `src/ai/telemetry/` |
| Consumer chạy nền | `src/worker/` |
| Script đo đạc, thí nghiệm | `tests/eval/` |
| **Model, notebook, artifact** | **`inference/` · `notebooks/` — KHÔNG đặt ở đây** |

## Bốn ranh giới không được vượt

1. **Không chạm CSDL nghiệp vụ của Track A.** Mọi thao tác đi qua `src/ai/integrations/java_core/`
   theo `docs/openapi/java-core-to-ai-service.yaml`. Đây là phòng thủ chính chống rò rỉ chéo
   tenant khi bị tiêm chỉ thị — ADR-0002, bề mặt T5.
2. **Chỉ ghi dải V2xx** trong `migration/`, chỉ đụng schema `knowledge`, `ai`, `integration`.
3. **Mọi truy vấn vector lọc `tenant_id`** — ADR-0007, bề mặt T6.
4. **`tenant_id` chỉ từ header `X-Tenant-Id`** do gateway gắn (`src/api/deps.py`). Không bao giờ
   từ body/query/path, không bao giờ có giá trị mặc định.

## Ba cái bẫy đã biết trước

**RLS và connection pool.** `SET LOCAL app.tenant_id` đặt **ngay sau `pool.acquire()`**, trong
cùng transaction với truy vấn. Quên một chỗ là rò tenant, và không có lỗi nào báo ra.

**Eureka.** FastAPI không tự đăng ký. `src/api/eureka.py`: đăng ký lúc khởi động, gửi nhịp tim,
**hủy đăng ký lúc tắt**. Quên hủy thì Eureka định tuyến tới tiến trình đã chết ~90 giây.

**Kafka.** Consumer chạy ở tiến trình riêng (`RUN_MODE=worker`), không trong luồng request.
`enable_auto_commit=False`, xác nhận offset **sau khi** xử lý xong. Và nhớ hai listener:
`kafka:9092` từ trong mạng Docker · `localhost:29092` từ máy chủ.

## Đường dẫn: cái nào có phiên bản

| Đường dẫn | Phiên bản | Vì sao |
|---|---|---|
| `/v1/ai/**` | Có | Giao ước nghiệp vụ với java-core, sẽ tiến hoá |
| `/health`, `/ready`, `/metrics` | **Không** | Bề mặt vận hành — Compose và Prometheus phải gọi được kể cả khi giao ước lên `v2` |

`/ready` khác `/health`: `/health` kiểm tiến trình còn sống; `/ready` kiểm **tầng suy luận và DB**,
và fail-closed nếu lệch một trong ba bất biến §3.4.2.

## Chạy cục bộ

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt      # dev.txt đã -r base.txt
cp .env.example .env                     # điền ANTHROPIC_API_KEY

python -m src.entrypoint                 # RUN_MODE=api mặc định
RUN_MODE=worker python -m src.entrypoint # consumer Kafka
```

Chưa bật tầng suy luận thì đặt `AI_MODE=mock` — trả dữ liệu giả có seed cố định (§3.4.1).

Kiểm nhanh không cần cài phụ thuộc:

```bash
python3.11 -m compileall -q src tests
python3.11 -c "import src, src.ai, src.worker"
ruff check src tests
```

## File đã có mã thật

`src/ai/config.py` (pydantic-settings) · `src/ai/telemetry/logging.py` (JSON + Trace ID qua
`ContextVar`) · `src/ai/telemetry/metrics.py` · `src/ai/exceptions.py` · `src/api/eureka.py` ·
`src/api/deps.py` · `src/api/v1/endpoints/health.py` · `src/ai/schemas.py` · `src/api/main.py` ·
`src/entrypoint.py`.

Các file còn lại mới có docstring nêu trách nhiệm, UC phụ trách và mục Master Plan tham chiếu.

## TODO

- [ ] `src/ai/db/session.py` — phiên async, `SET LOCAL app.tenant_id` mỗi transaction
- [ ] `src/ai/service.py` — 11 phương thức facade theo §2.5
- [ ] `src/worker/main.py` — `run_worker()`, chống trùng theo `event_id` **trước** consumer đầu tiên
- [ ] Hàm chuẩn hoá văn bản dùng chung cho **cả lúc nạp và lúc truy vấn**
- [ ] Middleware gắn `X-Trace-Id` vào `ContextVar`
- [ ] `tests/integration/test_rls.py` và `test_contract.py`
- [ ] `tests/eval/golden_qa.jsonl` — ≥ 80 cặp, recall@5 ≥ 0,85
