# ADR-0015 — Cấu trúc `src/` và tách tầng suy luận theo Master Plan v8.0

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-09-19
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** **thay thế [ADR-0010](0010-ai-service-app-src-layout.md)** · thi hành
  [ADR-0002](0002-ai-service-khong-truy-cap-db-truc-tiep.md) ở mức cấu trúc mã nguồn ·
  giữ nguyên [ADR-0007](0007-pgvector-thay-vector-db-rieng.md)

## Bối cảnh

ADR-0010 (20/08/2026) chọn bố cục `app/` src-layout và **cố ý lệch** khỏi Phụ lục A của kế
hoạch gốc. Quyết định đó đúng với thông tin có lúc bấy giờ.

Master Plan v8.0 (06/09/2026) sau đó đổi một thứ mà ADR-0010 không thể lường trước: **tách
kiến trúc làm hai tầng**. `ai-service` trở thành tầng orchestration **không có ML runtime**,
còn toàn bộ model chuyển sang `inference/` — một image riêng. §3.9.2 của bản v8.0 đưa ra cây
thư mục cho cả hai tầng, và cây đó dùng `src/` chứ không dùng `app/`.

Đây không phải chuyện đổi tên thư mục. `src/entrypoint.py` ở §3.9.1 đọc biến `RUN_MODE` để một
image chạy được hai vai trò (`api` và `worker`) — `app/main.py` của ADR-0010 không có chỗ cho
khái niệm đó.

Ba thứ ép phải quyết lại:

1. Cây `app/` không có ô nào cho `entrypoint.py`, `service.py` (facade), `guardrails/`,
   `extraction/`, `telemetry/` hay `inference/`.
2. `ai-service/requirements.txt` đang chứa `torch`, `sentence-transformers`, `FlagEmbedding`,
   `scikit-learn` — đúng những gói mà cổng chặn CI §3.2 cấm trong image này.
3. Hình vẽ §3.9.2 **thiếu ô** cho bốn thứ đang tồn tại trong mã: `core/`, `integrations/`,
   `scoring/`, `clustering/` — dù §5.10.5 lại trích dẫn đường dẫn `src/ai/scoring/service.py`.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| Giữ `app/`, chỉ thêm `inference/` | Không phải sửa import nào; ADR-0010 còn hiệu lực | Cây lệch §3.9.2 ở mọi dòng; `entrypoint.py` §3.9.1 trỏ `src.api.main:app` sẽ sai; mọi trích dẫn đường dẫn trong Master Plan và kế hoạch 49 ngày đều phải dịch lại trong đầu |
| **`src/` theo §3.9.2, tách `inference/`** (đã chọn) | Khớp tài liệu chuẩn; một image hai vai trò chạy được; `ai-service` sạch ML runtime nên pod sẵn sàng 2–5 s thay vì 20–40 s | Thay thế một ADR mới 4 tuần tuổi; 40 file phải `git mv` |
| Tách `ai-service` thành hai repo | Ranh giới cứng nhất | Mất `docker compose up` một lệnh; hai repo cho một người làm là chi phí không đổi lại được gì |

## Quyết định

### 1. Bố cục `src/`, thay thế `app/`

```
ai-service/src/
├── entrypoint.py        RUN_MODE=api|worker · GHIM workers=1
├── api/                 FastAPI      ── không import worker/
├── worker/              Kafka        ── không import api/
└── ai/
    ├── service.py       FACADE DUY NHẤT cho cả hai vai trò trên
    ├── schemas.py       hợp đồng §2.5 — là FILE, không phải thư mục
    ├── inference/ orchestrator/ rag/ mcp_client/ extraction/ guardrails/
    ├── db/ events/ telemetry/
    └── scoring/ clustering/ integrations/        ← ba ô bổ sung, xem mục 3
```

**Tên và vai trò của mọi capability giữ nguyên** so với ADR-0010, chỉ đổi vị trí và bỏ một cấp
`domain/`. Không capability nào bị gộp, tách hay đổi tên.

`src` là **package thật**, không phải quy ước src-layout: nó có `__init__.py`, và `pyproject.toml`
khai `where = ["."]` + `include = ["src*"]`. Nếu dùng `where = ["src"]` thì `src.api.main:app`
trong `entrypoint.py` sẽ không import được.

