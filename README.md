# thesis-crm-ai

Chatbot AI chăm sóc khách hàng tích hợp CRM cho doanh nghiệp vừa và nhỏ.
Đồ án tốt nghiệp — nhóm 2 người, lộ trình 19 tuần (19/08/2026 → 31/12/2026).

Kế hoạch đầy đủ: [`docs/Ke-hoach-do-an-Chatbot-AI-CRM-v2-nhom-2-nguoi.docx`](docs/).

---

## Chạy trong 5 phút

**Cần có:** Docker Desktop (≥ 4.30), Java 21, Node 22, Python 3.11.

```bash
git clone <repo> && cd ai-crm-chatbot-platform

# 1. Cấu hình. Nếu máy bạn đã có PostgreSQL/Redis chiếm cổng, đổi *_HOST_PORT ở đây.
cp .env.example .env

# 2. Hạ tầng — chạy được ngay, không cần code (kafka kéo theo zookeeper)
docker compose up -d postgres redis kafka
docker compose ps                    # cả bốn phải "healthy"

# 3. Khai báo topic Kafka tường minh
bash scripts/create-topics.sh        # phải hiện đủ 5 topic

# 4. Toàn bộ dịch vụ (cần code — xem "Trạng thái" bên dưới)
docker compose up -d

# 5. Quan sát hệ thống, khi cần
docker compose --profile observability up -d
```

Dừng lại: `docker compose down` (thêm `-v` nếu muốn xóa luôn dữ liệu).

**Trạng thái hiện tại:** repo đang ở bước *dựng khung*. Bước 1–3 chạy được ngay;
bước 4 sẽ báo lỗi build cho tới khi mỗi service có mã nguồn — đó là dự kiến.

### Bảng cổng

| Dịch vụ | Cổng | Địa chỉ | Làn |
|---|---|---|---|
| Gateway | 8080 | http://localhost:8080 | A |
| java-core | 8081 | http://localhost:8081 | A |
| Eureka | 8761 | http://localhost:8761 | A |
| web-dashboard | 5173 | http://localhost:5173 | A |
| web-widget | 5174 | http://localhost:5174 | A |
| ai-service | 8000 | http://localhost:8000 | B |
| PostgreSQL + pgvector | 5432 | — | — |
| Redis | 6379 | — | — |
| Kafka | 9092 / **29092** | trong Docker / từ máy chủ | — |
| ZooKeeper | 2181 | — | — |
| Prometheus | 9090 | http://localhost:9090 | profile `observability` |
| Grafana | 3000 | http://localhost:3000 | profile `observability` |

Bốn cổng hạ tầng (PostgreSQL, Redis, Kafka, ZooKeeper) là cổng **trên máy chủ**, đổi được
bằng `POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`, `KAFKA_HOST_PORT`, `ZOOKEEPER_HOST_PORT`
trong `.env`. Cổng bên trong mạng Docker không đổi — các service luôn gọi nhau bằng
`postgres:5432`, `redis:6379`, `kafka:9092`.

Kafka có **hai listener**: `kafka:9092` cho container, `localhost:29092` cho máy chủ.
Dùng nhầm là lỗi kết nối khó đoán nhất của dự án.

---

## Kiến trúc

```
     [Web Widget]              [Zalo OA  hoặc  FB Messenger]
           │                              │
           └──────────────┬───────────────┘
                          ▼
                 Nginx        TLS, chặn rác, giới hạn body
                          ▼
     Spring Cloud Gateway   JWT RS256, rate limit, X-Trace-Id
                          │  định tuyến qua lb://  (Eureka)
           ┌──────────────┴───────────────┐
           ▼                              ▼
  java-core  (Java 21)            ai-service  (Python 3.11)
  ├ platform    tenant, user, auth  ├ orchestrator  LangGraph
  ├ engagement  conversation, WS    ├ rag           hybrid + rerank
  ├ sales       lead, deal, activity├ mcp_client    discover + call
  └ analytics   read model          ├ scoring       lead scoring
           │                        ├ clustering    K-Means
           │                        └ eval          harness
           │                              │
     Outbox ─────► Apache Kafka (ZooKeeper) ◄──┘
                          │
                          ▼
  PostgreSQL 16   RLS · pgvector HNSW              Redis 7
                          │
                          ▼   Model Context Protocol
                 mcp-server-mock          ← REPOSITORY RIÊNG
```

### Quyết định kiến trúc

Mỗi quyết định một file trong [`docs/adr/`](docs/adr/) — nguồn trực tiếp cho chương 3 báo cáo.

| # | Quyết định |
|---|---|
| [0001](docs/adr/0001-multi-tenant-isolation-rls.md) | Cô lập đa khách thuê bằng Row-Level Security |
| [0002](docs/adr/0002-ai-service-khong-truy-cap-db-truc-tiep.md) | ai-service không chạm DB nghiệp vụ, đi qua API nội bộ |
| [0003](docs/adr/0003-outbox-pattern-kafka.md) | Outbox Pattern trên Kafka |
| [0004](docs/adr/0004-service-discovery-eureka.md) | Eureka, gateway định tuyến qua `lb://` |
| [0005](docs/adr/0005-mcp-thay-adapter-rieng.md) | MCP thay adapter riêng cho từng khách |
| [0006](docs/adr/0006-hybrid-search-rrf-rerank.md) | Tìm kiếm lai + RRF + xếp hạng lại |
| [0007](docs/adr/0007-pgvector-thay-vector-db-rieng.md) | pgvector trong cùng cụm PostgreSQL |
| [0008](docs/adr/0008-web-dashboard-react-vite-thay-nextjs.md) | web-dashboard React + Vite (lệch so với kế hoạch) |
| [0009](docs/adr/0009-kafka-che-do-zookeeper-thay-kraft.md) | Kafka chế độ ZooKeeper (lệch so với kế hoạch) |
| [0010](docs/adr/0010-ai-service-app-src-layout.md) | ai-service `app/` src-layout (lệch so với kế hoạch) |

