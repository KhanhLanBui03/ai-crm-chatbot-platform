# CHANGELOG — module AI

Ghi theo phiên làm việc. Chỉ ghi thay đổi **có ảnh hưởng tới người khác**: đổi hợp đồng, đổi
cấu trúc, đổi ngưỡng, thêm/bớt phụ thuộc. Việc sửa lỗi nội bộ không cần vào đây.

Tiếng Việt. Ngày theo định dạng DD/MM/YYYY.

---

## 19/09/2026 — Tái cấu trúc theo Master Plan §3.9.2

### Đổi cấu trúc (ADR-0015, thay thế ADR-0010)

- `ai-service/app/` → `ai-service/src/`, bỏ một cấp `domain/`. 37 file `git mv`, giữ lịch sử.
- `ai-service/eval/` → `ai-service/tests/eval/`.
- `app/schemas/answer.py` → `src/ai/schemas.py` (§3.9.2: là **file**, không phải thư mục).
- Thêm `src/entrypoint.py` — một image hai vai trò `RUN_MODE=api|worker`, **ghim `workers=1`**.
- Thêm `src/ai/service.py` — facade duy nhất cho `api/` và `worker/`.
- **Mới: tầng suy luận `inference/`** — Dockerfile, `compose.inference.yml`, ba vai trò
  `embed`/`rerank`/`classify` chọn bằng `MODEL_ROLE`.
- Mới: `notebooks/` `artifacts/` `data/` `reports/eval/` `.github/workflows/ci.yml`.

### Đổi phụ thuộc — ảnh hưởng tới ai build image

- `requirements.txt` tách thành `requirements/{base,dev}.{in,txt}`.
- **Gỡ khỏi `ai-service`:** `torch` · `sentence-transformers` · `FlagEmbedding` ·
  `scikit-learn` (trực tiếp) · `ranx` · `matplotlib` → chuyển sang `notebooks/requirements.txt`.
- Thêm `redis`, `trafilatura`, `unidecode` vào `base.txt`.
- `inference/requirements/base.txt` mới: `onnxruntime` · `tokenizers` · `numpy`.

### Hai lỗi thật đã sửa

- **`.gitignore` nuốt file nguồn.** Mẫu `**/models/` (dành cho artifact ML) khớp luôn package
  Python `db/models/` — file biến mất khỏi Git mà không báo gì. Thu hẹp thành
  `artifacts/models/` + `inference/models/` + `notebooks/models/`.
- **Cổng chặn CI mâu thuẫn tài liệu.** Đoạn code §3.2 grep cả `scikit-learn`, nhưng §4.6 nói
  rõ `pyvi` (kéo theo sklearn) thuộc về ai-service. Chốt bản **3 gói** theo §1.6 + kế hoạch
  Ngày 4 + sheet Chỉ số nghiệm thu. Bù lại, CI thêm một kiểm mới: cấm `import sklearn` trong
  `src/`. Chi tiết: ADR-0015 mục 4.

### Chốt hai xung đột tài liệu mà kế hoạch Ngày 3 yêu cầu

| | Master Plan | **Chốt theo** |
|---|---|---|
| Số chiều vector | §4.2 → 768 | **1024** (UC019, `V203`) |
| Schema kho tri thức | `ai.chunks` | **`knowledge.knowledge_chunks`** (ERD, `V202`/`V203`) |

### Còn nợ

- Image `ai-service` **776 MB**, ngưỡng < 400 MB. Đường tối ưu đã biết (tách layer worker),
  giao cho Ngày 6. ADR-0015 mục Đánh đổi 6.
- Chưa chuyển sang Alembic dù §3.9.2 ghi vậy — giữ Flyway V2xx vì đó là cơ chế chống xung đột
  hai làn.
- **Chưa chốt:** bộ tên topic Kafka (8 theo §2.6 vs 5 `crm.*.v1` trong repo) · tên role runtime
  (`ai_service` vs `ai_app`) · bảng `ai.lead_features` chưa có migration nào tạo.