### 2. Tách tầng suy luận `inference/`

Image `ai-service` **không có** `onnxruntime`, `torch`, `xgboost`, `scikit-learn`,
`transformers`. Ba nơi nhận các gói đó:

| Gói | Đi về | Vì sao |
|---|---|---|
| `onnxruntime` `tokenizers` `numpy` | `inference/requirements/base.txt` | chỉ *chạy* artifact `.onnx` |
| `torch` `sentence-transformers` `FlagEmbedding` `scikit-learn` `xgboost` `skl2onnx` `shap` | `notebooks/requirements.txt` | thư viện *huấn luyện*, chỉ chạy trên Kaggle |
| `ranx` `pytest` `ruff` `testcontainers` | `ai-service/requirements/dev.txt` | không vào image production |

### 3. Ba chỗ cố ý lệch khỏi hình vẽ §3.9.2

| Lệch | Quyết định | Lý do |
|---|---|---|
| §3.9.2 ghi `alembic/` | **Giữ `migration/` với Flyway dải V2xx** | V2xx là cơ chế chống xung đột giữa hai làn, ghi ở luật #1 của `.claude/CLAUDE.md`. `scripts/migrate-ai.sh` và `docs/erd-*.md` đều bám vào nó, và schema đang chạy thật đã có V201–V209. Đổi sang Alembic là đơn phương đổi giao ước liên làn — phải báo Track A trước, và không phải việc của lần tái cấu trúc này |
| §3.9.2 không có ô cho `config.py`/`exceptions.py` | Đặt ở gốc `src/ai/` | Dùng chung cho cả `api/` lẫn `worker/`, không thuộc capability nào |
| §3.9.2 không có `integrations/`, `scoring/`, `clustering/` | Tạo cả ba ở `src/ai/` | `integrations/java_core/` là bề mặt duy nhất chạm dữ liệu CRM (ADR-0002) — giữ nó thành một thư mục riêng làm ranh giới **nhìn thấy được**. `scoring/` có căn cứ trực tiếp: §5.10.5 trích dẫn `ai-service/src/ai/scoring/service.py`. `clustering/` cho UC038 |

`logging.py` và `metrics.py` vào `src/ai/telemetry/` (đúng ô §3.9.2 dành cho UC039/UC040);
`eureka.py` vào `src/api/` vì chỉ tiến trình API đăng ký Eureka, worker thì không.

### 4. Cổng chặn CI là bản **3 gói**, không phải bản 6 gói

Master Plan mâu thuẫn với chính nó ở đây:

| Nguồn | Danh sách grep |
|---|---|
| §1.6 — bảng 7 chỉ số nghiệm thu | `onnxruntime\|torch\|xgboost` |
| Kế hoạch 49 ngày, Ngày 4 | `onnxruntime\|torch\|xgboost` |
| Kế hoạch 49 ngày, sheet *Chỉ số nghiệm thu* | `onnxruntime\|torch\|xgboost` |
| **§3.2 — đoạn code YAML** | `onnxruntime\|torch\|xgboost\|transformers\|scikit-learn\|sentence-transformers` |

**Chốt theo bản 3 gói.** Ba nguồn độc lập ghi bản đó, và §4.6 giải thích tường minh vì sao
bản 6 gói sai trong trường hợp `scikit-learn`:

> *"pyvi chạy ở đâu? Nó là thư viện tách từ thuần Python, không phải model neural, nên nó nằm
> trong ai-api cùng với guardrails. Đây không phải ngoại lệ của §3.2: quy tắc là 'ai-api không
> nạp model ONNX', không phải 'ai-api không có logic ngôn ngữ nào'."*

`pyvi` khai `Requires: scikit-learn, sklearn-crfsuite`, nên bản 6 gói sẽ chặn đúng thứ §4.6
nói là được phép. `src/ai/rag/tsquery.py` cần `ViTokenizer.tokenize` để dựng phrase query `<->`;
gỡ pyvi nghĩa là đẩy tách từ sang tầng suy luận và cộng một lượt gọi mạng vào **mọi** truy vấn.

**Luật vẫn giữ:** không `import sklearn` trong `ai-service/src/` để suy luận. sklearn ở đây chỉ
tồn tại như phụ thuộc của bộ tách từ, không phải công cụ mô hình hoá.