---

## Hai làn và ranh giới sở hữu

|  | **Track A** — Nền tảng và Nghiệp vụ | **Track B** — AI và Dữ liệu |
|---|---|---|
| Ngôn ngữ | Java 21, Spring Boot 3.3, TypeScript | Python 3.11, FastAPI |
| Mã nguồn | `java-core/` `gateway/` `eureka-server/` `web-dashboard/` `web-widget/` `loadtest/` | `ai-service/` `mcp-server-mock` (repo riêng) |
| Schema CSDL | `platform` `engagement` `sales` `analytics` | `knowledge` `ai` `integration` |
| Flyway | **dải V1xx** | **dải V2xx** |
| Kafka | sản xuất sự kiện nghiệp vụ | tiêu thụ, và sản xuất nhóm `ai` |
| Chương báo cáo | 3 (thiết kế, ERD), 4 (backend, giao diện), hiệu năng ở 5 | 2 (RAG, MCP), 3 (khối AI), 4 (AI), phần lớn 5 |

**Hai làn không bao giờ ghi vào dải migration của nhau.** Đây là cách tránh xung đột khi làm song song.

### Giao ước giữa hai làn — chốt trước 07/09

- [`docs/openapi/java-core-to-ai-service.yaml`](docs/openapi/) — ai-service gọi được gì
- [`docs/openapi/ai-service-to-java-core.yaml`](docs/openapi/) — java-core gọi được gì
- [`docs/events/`](docs/events/) — lược đồ 5 topic Kafka, có `event_version`

Sau khi chốt, mỗi bên tự dựng bản giả lập của bên kia và làm việc độc lập, không phải chờ nhau.

---

## Cấu trúc repository

```
├── docker-compose.yml      postgres+pgvector · redis · kafka+zookeeper · eureka
├── docs/
│   ├── adr/                mỗi quyết định kiến trúc một file → chương 3
│   ├── openapi/            hai đặc tả giao ước giữa hai làn
│   ├── events/             lược đồ sự kiện Kafka, có phiên bản
│   ├── threat-model.md
│   └── report/             bản thảo báo cáo, viết song song
│
│   ── TRACK A ──
├── eureka-server/
├── gateway/                config · filter · security · exception
├── java-core/              4 bounded context, mỗi context đủ tầng:
│   │                       controller · dto · entity · repository · service/impl
│   ├── platform/  engagement/  sales/  analytics/
│   ├── client/  config/  security/  common/
│   └── src/main/resources/db/migration/     Flyway, dải V1xx
├── web-dashboard/          React + Vite
├── web-widget/             Vite
├── loadtest/               k6
│
│   ── TRACK B ──
└── ai-service/             app/ src-layout (ADR-0010)
    ├── app/
    │   ├── api/            bề mặt HTTP có phiên bản
    │   ├── core/           config · logging · metrics · eureka
    │   ├── db/  schemas/  repositories/
    │   ├── domain/         orchestrator · rag · mcp_client · scoring · clustering
    │   ├── integrations/   java_core · llm · kafka
    │   └── workers/        consumer nền
    ├── migration/          Flyway, dải V2xx
    └── eval/
        ├── golden_set.jsonl      150 câu — tài sản giá trị nhất
        ├── adversarial.jsonl     60-80 kịch bản tấn công
        ├── configs/              mỗi cấu hình thí nghiệm một file
        └── reports/              CSV và HTML sinh tự động

mcp-server-mock/            REPOSITORY RIÊNG — cố ý tách để chứng minh
                            nó là hệ thống ngoài, không thuộc CRM
```

`mcp-server-mock` nằm ở `../mcp-server-mock/`, cạnh repo này.

---

## Mốc

| Mốc | Hạn |
|---|---|
| M0 — Chốt kênh tích hợp | 31/08 |
| M1 — Giao ước hợp đồng | 14/09 |
| M2 — Có doanh nghiệp pilot | 15/09 |
| M3 — Xương sống chạy | 28/09 |
| M4 — Bộ dữ liệu vàng hoàn tất | 12/10 |
| M5 — Recall@5 ≥ 0,80 | 26/10 |
| M6 — Vòng lặp AI khép kín | 09/11 |
| M7 — Đóng băng tính năng | 07/12 |
| Đóng băng code | 21/12 |
| Bảo vệ | 31/12 |

## Nhịp làm việc

- **Mỗi ngày** — đồng bộ 15 phút: hôm qua, hôm nay, đang bị chặn bởi ai.
- **Mỗi thứ Sáu** — ngày tích hợp: gỡ bản giả lập, ghép thật, chạy kịch bản đầu-cuối (2–3 giờ);
  quay video demo 3 phút; cập nhật sổ rủi ro.
- **Cuối mỗi sprint** — viết phần báo cáo tương ứng. Viết chương thiết kế **trong lúc thiết kế**,
  không phải sau khi code xong.
