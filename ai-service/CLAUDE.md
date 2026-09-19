# ai-service — quy ước tầng orchestration

Luật dùng chung của cả module AI ở [`../CLAUDE.md`](../CLAUDE.md). Quy ước code Python chi
tiết ở [`.claude/rules/ai-service.md`](../.claude/rules/ai-service.md). Bảng "đặt file mới ở
đâu" ở [`README.md`](README.md). **File này chỉ ghi phần riêng của tầng orchestration**, không
chép lại ba chỗ trên.

## Điều dễ sai nhất: `src` là package THẬT

Không phải quy ước src-layout. `src/entrypoint.py` gọi `"src.api.main:app"`, nên `src` phải
import được:

```toml
[tool.setuptools.packages.find]
where = ["."]        # KHÔNG phải ["src"]
include = ["src*"]
```

Đổi thành `where = ["src"]` là gãy `entrypoint.py` — và nó gãy lúc chạy container, không gãy
lúc build. Docker `WORKDIR /app` với mã ở `/app/src` cũng vì lý do này.

## Một image, hai vai trò — `RUN_MODE`

```bash
python -m src.entrypoint                  # RUN_MODE=api (mặc định), cổng 8000
RUN_MODE=worker python -m src.entrypoint  # Kafka consumer
```

**`workers=1` là ràng buộc kiến trúc, không phải tham số hiệu năng.** Ba lý do (§3.9.1):
`OMP_NUM_THREADS` là biến ở mức tiến trình · `lifespan` khởi động tài nguyên nền không nhân
bản được (nhiều consumer cùng group, nhiều lần đăng ký cùng `instance_id`) · HPA đếm pod chứ
không đếm tiến trình. **Scale bằng `replicas`, không thêm `--workers`, không dùng gunicorn.**

## Hai luật import — kiểm được bằng máy

```
api ──┐
      ├──► ai/service.py ──► rag · orchestrator · mcp_client · extraction · scoring
worker┘                  └──► db · events · telemetry · inference · integrations
```

1. `src/ai/` không import `src.api` hay `src.worker`.
2. `api/` và `worker/` không import chéo nhau — một image, hai vai trò **độc lập**.

Lệnh kiểm **phải neo vào đầu dòng**, nếu không nó tự khớp chính câu lệnh viết trong docstring
và báo vi phạm giả (đã vấp thật khi tái cấu trúc):

```bash
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.(api|worker)\b' src/ai/
```

CI chạy cả ba lệnh này (`.github/workflows/ci.yml`).

## `service.py` là facade duy nhất

`api/` và `worker/` chỉ gọi vào đây. Lý do không phải "cho gọn": hai vai trò không được import
chéo nhau, nhưng cả hai cần đúng những năng lực giống nhau — một lượt chat đến từ HTTP và một
hội thoại đóng đến từ Kafka chạy qua phần lớn cùng một đường ống. Facade là chỗ duy nhất giữ
được cả hai điều đó.

Hệ quả có lợi: `tests/eval/` chạy lại đúng đường ống RAG mà **không cần dựng máy chủ HTTP**.

## Về `scikit-learn` trong image này

`pip list` sẽ thấy `scikit-learn`. **Đây là có chủ ý**, không phải sót:

`pyvi` (tách từ tiếng Việt, dùng ở `src/ai/rag/tsquery.py` để dựng phrase query `<->`) khai
`Requires: scikit-learn, sklearn-crfsuite`. §4.6 nói rõ:

> *"pyvi... là thư viện tách từ THUẦN PYTHON, không phải model neural, nên nó nằm trong ai-api
> cùng với guardrails. Đây không phải ngoại lệ của §3.2: quy tắc là 'ai-api không nạp model
> ONNX', không phải 'ai-api không có logic ngôn ngữ nào'."*

Cổng chặn CI vì thế grep đúng **3 gói** `onnxruntime|torch|xgboost` (theo §1.6 + kế hoạch
Ngày 4), không phải 6 gói như đoạn code §3.2. Lý do đầy đủ: **ADR-0015 mục 4**.

**Luật đi kèm, CI kiểm:** không `import sklearn` trong `src/`. sklearn ở đây chỉ tồn tại như
phụ thuộc của bộ tách từ, không phải công cụ mô hình hoá.

## Ba chỗ cố ý lệch §3.9.2 (ADR-0015)

| Lệch | Vì sao |
|---|---|
| `migration/` (Flyway V2xx) thay vì `alembic/` | V2xx là cơ chế chống xung đột hai làn; `scripts/migrate-ai.sh` và `docs/erd-*.md` đều bám vào nó |
| `config.py` `exceptions.py` ở gốc `src/ai/` | §3.9.2 không có ô `core/`; hai file này dùng chung cho cả `api/` lẫn `worker/` |
| Thêm `integrations/` `scoring/` `clustering/` | `integrations/java_core/` là bề mặt ADR-0002 — giữ thành thư mục riêng làm ranh giới nhìn thấy được. `scoring/` có căn cứ trực tiếp ở §5.10.5 |

## Nợ kỹ thuật đã biết

- **Image 776 MB, ngưỡng < 400 MB.** `pymupdf`/`python-docx`/`trafilatura` chỉ chạy ở
  `RUN_MODE=worker` → tách layer được, giảm ~120 MB. Giao cho Ngày 6. ADR-0015 Đánh đổi 6.
- CI chỉ `::warning::` cho dung lượng, chưa `exit 1`. Đổi sau khi tách layer.

## Kiểm nhanh không cần cài phụ thuộc

```bash
python3.11 -m compileall -q src tests
python3.11 -c "import src, src.ai, src.worker"
ruff check src tests
```

Chưa bật tầng suy luận thì đặt `AI_MODE=mock` — trả dữ liệu giả có seed cố định (§3.4.1).