### 5. Hai xung đột tài liệu mà kế hoạch 49 ngày (Ngày 3) bắt phải chốt

Repo đã chốt trên thực tế từ V202/V203 nhưng chưa ADR nào ghi lại. ADR này ghi:

| Xung đột | Master Plan | **Chốt theo** |
|---|---|---|
| Số chiều vector | §4.2 ghi `vector(768)` (theo e5-base) | **`vector(1024)`** — theo UC019 và `V203__knowledge_doan_va_vector.sql:17` đang chạy |
| Tên schema kho tri thức | `ai.documents` · `ai.chunks` | **`knowledge.knowledge_documents`** · **`knowledge.knowledge_chunks`** — theo ERD và V202/V203 |

Lý do chọn hiện trạng: chỉ mục HNSW và toàn bộ `docs/erd-*.md` (471 cột đã đối chiếu, 0 lệch)
đã bám vào hai quyết định này. Đổi số chiều nghĩa là dựng lại toàn bộ chỉ mục; đổi tên schema
nghĩa là sửa 24 file migration và chín sơ đồ ERD. Cái giá đó không đổi lại lợi ích nào.

Việc chọn model encoder vì thế bị ràng buộc: **model phải cho vector 1024 chiều**, hoặc phải
kèm một migration đổi kiểu cột và dựng lại chỉ mục.

## Lập luận

**Vì sao đáng thay thế một ADR mới 4 tuần tuổi.** ADR-0010 đã tự viết sẵn đường lùi ở mục
*Đánh đổi*: *"Muốn về đúng Phụ lục A chỉ cần nâng `app/domain/*` lên gốc và sửa `pyproject.toml`
với `Dockerfile`. Không đụng logic."* Đó chính xác là việc đã làm. Chi phí đúng như dự đoán:
40 file `git mv`, 9 dòng import, 0 dòng logic.

**Lợi ích thật không nằm ở tên thư mục mà ở việc `ai-service` sạch ML runtime.** Pod sẵn sàng
trong 2–5 giây thay vì 20–40 giây; HPA vì thế phản ứng kịp khi tải tăng đột ngột — scale lên
gần như vô nghĩa nếu pod mới mất 40 giây mới nhận được traffic. Và bề mặt gỡ lỗi tách bạch:
khi p95 xấu đi, `ai-service` chỉ có thể chậm vì *chờ*, tầng suy luận chỉ có thể chậm vì *tính*.

**`service.py` là facade vì `api/` và `worker/` không được import chéo nhau.** Nhưng cả hai
cần đúng những năng lực giống nhau — một lượt chat đến từ HTTP và một hội thoại đóng đến từ
Kafka chạy qua phần lớn cùng một đường ống. Facade là chỗ duy nhất giữ được cả hai điều đó.

**Chiều phụ thuộc vẫn kiểm được bằng máy**, như ADR-0010 đã đặt ra — nhưng lệnh kiểm phải neo
vào đầu dòng, nếu không nó tự khớp chính câu lệnh viết trong docstring và báo vi phạm giả:

```bash
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.(api|worker)\b' ai-service/src/ai/
```

## Đánh đổi

1. **Thay thế một ADR còn rất mới.** Hội đồng có thể hỏi vì sao đổi ý sau 4 tuần. Câu trả lời
   là kiến trúc đổi (một tầng → hai tầng), không phải sở thích đổi — và ADR-0010 vẫn nằm trong
   repo với lập luận nguyên vẹn để đối chiếu.

2. **Cây `ai-service` không khớp §3.9.2 ở ba chỗ** (mục 3 ở trên). Ai đối chiếu từng dòng sẽ
   thấy lệch; giảm nhẹ bằng chính ADR này và bằng ghi chú ngay trong `ai-service/README.md`.

3. **`src` là package thật trái với quy ước src-layout phổ biến.** Người quen Python sẽ phản xạ
   viết `where = ["src"]` và làm gãy `entrypoint.py`. Đã ghi cảnh báo ở `pyproject.toml`,
   `README.md` và `.claude/rules/ai-service.md` — ba chỗ, vì đây là cái bẫy dễ vấp nhất.

