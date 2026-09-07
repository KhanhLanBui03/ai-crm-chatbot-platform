# ADR-0010 — ai-service dùng `app/` src-layout, capability nằm trong `app/domain/`

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-20
- **Làn sở hữu:** Track B
- **Quan hệ:** thi hành [ADR-0002](0002-ai-service-khong-truy-cap-db-truc-tiep.md) ở mức cấu trúc mã nguồn

## Bối cảnh

Phụ lục A của kế hoạch đặt các capability của khối AI **ngay ở gốc** `ai-service/`:

```
ai-service/
├── orchestrator/   rag/   mcp_client/   scoring/   clustering/
├── migration/
└── eval/
```

Cây đó mô tả đúng **những năng lực** phải có, nhưng không nói gì về các tầng kỹ thuật mà một
dịch vụ FastAPI chạy thật vẫn cần: điểm vào ứng dụng, tầng HTTP có phiên bản, cấu hình, phiên
CSDL, DTO, truy cập dữ liệu, adapter ra ngoài, tác vụ nền. Nếu để nguyên, những thứ này sẽ
mọc lẫn vào trong các capability và ranh giới sẽ mờ dần.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| Giữ capability ở gốc, thêm `core/`, `api/`, `db/`… làm anh em cùng cấp | Khớp Phụ lục A 100%, không cần ADR này | Gốc repo rậm; không phân biệt được "mã phục vụ request" với "tài sản thí nghiệm"; import dài và dễ đụng tên với thư viện ngoài |
| **`app/` src-layout, capability vào `app/domain/`** (đã chọn) | Bố cục FastAPI production phổ biến; một gói gốc duy nhất nên import sạch và đóng gói được; tách bạch `app/` (phục vụ request) với `eval/` (thí nghiệm) và `migration/` (schema) | Cây không còn khớp **chữ** của Phụ lục A |
| Hexagonal đầy đủ (`domain/application/infrastructure/interfaces`) | Ranh giới chặt nhất | Quá nặng cho nhóm 2 người đang ở 145% quỹ thời gian; nhiều tầng gián tiếp mà chưa có nhu cầu |

## Quyết định

```
ai-service/
├── app/                     ← mã phục vụ request
│   ├── main.py              factory create_app() + lifespan
│   ├── api/{deps.py, v1/{router.py, endpoints/}}
│   ├── core/                config · logging · exceptions · metrics · eureka
│   ├── db/{session, base, models/}
│   ├── schemas/             Pydantic DTO — giao ước với java-core
│   ├── repositories/
│   ├── domain/              ← capability của Phụ lục A, nguyên vẹn
│   │   ├── orchestrator/  rag/{ingest,retrieve,rerank,generate}
│   │   ├── mcp_client/  scoring/  clustering/
│   ├── integrations/        java_core/ · llm/ · kafka/
│   └── workers/consumers/
├── migration/               Flyway V2xx — GIỮ NGUYÊN ở gốc
├── eval/                    harness thí nghiệm — GIỮ NGUYÊN ở gốc
└── tests/{unit,integration,e2e}/
```

**Tên và vai trò của mọi capability giữ nguyên**, chỉ đổi vị trí: từ `ai-service/rag/` thành
`ai-service/app/domain/rag/`. Không capability nào bị gộp, tách hay đổi tên.

## Lập luận

**`eval/` và `migration/` cố ý nằm ngoài `app/`.** Đây là phần có giá trị nhất của quyết định
này. `eval/` là harness thí nghiệm, `migration/` là schema — không cái nào phục vụ request.
Tách chúng ra khiến ranh giới "cái gì chạy trong sản phẩm, cái gì chỉ dùng để đo" trở thành
ranh giới thư mục thay vì một quy ước ghi trong đầu. `eval/` import ngược vào `app.domain.rag`
là bình thường và đúng chiều.

**Một gói gốc duy nhất.** Mọi thứ import qua `app.*` nên không có nguy cơ đụng tên với thư
viện ngoài (`rag`, `scoring`, `clustering` đều là tên rất dễ trùng trên PyPI), và
`pip install -e .` hoạt động đúng.

**Chiều phụ thuộc kiểm tra được bằng máy:**

```
api ──► domain ──► repositories ──► db
 │         │
 └─────────┴──► core, schemas, integrations
```

`app/domain/` **không được import** `app.api`. Nhờ vậy domain không biết mình đang chạy sau
HTTP hay sau một consumer Kafka — đó chính là điều kiện để `eval/` dùng lại được đường ống
RAG mà không cần dựng máy chủ HTTP. Luật này kiểm tra được bằng một lệnh `grep`, xem phần
Kiểm chứng.

## Đánh đổi

1. **Cây không khớp chữ của Phụ lục A.** Nếu hội đồng đối chiếu từng dòng thì sẽ thấy lệch.
   Giảm nhẹ bằng chính ADR này và bằng việc giữ nguyên tên mọi capability.
2. **Thêm một cấp thư mục** khi đi tới capability (`app/domain/rag/` thay vì `rag/`).
3. **Đường quay lại rẻ.** Muốn về đúng Phụ lục A chỉ cần nâng `app/domain/*` lên gốc và sửa
   `pyproject.toml` với `Dockerfile`. Không đụng logic.

## Hệ quả

| File | Thay đổi |
|---|---|
| `ai-service/Dockerfile` | `CMD` → `uvicorn app.main:app` |
| `ai-service/pyproject.toml` | `packages` tường minh → `[tool.setuptools.packages.find] include = ["app*", "eval*"]` |
| `docker-compose.yml` | Không đổi — healthcheck vẫn `/health` |

**`/health` và `/metrics` không bị đánh phiên bản.** Chúng gắn ở gốc ứng dụng, không nằm dưới
`/v1`, vì là bề mặt vận hành chứ không phải giao ước nghiệp vụ: Docker Compose và Prometheus
phải gọi được kể cả khi giao ước lên `v2`. Điều này khớp với
`docs/openapi/ai-service-to-java-core.yaml` vốn đã đặt `/health` và `/metrics` ở gốc.

## Kiểm chứng

- `python3.11 -m compileall -q app eval` → không lỗi cú pháp
- `grep -rn "from app.api\|import app.api" app/domain/` → **rỗng** (chiều phụ thuộc đúng)
- `/health` khớp healthcheck của `ai-service` trong `docker-compose.yml`