4. **`tests/eval/` giờ nằm trong `tests/`.** ADR-0010 cố ý để `eval/` ngoài `app/` để ranh giới
   "chạy trong sản phẩm" vs "chỉ dùng để đo" là ranh giới thư mục. Ranh giới đó vẫn còn, chỉ
   chuyển thành `src/` vs `tests/` — nhưng nhìn kém rõ hơn một chút so với hai thư mục anh em
   ở gốc.

5. **Chưa chuyển sang Alembic** dù §3.9.2 ghi vậy. Nợ này còn đó và sẽ phải trả nếu Track A
   đồng ý bỏ cơ chế V1xx/V2xx.

6. **Image `ai-service` đo được 776 MB, vượt ngưỡng < 400 MB của §3.2.3.** Đây là đánh đổi
   phải nói thẳng: con số 400 MB trong Master Plan được tính cho một image chỉ có FastAPI +
   LangGraph + driver, nhưng §4.6 lại đặt `pyvi` vào đây và §6.3 đặt bộ phân tích tài liệu
   (`pymupdf`, `python-docx`, `trafilatura`) vào đây. Ba thứ đó cộng lại:

   | Gói | MB | Vì sao có mặt |
   |---|---|---|
   | scipy + numpy + sklearn | 252 | phụ thuộc gián tiếp của `pyvi` (§4.6) |
   | pymupdf | 63 | phân tích PDF, UC018/UC019 |
   | babel + zstandard | 55 | phụ thuộc gián tiếp của `trafilatura` |

   Lợi ích kiến trúc thật (pod sẵn sàng 2–5 s, HPA phản ứng kịp, bề mặt gỡ lỗi tách bạch)
   **vẫn đạt được** vì chúng đến từ việc không nạp model, không phải từ con số dung lượng.

   Đường tối ưu đã biết: `pymupdf`/`python-docx`/`trafilatura` chỉ chạy ở `RUN_MODE=worker`,
   tách được thành một layer riêng để image API giảm ~120 MB. **Chưa làm ở bước dựng khung** —
   giao cho Ngày 6 ("Đệm + Ổn định hoá", kế hoạch 49 ngày ghi rõ mục tiêu đo dung lượng image).

## Hệ quả

| File | Thay đổi |
|---|---|
| `ai-service/pyproject.toml` | `include = ["src*"]`, `where = ["."]`, `pythonpath = ["."]`, `known-first-party = ["src"]` |
| `ai-service/Dockerfile` | `CMD ["python","-m","src.entrypoint"]`; chỉ `COPY requirements/base.txt`; bỏ `build-essential` |
| `ai-service/requirements.txt` | → `requirements/{base,dev}.{in,txt}`; gỡ 4 gói ML runtime |
| `docker-compose.yml` | thêm `RUN_MODE: api`, `AI_MODE: ${AI_MODE:-mock}` và ba biến URL của tầng suy luận |
| `.gitignore` | `**/models/` → `artifacts/models/` + `inference/models/` + `notebooks/models/` — mẫu cũ nuốt luôn package Python `src/ai/db/models/` |
| `.claude/rules/*.md` · `.claude/CLAUDE.md` | cập nhật `paths` và mọi đường dẫn `app/` |
| `docs/threat-model.md` | `ai-service/eval/adversarial.jsonl` → `ai-service/tests/eval/adversarial.jsonl` |
| Mới | `inference/` · `notebooks/` · `artifacts/` · `data/` · `reports/eval/` |

`/health` và `/metrics` **không đổi** — healthcheck của Compose và Prometheus vẫn gọi được.

## Kiểm chứng

```bash
cd ai-service
python3.11 -m compileall -q src tests
python3.11 -c "import src, src.ai, src.worker"
ruff check src tests

# Chiều phụ thuộc — cả ba lệnh phải RỖNG
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.(api|worker)\b' src/ai/
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.worker\b'       src/api/
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.api\b'          src/worker/

# Cổng chặn ML runtime §3.2 — phải RỖNG
docker build -t ai-service:ci . && \
docker run --rm ai-service:ci pip list --format=freeze \
  | grep -Ei "^(onnxruntime|torch|xgboost|transformers|scikit-learn)"

# Lịch sử Git giữ nguyên — phải thấy R (rename), không thấy cặp A+D
git log --follow --oneline -- ai-service/src/api/main.py
```
