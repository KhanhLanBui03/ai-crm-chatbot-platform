# Kế hoạch 21 ngày — Dev A · Kho tri thức & Trả lời

> **8 Use Case:** UC018 · UC019 · UC020 · UC023 · UC025 · UC026 · UC027 · UC041
> **Kiêm:** hạ tầng CSDL, RLS, model nhúng, hybrid search, 4 node `guard`/`retrieve`/`generate`/`postguard`,
> eval harness, benchmark, triển khai, load test.
> **Lịch:** Ngày 1 = T2 21/09/2026 → Ngày 21 = CN 11/10/2026.

**Nguồn sự thật là `docs/Ke-hoach-21-ngay-Module-AI-CRM.xlsx`.** File này chỉ là bản lọc sẵn
phần của Dev A để mở cạnh code. **Số nào lệch thì xlsx đúng, file này sai** — sửa file này.

Thứ tự ưu tiên khi tài liệu mâu thuẫn: `repo` > `docs/adr/` > Master Plan > xlsx > file này.

---

## ⚠️ Lệch lịch — đọc trước khi bắt đầu

Hôm nay là **22/09**, theo lịch gốc đó là **Ngày 2**, nhưng phần việc Ngày 1 chưa làm xong.
Đã chốt: **giữ nguyên hạn 11/10, không dời lịch.**

→ **Hôm nay gánh: phần còn lại của Ngày 1 + toàn bộ Ngày 2.** Từ Ngày 3 (23/09) về đúng nhịp.

Tin tốt: cột *Điểm xuất phát* của xlsx soạn ngày 20/09 và đã cũ. Kiểm lại thực tế:

| Hạng mục | xlsx ghi | Thực tế 22/09 |
|---|---|---|
| Flyway V201–V209 | "chưa từng chạy thật" | ✅ **đã chạy** — container chỉ đang tắt, bật lại là có |
| `ai-service/.env` | không nhắc | ❌ **chưa tồn tại** — bẫy sẽ nổ ngay khi viết `session.py` |
| `tests/test_*.py` | 0 test | ❌ vẫn 0 |
| `tests/eval/*.jsonl` | 0 dòng | ❌ vẫn 0 dòng |
| Đề xuất 3 cột `sales.lead_scores` | soạn 19/09, chưa gửi | ❌ **vẫn chưa gửi** |
| Docker | — | daemon UP, 0 container chạy |

Nên phần Ngày 1 còn lại **nhẹ hơn xlsx mô tả**: không phải chạy lại migration, chỉ cần bật
container → xác minh lại → `.env` → `dev.txt` → `test_rls.py` → job CI → gửi Track A.

---

## Quy ước: ai gõ dòng code nào

Đây là đồ án tốt nghiệp. Tiêu chí phân tầng không phải "khó hay dễ" mà là **hội đồng có hỏi
được không** và **sai thì có âm thầm làm hỏng số liệu không**.

| Nhãn | Nghĩa | Tiêu chí |
|---|---|---|
| 🖐 **TỰ GÕ** | Bạn viết từ đầu. AI được phép giải thích khái niệm, gợi ý hướng, review **sau khi** bạn viết xong — không dán lời giải | Code mang một **quyết định thiết kế**, hoặc là **bằng chứng của một chỉ số nghiệm thu** |
| 🤖 **AI SINH → VERIFY** | AI sinh bản đầu, bạn **đọc từng dòng**, sửa cho khớp bố cục repo rồi mới commit | Lặp lại, bám thư viện, hoặc là giàn giáo. Sai thì lộ ra ngay ở test/CI |
| 📖 **ĐỌC HIỂU** | Không viết, nhưng phải hiểu — file đã có sẵn trong repo mà bạn sẽ đụng tới | V201–V209, `config.py`, `deps.py`, `ci.yml` |

> **Luật:** mọi dòng gắn 🤖 mà bạn **không giải thích được** thì coi như **chưa xong** — chưa
> được tick ô đó. Ô 🤖 nào cũng kèm sẵn *điểm phải verify*: soi đúng chỗ đó, đừng đọc lướt.

### Mười thứ bắt buộc 🖐 TỰ GÕ trong cả 21 ngày

Đây là khối lượng lõi thật sự. Mọi thứ khác là phụ trợ quanh mười thứ này:

| # | Thứ | Ngày | Vì sao không được nhờ AI |
|---|---|---|---|
| 1 | `test_rls.py` — 3 ca | N1 | Bằng chứng của chỉ số "rò rỉ tenant = 0" |
| 2 | `SET LOCAL app.tenant_id` trong `db/session.py` | N2 | Trung tâm của cô lập tenant; bẫy connection pool |
| 3 | `normalize_vi` — một hàm cho cả hai đầu | N4 | Hai hàm khác nhau = recall tụt mà không có exception |
| 4 | Hàm chia đoạn giữ heading + số trang | N4 | Không có heading thì UC023 không trích dẫn được |
| 5 | Câu SQL hybrid + RRF k=60 | N6 | Quyết định kiến trúc lớn nhất của phần truy hồi (ADR-0006) |
| 6 | `needs_rerank()` / `AMBIGUITY_GAP` | N8 | Cổng quyết định bật/tắt rerank, ghi vào ADR |
| 7 | `postguard` — groundedness vs retrieval_top_score | N9 | Hai đại lượng khác nhau; nhầm là hỏng cả chương đánh giá |
| 8 | Circuit breaker 3 trạng thái | N9 | Chịu lỗi LLM — hội đồng chắc chắn hỏi |
| 9 | `search_or_abstain` — 4 lý do từ chối | N10 | Toàn bộ UC025 nằm ở đây |
| 10 | Khoá semantic cache có `tenant_id` | N16 | Thiếu `tenant_id` = rò rỉ giữa doanh nghiệp, 1 trong 7 chỉ số §1.6 |

---

## 8 Use Case của Dev A

| UC | Tên | Ngày | Phụ thuộc trước đó |
|---|---|---|---|
| UC018 | Tải lên tài liệu tri thức | N3 | CSDL chạy thật (N1) |
| UC019 | Nạp và lập chỉ mục tài liệu | N4–5 | UC018, encoder ONNX (N2) |
| UC020 | Quản lý kho tri thức | N11 | UC019 |
| UC023 | Trả lời dựa trên tri thức doanh nghiệp | N9 | UC019, Hybrid (N6), UC022 của Dev B, LangGraph (N8) |
| UC025 | Từ chối khi không đủ căn cứ | N10 | UC023 |
| UC026 | Tóm tắt nội dung hội thoại | N12 | Worker Kafka (N5) |
| UC027 | Đánh giá chất lượng câu trả lời | N10 | UC023, UC039 của Dev B |
| UC041 | Xử lý yêu cầu xoá dữ liệu cá nhân | N12 | UC019 (chunk), UC030 của Dev B (đặc trưng lead) |

**Mức hoàn thành tối thiểu mỗi UC:** endpoint hoặc worker chạy được + 1 test chứng minh luồng
chính + 1 con số minh chứng. Đạt ba thứ đó là UC được tính. **Đừng làm sâu hơn mức này cho tới
khi cả 17 UC đều đạt.**

---

## Ranh giới file — cái gì của tôi, cái gì phải hỏi

**Dev A sở hữu, sửa thoải mái:**

```
ai-service/src/ai/db/**                      session.py, pool, models, repositories
ai-service/src/ai/rag/**                     ingest, retrieve, rerank, generate
ai-service/migration/**                      BẮT ĐẦU TỪ V210 — V201–V209 đã chạy, KHÔNG sửa
ai-service/src/ai/orchestrator/nodes/{guard,retrieve,generate,postguard}.py
ai-service/tests/eval/**                     bộ vàng, eval harness, configs
inference/src/roles/{embed,rerank}.py
```

**CHUNG — cần Dev B duyệt trước khi merge:**

```
ai-service/src/ai/service.py                 FACADE DUY NHẤT
ai-service/src/ai/orchestrator/{graph.py,state.py}   AgentState chốt chung ở N8
ai-service/src/ai/schemas.py                 là MỘT FILE, không phải thư mục (ADR-0015)
docs/openapi/**  docs/events/**  scripts/create-topics.sh
```

**KHÔNG ĐƯỢC SỬA:**

```
java-core/ gateway/ eureka-server/ web-dashboard/ web-widget/ loadtest/   ← Track A
data/intent_test_human.jsonl · bộ vàng đã đóng băng · artifacts/DATA_HASHES.txt
```

Hai file cuối là **tập test đóng băng và sổ hash**. Sửa được chúng thì mọi con số macro-F1 và
recall@5 trong báo cáo mất ý nghĩa.

---

## Sáu luật không bao giờ vi phạm

1. **`tenant_id` LUÔN từ ngữ cảnh đã xác thực** — header `X-Tenant-Id` do gateway gắn
   (`src/api/deps.py`). Không bao giờ từ body/query/path. Thiếu thì ném lỗi ngay.
2. **AI không ghi bảng nghiệp vụ CRM.** Chỉ đọc qua REST hoặc phát sự kiện Kafka (ADR-0002).
3. **`SET LOCAL app.tenant_id` trong CÙNG transaction** với truy vấn, ngay sau `pool.acquire()`.
   Runtime dùng role `ai_app` — **không phải** chủ bảng (chủ bảng bypass RLS kể cả khi `FORCE`).
4. **Mọi truy vấn vector lọc `tenant_id` ngay trong truy vấn** (ADR-0007, bề mặt T6).
5. **`ai-service` không nạp model.** `pip list | grep -E "onnxruntime|torch|xgboost"` phải RỖNG.
6. **Contract-first.** Sửa `docs/openapi/` hay `docs/events/` là đơn phương đổi hợp đồng — báo
   Dev B và Track A trước.

## Ba cái bẫy đã biết của repo này

- **RLS × connection pool:** `SET` không có `LOCAL` sẽ **dính lại trên kết nối** và rò sang
  request của tenant khác. Luôn `SET LOCAL`, luôn trong transaction.
- **Eureka:** FastAPI không tự đăng ký, và phải **huỷ đăng ký lúc tắt** — quên thì Eureka định
  tuyến tới tiến trình chết khoảng 90 giây.
- **Kafka hai listener:** `kafka:9092` từ **trong** mạng Docker · `localhost:29092` từ **máy chủ**.
  Dùng nhầm thì client treo rồi timeout mà **không có thông báo nào** chỉ ra nguyên nhân.

## Thứ tự cắt khi trượt lịch — cắt theo thứ tự này, không cắt bừa

1. Rerank cross-encoder (đã có feature flag, mặc định tắt)
2. Semantic cache (N16) — tối ưu, không phải use case
3. Chiều sâu UC038 (của Dev B)
4. Soak 1 giờ (N19)

**KHÔNG cắt:** nguyên một use case · giảm image xuống < 400 MB (N16, cổng CI đã `exit 1`) ·
tập test đóng băng · test cách ly tenant trong CI · bộ vàng ≥ 80 cặp.

Một ngày trượt phải xử lý bằng **cắt độ sâu ngay trong ngày**, không được lùi sang ngày sau —
vì ngày sau đã đầy.

---
---

# TUẦN 1 — Nền móng, kho tri thức, truy hồi

## Ngày 1 — T2 21/09 — Dựng CSDL thật từ V201–V209 + test cách ly tenant đầu tiên

> **Mục tiêu:** chứng minh bằng test rằng tenant A không đọc được dữ liệu của tenant B.

**Điều kiện vào:** Docker daemon chạy. `.env` ở gốc repo đã có (`POSTGRES_HOST_PORT=5433`,
`KAFKA_HOST_PORT=29092`).

**Việc:**

- [ ] 🤖 Tạo `ai-service/.env` — *verify: `DB_HOST=localhost` và `DB_PORT=5433`, **không phải**
      `postgres:5432`. `config.py:19` khai `env_file=".env"` tính theo CWD; chạy từ `ai-service/`
      thì không thấy `.env` ở gốc repo, rơi về mặc định `db_host='postgres'` là tên DNS trong
      mạng Docker, không phân giải được từ máy chủ.*
      Khoá cần có: `DB_HOST` `DB_PORT` `DB_NAME=thesis_crm` `DB_USERNAME=ai_app` `DB_PASSWORD`
      `KAFKA_BOOTSTRAP=localhost:29092` `ANTHROPIC_API_KEY=` (để rỗng, cần trước N9).
- [ ] 📖 `docker compose up -d postgres redis kafka` → **cả 4 container phải healthy**
      (kéo theo zookeeper). Kiểm bằng `docker compose ps`.
- [ ] 📖 Xác minh migration đã chạy (KHÔNG chạy lại): `SELECT version, success FROM
      knowledge.flyway_schema_history_ai;` → đủ **9 dòng V201–V209**, `success = t`.
      Nếu rỗng thì mới chạy `bash scripts/migrate-ai.sh`.
- [ ] 📖 `\dt knowledge.* ai.* integration.*` → đủ **6 bảng**. `\di` → đủ chỉ mục của V202–V209.
- [ ] 📖 Đọc `migration/V206__grants_cho_ai_app.sql` và `V207__enable_rls.sql` — hiểu policy
      `tenant_isolation` dùng `USING` + `WITH CHECK` qua hàm `ai.current_tenant()`.
- [ ] 📖 Mở `ai-service/scripts/create_hnsw_index.sql` xác nhận **cú pháp đúng**. **CHƯA CHẠY** —
      `CONCURRENTLY` phải chạy sau khi đã có dữ liệu thật (Ngày 5).
- [ ] 🤖 `pip install -r requirements/dev.txt` trong venv — *verify: `testcontainers[postgres,kafka]`
      cài được (`dev.txt:9`); `pip list | grep -E "onnxruntime|torch|xgboost"` vẫn **rỗng***.
- [ ] 🤖 `tests/conftest.py` + fixture testcontainers Postgres — *verify: fixture kết nối bằng
      role **`ai_app`**, không phải `crm_owner`. Đây là chỗ dễ sai nhất và sai thì cả 3 ca dưới
      đều xanh giả.*
- [ ] 🖐 **`tests/integration/test_rls.py` — ĐỦ BA CA, tự gõ:**
      **(a)** tenant A đọc chunk của B → trả **RỖNG**.
      **(b)** `pool.acquire()` mà **KHÔNG** `SET LOCAL app.tenant_id` → ném **SQLSTATE 42501**,
      không phải trả rỗng. *(Sửa 24/09: dòng cũ ghi "trả RỖNG" là sai so với repo —
      `ai.current_tenant()` ở [V201:42-53] cố ý `RAISE EXCEPTION ... ERRCODE = '42501'`, lý do
      ghi ngay trong comment: "Trả NULL để lặng lẽ ra rỗng còn tệ hơn: danh sách rỗng trông y
      hệt 'chưa có dữ liệu'". Vẫn là fail-closed, chỉ khác ở chỗ nó **ồn ào** thay vì im lặng.)*
      **(c)** `SELECT current_user` → trả **`ai_app`**, không phải `crm_owner`.
- [ ] 🤖 Thêm job test RLS vào `.github/workflows/ci.yml` dùng testcontainers — *verify: job
      chạy trên PR, và cố tình làm hỏng ca (b) thì CI phải **đỏ**. Job xanh mà không bao giờ đỏ
      được là job vô dụng.*
- [ ] 🖐 **GỬI TRACK A HÔM NAY:** `docs/contracts/de-xuat-track-a-lead-scores-outcome.md`
      (3 cột `rule_score` / `outcome` / `outcome_at`). Việc 5 phút.
      ⚠️ *xlsx lệch: sheet Kế hoạch giao Dev A, sheet Chỉ số nghiệm thu dòng 15 ghi Dev B.
      Một trong hai gửi, **đừng để rơi** — Ngày 9 UC030 của Dev B chặn ở đây.*

**File sẽ đụng:** `ai-service/.env` (không commit) · `ai-service/tests/conftest.py` ·
`ai-service/tests/integration/test_rls.py` · `.github/workflows/ci.yml`

**Chạm Dev B:** Sáng ngồi cùng chốt **4 mâu thuẫn hợp đồng → ADR-0017** (tên endpoint · bộ topic
Kafka · chỗ đặt bộ vàng · cỡ tập test 200). Cả hai đều phụ thuộc.
**Cần nhận:** tên endpoint đã chốt — mình viết route đầu tiên ở **Ngày 3**.
**Dự phòng:** Dev B chưa chốt xong trong ngày → mình cứ theo `/v1/ai/**` (đề xuất của §2.5) và
ghi nợ, đừng dừng.

**Phải giải thích được:**
- Vì sao ca (b) quan trọng hơn ca (a)? *(Gợi ý: ca (a) chứng minh policy chạy; ca (b) chứng minh
  khi lập trình viên **quên** thì hệ thống fail-closed chứ không mở toang.)*
- `FORCE ROW LEVEL SECURITY` khác `ENABLE` ở chỗ nào, và vì sao vẫn phải tránh `crm_owner`?

**Cổng ra (DoD):** `test_rls.py` **3/3 ca XANH trong CI**.
🚫 **Không xanh thì không được sang Ngày 2.**

**Minh chứng báo cáo:** ảnh chụp `flyway_schema_history_ai` đủ 9 dòng · danh sách 6 bảng + chỉ mục ·
`test_rls.py` 3/3 xanh trong CI · ảnh chụp `SELECT current_user` = `ai_app` · tin nhắn đã gửi
đề xuất 3 cột cho Track A kèm dấu thời gian.

---

## Ngày 2 — T3 22/09 — Tầng truy cập CSDL có RLS + export encoder 1024 chiều sang ONNX INT8

> **Mục tiêu:** có `session.py` đúng luật RLS, và có artifact `.onnx` đầu tiên qua được cổng parity.

**Điều kiện vào:** `test_rls.py` 3/3 xanh. Nếu chưa → làm nốt Ngày 1 trước, cắt phần R&D xuống
chỉ chọn model + export, dời đo parity sang sáng Ngày 3.

**Việc — phần [PRODUCTION]:**

- [ ] 🖐 **`src/ai/db/session.py` — tự gõ.** Pool **psycopg3 async**; `SET LOCAL app.tenant_id` đặt
      **NGAY SAU `pool.acquire()`** và trong **CÙNG transaction** với truy vấn. Kết nối bằng
      role `ai_app`.
      *Đây là bẫy connection pool: `SET` không có `LOCAL` sẽ dính lại trên kết nối và rò sang
      request của tenant khác.*
      *(Sửa 24/09: dòng cũ ghi `asyncpg` là sai so với repo — `requirements/base.txt:59` đã có
      `psycopg[binary,pool]>=3.2` + `pgvector>=0.3.6`, và image đang nợ 776/400 MB nên không thêm
      driver thứ hai chỉ để khớp một dòng chữ. Không cần ADR mới: đây là xác nhận theo repo, không
      phải đổi công nghệ. `tests/conftest.py` đã dựng trên psycopg3.)*
- [ ] 🤖 Repository cho `knowledge_documents` và `knowledge_chunks` — *verify: **mọi** truy vấn
      vector lọc `tenant_id` **ngay trong câu SQL**, không lọc ở Python (ADR-0007, bề mặt T6).
      Soi từng hàm; AI rất hay sinh ra `WHERE` thiếu `tenant_id` rồi lọc lại ở tầng Python.*
- [ ] 🖐 Chạy lại `test_rls.py` **sau khi** thêm `session.py` — phải vẫn xanh. Nếu đỏ thì
      `session.py` sai, không phải test sai.
- [ ] 🖐 Một lượt `INSERT` **thật** vào `knowledge_chunks` với vector 1024 chiều — sai chiều là
      lỗi ngay ở tầng CSDL (V203 dòng 17 khai `vector(1024)`).

**Việc — phần [R&D] (Kaggle, chạy CPU cũng được):**

- [ ] 🖐 Chọn encoder cho ra **ĐÚNG 1024 chiều** — ràng buộc **cứng**, không đổi được vì cột đã
      là `vector(1024)`. `config.py` đang để mặc định `BAAI/bge-m3` (1024) — xác nhận lại.
- [ ] 🤖 Notebook export ONNX + lượng tử hoá **INT8 động per-channel** — *verify: `torch` chỉ
      nằm trong notebook và `notebooks/requirements.txt`, **không** lọt vào
      `ai-service/requirements/base.txt`. Chạy lại cổng chặn CI cho chắc.*
- [ ] 🖐 **CỔNG PARITY — tự gõ script đo:** cosine giữa fp32 và INT8 trên **500 câu** phải
      **≥ 0,995**. 🚫 Không đạt thì **dừng, đổi model**, không đi tiếp.
- [ ] 🤖 Ghi dòng đầu tiên thật vào `artifacts/MODEL_REGISTRY.md` kèm **sha256** — *verify: hash
      khớp file `.onnx` thật, không phải hash chép tay.*

**File sẽ đụng:** `src/ai/db/session.py` · `src/ai/db/models/` · `src/ai/db/repositories/` ·
`notebooks/06_export_onnx.ipynb` · `artifacts/MODEL_REGISTRY.md`

**Chạm Dev B:** 🤝 **BUỔI CHUNG ~3 GIỜ — gõ tay 200 câu hỏi thật** theo 7 nhánh ý định, có cả câu
**KHÔNG DẤU**, viết tắt, sai chính tả. Đây là tài sản giá trị nhất của phần thực nghiệm.
Đóng băng `data/intent_test_human.jsonl` + ghi sha256 vào `artifacts/DATA_HASHES.txt`.
**Từ lúc đóng băng, file này KHÔNG BAO GIỜ được sửa để cải thiện điểm.**

**Phải giải thích được:**
- Vì sao `SET LOCAL` chứ không phải `SET`? Nếu bỏ `LOCAL` thì hỏng ở đâu, và vì sao test vẫn có
  thể xanh?
- Vì sao runtime dùng `ai_app` mà không dùng `crm_owner`, dù `crm_owner` cũng bị `FORCE RLS`?
- Lượng tử hoá INT8 **per-channel** khác **per-tensor** ở chỗ nào, và vì sao ngưỡng là 0,995?

**Cổng ra (DoD):** parity cosine **≥ 0,995** · `INSERT` vector 1024 chiều thành công ·
`test_rls.py` vẫn xanh · tập test 200 mẫu đã đóng băng + hash trong Git.

**Minh chứng báo cáo:** bảng + histogram parity INT8 vs fp32 · xác nhận số chiều = 1024 bằng
`INSERT` thật · `MODEL_REGISTRY.md` có dòng đầu tiên với sha256.

---

## Ngày 3 — T4 23/09 — UC018 Tải lên tài liệu tri thức

> **Mục tiêu:** route đầu tiên của cả dự án chạy được, và 5 mã lỗi tách bạch.

**Điều kiện vào:** tên endpoint đã chốt (Ngày 1). Chưa chốt → theo `/v1/ai/**` và ghi nợ.

**Việc:**

- [ ] 🖐 **Bộ 20 tệp mẫu** PDF/DOCX/TXT/MD/HTML + **5 tệp lỗi** (quá 20 MB, sai MIME, PDF scan
      không trích được text).
      ⚠️ *Đây cũng là nguồn của bộ vàng Ngày 6 — chọn tài liệu có **nội dung nghiệp vụ thật**
      (bảng giá, chính sách bảo hành, quy trình đổi trả), không lấy văn bản ngẫu nhiên.*
      Kiểm kỹ: **không chứa dữ liệu cá nhân** trước khi commit (Nghị định 13).
- [ ] 🤖 Route `POST` tải lên theo tên đã chốt — *verify: `tenant_id` lấy từ `get_tenant_id`
      của `src/api/deps.py` (header `X-Tenant-Id`), **không** từ body/query/path.*
- [ ] 🤖 Kiểm phần mở rộng + dung lượng + hạn mức `max_documents` của gói — *verify: ngưỡng
      **cảnh báo 80%** và **chặn 100%** là hai nhánh khác nhau, không gộp.*
- [ ] 🤖 Ghi bản ghi `PENDING` — *verify: `title` 3–300 ký tự, `description` ≤ 500,
      `language` ∈ {`vi`,`en`}; ràng buộc `ck_doc_failed` của V202 không bị vi phạm.*
- [ ] 🖐 **Lưu tệp theo đường dẫn CÓ CHỨA `tenant_id`** — cô lập ngay ở tầng kho lưu trữ chứ
      không chỉ ở truy vấn.
- [ ] 🖐 Trùng tiêu đề → **tăng `version`**, không ghi đè (uq theo `(tenant, title, version)`).
- [ ] 🤖 Trả `202` + `job_id`; phát sự kiện với **khoá phân vùng = `tenant_id`** — *verify: khoá
      phân vùng đúng là `tenant_id`, nếu không thì thứ tự sự kiện trong một tenant không đảm bảo.*
- [ ] 🖐 **Test 5 mã lỗi tách bạch:** `413` (tệp > 20 MB) · `415` (sai định dạng) · `409` (chạm
      hạn mức gói) · `422` · `PARSE_NO_TEXT_EXTRACTED`.
      *Đây là điểm 1 trong "Mười một điểm cần chốt" của đặc tả UC.*

**File sẽ đụng:** `src/api/v1/router.py` · `src/api/v1/endpoints/` · `src/ai/rag/ingest/` ·
`src/ai/service.py` (facade — Dev B duyệt) · `data/` (tệp mẫu)

**Chạm Dev B:** 🤝 **Gán nhãn chéo tập test 200 mẫu** — mỗi người gán **ĐỘC LẬP** rồi mới đối
chiếu, đo **Cohen's kappa**, ngồi lại giải quyết mọi ca bất đồng.
*Bất đồng nhãn ở đây biến thành sai số hệ thống ở MỌI chỉ số về sau.*
**Phải giao:** không có. **Cần nhận:** không có.

**Phải giải thích được:**
- Vì sao đường dẫn lưu trữ phải chứa `tenant_id` khi truy vấn đã lọc `tenant_id` rồi?
- `409` và `422` khác nhau thế nào trong UC018? Vì sao không gộp làm một?

**Cổng ra (DoD):** 25/25 tệp mẫu cho ra **đúng mã HTTP** mong đợi.

**Minh chứng báo cáo:** bảng 5 ca lỗi × mã HTTP (25/25 tệp) · ảnh chụp đường dẫn lưu trữ có
`tenant_id` · ngưỡng cảnh báo 80% và chặn 100% · 20 tệp mẫu đã vào repo.

---

## Ngày 4 — T5 24/09 — UC019 (1/2) Phân tích cú pháp, chuẩn hoá tiếng Việt, chia đoạn

> **Mục tiêu:** tài liệu thật biến thành chunk có heading, tìm được cả khi gõ không dấu.

**Điều kiện vào:** UC018 nhận được tệp và ghi `PENDING`.

**Việc:**

- [ ] 🤖 Parser đa định dạng (pymupdf / python-docx / trafilatura) chạy trong
      `ProcessPoolExecutor` **ĐÚNG 1 WORKER** — *verify: đúng 1 worker, không phải mặc định.
      PDF hỏng làm treo tiến trình; tách tiến trình là để **giết được nó** mà không giết cả service.*
- [ ] 🖐 **`normalize_vi` — tự gõ.** Xử lý zero-width, NFD/NFC, `hoà`/`hòa`, ký tự lặp.
      ⚠️ **MỘT HÀM DUY NHẤT dùng cho CẢ hai đầu** — lúc nạp và lúc truy vấn.
      *Hai hàm khác nhau là lỗi thầm lặng: không có exception, chỉ có recall tụt.*
- [ ] 🖐 **Hàm chia đoạn — tự gõ.** ~500 token, **GIỮ số trang và heading** để trích dẫn được
      (ví dụ `"Bảng giá 2026 > Gói Pro"`).
- [ ] 🤖 Ghi `content_segmented` bằng `pyvi` — *verify: `ViTokenizer` chạy đúng trên câu có dấu
      lẫn không dấu.*
- [ ] 🖐 `tsvector` bọc `unaccent` trong hàm **IMMUTABLE** (bắt buộc để đánh chỉ mục được).
- [ ] 🖐 **Dựng phrase query — tự gõ:** toán tử **liền kề** cho cụm nhiều âm tiết, phép **OR**
      giữa các từ.
      ⚠️ *Dùng `AND` sẽ trả rỗng ngay khi khách gõ thừa một từ.*
- [ ] 🤖 Nếu cần cột mới → migration **bắt đầu từ V210** — *verify: không sửa V201–V209 (đã chạy),
      không đụng dải V1xx của Track A.*
- [ ] 🖐 Unit test: `normalize_vi` · `build_tsquery` với câu **KHÔNG DẤU** · PDF scan phải chuyển
      `FAILED` kèm `error_message`.

**File sẽ đụng:** `src/ai/rag/ingest/` · `ai-service/migration/V210__*.sql` (nếu cần) ·
`tests/unit/test_normalize.py`

**Chạm Dev B:** Dev B đang huấn luyện router nhánh B/C (N4), cuối ngày phóng GPU Kaggle qua đêm.
Không giao cắt. **Nhắc Dev B:** nếu Kaggle chưa verify số điện thoại thì **không bật được GPU** —
hạn chót tối Ngày 4, trượt là đổ cả Ngày 5–7.

**Phải giải thích được:**
- Vì sao `normalize_vi` phải là **một** hàm dùng chung hai đầu? Cho một ví dụ cụ thể hỏng thế nào.
- Vì sao `unaccent` phải bọc trong hàm `IMMUTABLE` mới đánh chỉ mục được?
- Vì sao phrase query dùng `OR` giữa các từ chứ không dùng `AND`?

**Cổng ra (DoD):** unit test `normalize_vi` và `build_tsquery` xanh · PDF scan chuyển `FAILED`
đúng kèm `error_message`.

**Minh chứng báo cáo:** bảng tỉ lệ trích xuất thành công **theo từng định dạng** · phân bố số
token mỗi đoạn (trung vị ~500) · tỉ lệ khớp truy vấn KHÔNG DẤU **trước/sau** khi bật `unaccent` ·
ảnh chụp một chunk có heading đầy đủ.

---

## Ngày 5 — T6 25/09 — UC019 (2/2) Nhúng theo lô + worker Kafka + DLQ

> **Mục tiêu:** tài liệu thật nằm trong `knowledge_chunks` với vector, có chỉ mục HNSW.

**Điều kiện vào:** chunk có heading từ Ngày 4. Bộ topic Kafka đã chốt (Ngày 1, Dev B).

**Việc:**

- [ ] 🤖 `/v1/embed/batch` — lô **32 đoạn** — *verify: không gom toàn bộ vector vào RAM; một tài
      liệu 3.000 đoạn phải chạy được mà RSS không phình.*
- [ ] 🖐 Semaphore giới hạn **ĐÚNG 1 job nạp đồng thời** (dùng chung hàng đợi với UC020 ở N11).
- [ ] 🖐 **Worker thật thay cho `NotImplementedError`** (`src/worker/main.py:38`) — tự gõ phần
      cốt lõi: `enable_auto_commit=False`, `max_poll_interval_ms=600000`, **xác nhận offset SAU
      khi xử lý thành công**.
      *Auto-commit đánh dấu xử lý xong TRƯỚC khi thực sự xong; một lần pod chết là mất sự kiện.*
- [ ] 🖐 Chống trùng bằng `INSERT ... ON CONFLICT DO NOTHING` vào `processed_events` — **0 dòng
      ảnh hưởng thì bỏ qua sự kiện**. *Giao nhận ít nhất một lần: nhận trùng là chắc chắn, không
      phải rủi ro.*
- [ ] 🤖 Chuyển tài liệu sang `READY` + `chunk_count` + `indexed_at`; lỗi vĩnh viễn đẩy sang
      **DLQ** — *verify: phân biệt lỗi tạm thời (retry) và lỗi vĩnh viễn (DLQ); đừng đẩy hết vào DLQ.*
- [ ] 🤖 Endpoint trả **6 bước tiến độ** của job.
- [ ] 🖐 **Chạy `create_hnsw_index.sql` LẦN ĐẦU** — sau khi đã có chunk thật.
      `m=16`, `ef_construction=64`, `CONCURRENTLY`.
- [ ] 🖐 Test: ép lỗi lược đồ để kiểm chứng DLQ · **restart worker giữa chừng**, job phải hoàn
      tất hoặc được nhận lại **nguyên vẹn**.

**File sẽ đụng:** `src/worker/main.py` · `src/worker/consumers/` · `src/ai/rag/ingest/` ·
`inference/src/roles/embed.py`

**Chạm Dev B:** **Cần nhận:** bộ topic đã chốt + `ai-embed` chạy được (Dev B dựng từ N2).
**Dự phòng:** `ai-embed` chưa sẵn → dùng backend `mock` của `src/ai/inference/clients.py`
(Dev B đã làm seed cố định ở N2 đúng để mình không phải chờ), ghi nợ và đo lại ở N7.
⚠️ **Bẫy Kafka hai listener:** worker chạy từ máy chủ → `localhost:29092`; chạy trong container
→ `kafka:9092`.

**Phải giải thích được:**
- Vì sao `enable_auto_commit=False`? Kịch bản mất sự kiện cụ thể nếu để `True`.
- Bảng `processed_events` chống trùng bằng cách nào, và vì sao dùng `ON CONFLICT DO NOTHING`
  chứ không `SELECT` trước rồi `INSERT`?
- `CONCURRENTLY` cho HNSW đánh đổi gì?

**Cổng ra (DoD):** tài liệu thật nằm trong `knowledge_chunks` có vector · `\di` xác nhận chỉ mục
HNSW tồn tại · DLQ hoạt động · restart worker không mất job.

**Minh chứng báo cáo:** thời gian nạp tài liệu 100 trang (đo thật) · throughput đoạn/giây ·
ảnh chụp sự kiện nằm trong DLQ · biểu đồ 6 bước tiến độ · `\di` xác nhận HNSW.

---

## Ngày 6 — T7 26/09 — Hybrid Search + bộ vàng v1 + khai thác dữ liệu fine-tune

> **Mục tiêu:** hybrid thắng dense-only ≥ 5 điểm recall@5, và phóng GPU fine-tune qua đêm.

**Điều kiện vào:** có chunk thật + chỉ mục HNSW và GIN. Chỗ đặt bộ vàng đã chốt (Ngày 1).

**Việc:**

- [ ] 🖐 **MỘT câu SQL gộp hai làn — tự gõ, đây là code lõi nhất của phần truy hồi.**
      Làn vector (HNSW cosine) + làn từ khoá (GIN tsvector), hợp nhất bằng **RRF hằng số 60**.
      **Mỗi làn 30 ứng viên.**
      ⚠️ Chỉ dùng **THỨ HẠNG**, không dùng điểm thô — nên không phải chuẩn hoá hai thang điểm
      khác nhau. **KHÔNG "cải tiến" RRF thành weighted sum** (ADR-0006).
- [ ] 🖐 `SET LOCAL hnsw.ef_search=100` và `hnsw.iterative_scan='relaxed_order'` trong **CÙNG
      transaction** với truy vấn.
- [ ] 🖐 **Bộ vàng v1: 40–50 cặp** câu hỏi/đoạn đúng từ 20 tệp mẫu Ngày 3, đặt đúng chỗ đã chốt.
      *Bắt buộc có TRƯỚC khi đo — recall@5 phải có mẫu số.*
- [ ] 🖐 **ĐO BASELINE (model pretrained):** dense-only vs sparse-only vs hybrid · **1 tenant vs
      20 tenant**.
      ⚠️ *Đây là MỐC SO SÁNH DUY NHẤT của phần fine-tune — không đo hôm nay thì ngày mai không
      có gì để so.* Lưu bảng này lại cẩn thận.
- [ ] 🤖 Khai thác cặp huấn luyện từ **chính kho tri thức** — *verify: `positive` = (câu hỏi sinh
      từ đoạn, đoạn đó); `hard negative` = đoạn **lọt top-5 hybrid nhưng SAI** — chỉ có được SAU
      khi hybrid chạy, nên đúng thứ tự là hôm nay.*
- [ ] 🖐 **Tách tập giữ lại theo TÀI LIỆU, không theo đoạn.**
      *Tách theo đoạn thì các đoạn cùng một tài liệu lọt cả hai bên, model học thuộc văn phong
      tài liệu đó và chỉ số bị thổi phồng.*
- [ ] 🤖 Notebook `07_finetune_embedding.ipynb` — `MultipleNegativesRankingLoss` — *verify: ghim
      seed, ghim phiên bản thư viện, ghi hash dữ liệu, xuất metric ra file (4 điều kiện tái lập).*
- [ ] 🖐 **CUỐI NGÀY: phóng notebook lên Kaggle GPU.** 3–5 giờ máy, **0 giờ người**.

**File sẽ đụng:** `src/ai/rag/retrieve/` · `tests/eval/golden_set.jsonl` (hoặc chỗ đã chốt) ·
`notebooks/07_finetune_embedding.ipynb`

**Chạm Dev B:** Dev B làm UC022 (4/4) — API định tuyến 7 nhánh + **guardrails**.
**Cần nhận:** `src/ai/guardrails/` (`normalize.py`, `injection.py`, `pii.py`) — mình gắn vào
node `guard` ở **Ngày 8**, nên Dev B phải xong hôm nay.
**Dự phòng:** chưa xong → node `guard` ở N8 để chỗ cắm (interface) và ghi nợ, đừng chờ.

**Phải giải thích được:**
- RRF hoạt động thế nào? Vì sao dùng thứ hạng an toàn hơn dùng điểm thô?
- Vì sao `k = 60` chứ không phải số khác? *(Không có câu trả lời "đẹp" — là hằng số kinh nghiệm
  từ bài báo gốc; nói thẳng vậy mạnh hơn là bịa lý do.)*
- Vì sao hard negative phải lấy **sau** khi hybrid chạy chứ không lấy ngẫu nhiên?

**Cổng ra (DoD):**
- ✅ **Hybrid thắng dense-only ≥ 5 điểm recall@5**
- ✅ **Chênh lệch recall@5 giữa 1 tenant và 20 tenant < 3 điểm**
- ✅ Notebook đang chạy trên Kaggle GPU

**Minh chứng báo cáo:** bảng 3 dòng (dense / sparse / hybrid) · bảng 1 tenant vs 20 tenant ·
**bảng baseline recall@5 và nDCG@5 của model pretrained** (cột đối chứng của toàn bộ phần
fine-tune) · số cặp huấn luyện khai thác được + tỉ lệ hard negative.

---

## Ngày 7 — CN 27/09 — 🏁 MỐC M1 · Fine-tune embedding: export, parity, reindex, đo lại

> **Mục tiêu:** chốt ship bản fine-tune hay rollback về pretrained — **bằng số, không bằng cảm tính.**

**Điều kiện vào:** notebook Kaggle đã chạy xong qua đêm.

**Việc:**

- [ ] 🤖 Thu kết quả; export bản fine-tune sang ONNX rồi lượng tử hoá **INT8 động per-channel** —
      *verify: cùng quy trình với Ngày 2, không đổi tham số giữa chừng (nếu đổi thì bảng so sánh
      mất nghĩa).*
- [ ] 🖐 **CỔNG PARITY:** cosine fp32 vs INT8 trên **500 câu** phải **≥ 0,995**.
      ⚠️ *Bản fine-tune có phân bố trọng số đã dịch nên INT8 có thể lệch nhiều hơn bản gốc.*
      🚫 **Không đạt → DỪNG, giữ bản pretrained, ghi ADR.**
- [ ] 🤖 `MODEL_CARD_embedding` v2 — *verify: có sha256, dữ liệu huấn luyện, tập giữ lại.*
- [ ] 🤖 Script reindex — đổi `embedding_model` rồi nhúng lại **TOÀN BỘ** chunk, chạy nền
      ~15–30 phút máy — *verify: chạy nền thật, không block; bản API đầy đủ làm ở Ngày 11.*
- [ ] 🖐 **Đo lại recall@5 và nDCG@5 trên CÙNG bộ vàng v1 của Ngày 6**, so sánh **THEO CẶP** bằng
      **paired bootstrap KTC 95%**.
      ⚠️ *Tiêu chí đúng là **ý nghĩa thống kê**, không phải một ngưỡng chênh lệch tuỳ tiện.*
- [ ] 🖐 **Đường lùi:** giữ **cả hai** artifact, đặt biến `EMB_MODEL_VERSION`. Fine-tune thua
      hoặc parity trượt → reindex ngược về pretrained, mất ~30 phút máy.
      *Cột `embedding_model` trên từng dòng `knowledge_chunks` (V203) có sẵn chính là để làm việc này.*

**File sẽ đụng:** `artifacts/` · `scripts/reindex.py` · `tests/eval/` · `docs/adr/`

**Chạm Dev B:** Dev B chạy **test tải hỗn hợp** hôm nay và phải chạy **SAU khi reindex của mình
xong** để không tranh CPU. → **Báo Dev B ngay khi reindex chạy xong.**

**Phải giải thích được:**
- Vì sao dùng **paired** bootstrap chứ không so hai con số trần?
- Nếu fine-tune thắng 2 điểm recall nhưng KTC 95% chứa 0 thì kết luận là gì?
- Vì sao cổng parity vẫn là 0,995 cho bản fine-tune dù biết nó dễ lệch hơn?

**🏁 ĐIỀU KIỆN THOÁT M1 — 4/4:**

| # | Điều kiện | ✅/❌ |
|---|---|---|
| 1 | Nạp được tài liệu thật vào `knowledge_chunks` | |
| 2 | Test cách ly tenant xanh trong CI | |
| 3 | Hybrid thắng dense ≥ 5 điểm | |
| 4 | Router chạy trong `ai-classify` (Dev B) | |

🚨 **TRƯỢT M1 → cắt rerank khỏi Ngày 8 và bỏ semantic cache ở Ngày 16.** Cắt ngay, đừng chờ.

**Minh chứng báo cáo:** parity bản fine-tune ≥ 0,995 · **hiệu số recall@5 trước/sau fine-tune
kèm KTC 95%** (biểu đồ này là một mục riêng đáng giá trong báo cáo) · `MODEL_CARD` v2 ·
ADR quyết định ship hay rollback · thời gian reindex toàn bộ chunk · bảng điều kiện thoát M1 4/4.

---
---

# TUẦN 2 — Luồng chính và nghiệp vụ AI

## Ngày 8 — T2 28/09 — LangGraph khung 8 node + node guard + node retrieve

> **Mục tiêu:** máy trạng thái chạy được, hai node của mình cắm vào đúng chỗ.

**Điều kiện vào:** 🤝 **AgentState phải chốt CÙNG Dev B TRƯỚC KHI ai code node nào.**

**Việc:**

- [ ] 🤝 **NGỒI CÙNG DEV B chốt cấu trúc `AgentState`.** Đây là điểm hai đường gặp nhau — lệch ở
      đây là conflict cả tuần.
      **Quy tắc:** mỗi người chỉ **ĐĂNG KÝ** node của mình vào registry, **KHÔNG sửa node của
      người kia**. Vi phạm quy tắc này là nguồn conflict số một.
- [ ] 🤖 `StateGraph` 8 node (`guard`, `route`, `fastpath`, `retrieve`, `generate`, `postguard`,
      `handoff`, `telemetry`) với cạnh điều kiện — *verify: file `graph.py` là file CHUNG, cần
      Dev B duyệt; mình chỉ thêm node của mình.*
- [ ] 🤖 **Node `guard`** — normalize + injection + PII, **dùng lại** `guardrails` Dev B viết
      Ngày 6 — *verify: gọi lại hàm của Dev B, **không viết lại** logic phát hiện; viết lại là
      hai bộ luật lệch nhau.*
- [ ] 🖐 **Node `retrieve` — tự gõ phần quyết định:**
      `hybrid_search(pool=30)` → `needs_rerank()` kiểm **`AMBIGUITY_GAP`**: chênh điểm RRF giữa
      **hạng 1 và hạng 3 < 0,15** thì mới gọi cross-encoder.
- [ ] 🖐 Rerank trên **12 ứng viên đầu** (**KHÔNG phải 20**) · **5 đoạn** vào lời nhắc ·
      **sàn liên quan toàn tập 0,25** và **sàn từng đoạn 0,15**.
- [ ] 🖐 **RERANK ĐẶT SAU FEATURE FLAG VÀ MẶC ĐỊNH TẮT.**
- [ ] 🖐 Đo nDCG@5 **có/không rerank MỘT LẦN** làm căn cứ cho ADR bật/tắt.
      **Cổng bật production:** ≥ **5 điểm nDCG@5** VÀ p95 chat vẫn **< 4 s**. Không đạt → giữ TẮT.
- [ ] 🤖 Mọi node ghi vào `src/ai/service.py` — **facade DUY NHẤT** — *verify: `api/` và `worker/`
      chỉ gọi vào `service.py`, **không gọi thẳng** `orchestrator`. CI kiểm luật này bằng grep —
      chạy thử `.github/workflows/ci.yml` bước "chiều phụ thuộc" cho chắc.*

⚠️ **Từ hôm nay toàn bộ truy hồi chạy trên EMBEDDING ĐÃ FINE-TUNE** (chốt ở Ngày 7). Mọi con số
recall/nDCG từ đây trở đi là của bản fine-tune; bảng baseline pretrained đã lưu từ Ngày 6.

**File sẽ đụng:** `src/ai/orchestrator/{graph.py,state.py}` (CHUNG) ·
`src/ai/orchestrator/nodes/{guard,retrieve}.py` · `src/ai/service.py` (CHUNG) ·
`src/ai/rag/rerank/` · `inference/src/roles/rerank.py`

**Chạm Dev B:** 🤝 buổi chốt `AgentState`. Dev B làm node `route` + `fastpath` + `telemetry`
cùng ngày. **Phải giao:** node `guard` và `retrieve` đã đăng ký vào registry, để Dev B nối
`route` vào sau `guard`.

**Phải giải thích được:**
- `AMBIGUITY_GAP` đo cái gì? Vì sao so hạng 1 với **hạng 3** chứ không phải hạng 2?
- Vì sao rerank **12** ứng viên chứ không rerank cả 20 đã lấy về?
- Vì sao rerank mặc định **TẮT** dù nó cải thiện chất lượng?

**Cổng ra (DoD):** graph 8 node chạy end-to-end (dù node của Dev B còn stub) · CI xanh ở bước
kiểm chiều phụ thuộc · có số nDCG có/không rerank.

**Minh chứng báo cáo:** sơ đồ máy trạng thái LangGraph 8 node · tỉ lệ lượt rơi vào vùng mơ hồ
(kỳ vọng 30–40%) · bảng nDCG@5 có/không rerank · CI xanh ở bước chiều phụ thuộc.

---

## Ngày 9 — T3 29/09 — UC023 Node generate + postguard + chịu lỗi LLM

> **Mục tiêu:** endpoint chat trả câu trả lời **có trích dẫn**, và không sập khi LLM sập.

**Điều kiện vào:** node `retrieve` trả được 5 đoạn. `ANTHROPIC_API_KEY` đã có.

**Việc:**

- [ ] 🤖 Node `generate` — dựng prompt 5 đoạn + gọi LLM API — *verify: ngân sách **2.500 ms**
      trong tổng 4.000 ms; có timeout thật, không để treo vô hạn.*
- [ ] 🖐 **Nội dung truy hồi là DỮ LIỆU KHÔNG ĐÁNG TIN (bề mặt T3)** — không để nó **chỉ thị**
      được cho mô hình. Tách rõ vùng dữ liệu và vùng chỉ thị trong prompt.
- [ ] 🖐 **Node `postguard` — tự gõ.** Kiểm **MỌI trích dẫn** có nằm trong đoạn đã lấy về;
      che PII; tính **`groundedness_score` VÀ `retrieval_top_score`**.
      ⚠️ **HAI đại lượng khác nhau:** `retrieval_top_score` đo *đoạn có giống câu hỏi không*;
      `groundedness_score` đo *câu trả lời có thật sự dựa vào đoạn không*.
      *Truy hồi tốt mà mô hình vẫn bịa là trường hợp CÓ THẬT.*
- [ ] 🖐 **Circuit breaker 3 trạng thái — tự gõ:** `closed → open → half-open`.
      Retry `429` / `5xx` / `timeout`; **KHÔNG retry** `400` / `401` / `422`.
      Breaker mở → trả câu trả lời **suy giảm** kèm `degraded=true`, **không ném lỗi ra người dùng**.
- [ ] 🖐 Unit test circuit breaker **đủ 3 trạng thái**.
- [ ] 🤖 Ghi `latency_breakdown` 9 tầng vào response — *verify: `ai.ai_interactions` đã có sẵn
      `retrieval_top_score`, `groundedness_score`, `is_cached`, `prompt_tokens`,
      `completion_tokens`, `cost_vnd`, `latency_ms` (V209) — **lược đồ không phải sửa gì**.*

**File sẽ đụng:** `src/ai/orchestrator/nodes/{generate,postguard}.py` ·
`src/ai/rag/generate/` · `src/ai/integrations/llm/`

**Chạm Dev B:** ⚠️ **Dev B cần node `generate` của mình cho UC029 ở Ngày 11.**
**Nếu hôm nay trượt → báo Dev B NGAY trong ngày** để Dev B đảo lịch: làm UC031/UC014 trước,
UC029 sau. Im lặng một ngày là chặn người kia một ngày.

**Phải giải thích được:**
- `groundedness_score` và `retrieval_top_score` khác nhau thế nào? Cho một ví dụ mà cái này cao
  còn cái kia thấp.
- Vì sao **không** retry lỗi `422`?
- Trạng thái `half-open` của circuit breaker để làm gì? Bỏ nó đi thì hỏng thế nào?

**Cổng ra (DoD):** endpoint chat trả đúng schema kèm `latency_breakdown` · unit test breaker 3/3
trạng thái xanh.

**Minh chứng báo cáo:** ảnh chụp endpoint chat trả đúng schema kèm `latency_breakdown` 9 tầng ·
bảng phân bố `groundedness_score` vs `retrieval_top_score` · unit test circuit breaker đủ 3 trạng thái.

---

## Ngày 10 — T4 30/09 — UC025 + UC027 Từ chối khi thiếu căn cứ và đánh giá chất lượng

> **Mục tiêu:** hệ thống biết nói "tôi không biết" đúng lúc, và đo được chất lượng của chính nó.

**Điều kiện vào:** UC023 trả lời được.

⚠️ **LƯU Ý:** danh sách khoảng trống tri thức là **MỘT TRUY VẤN GỘP**, không phải một bảng mới —
**đừng tạo bảng.**

**Việc — UC025:**

- [ ] 🖐 **`search_or_abstain` — tự gõ. 4 lý do từ chối:**
      (1) *chưa có trong tài liệu* — không đoạn nào vượt **sàn 0,25**
      (2) *ngoài phạm vi dữ liệu*
      (3) *độ tin cậy thấp*
      (4) *dò tìm dữ liệu nội bộ* → bật `safety_flag`
- [ ] 🖐 Ngưỡng bám nguồn không đạt → **HUỶ câu trả lời đã sinh** và chuyển sang từ chối.
      *Sinh xong rồi vứt nghe lãng phí, nhưng trả lời bịa ra thì tệ hơn nhiều.*
- [ ] 🖐 Ngưỡng chọn **từ đường cong hiệu chỉnh**, có baseline "không ngưỡng" để so.
- [ ] 🖐 **30 câu hỏi ngoài phạm vi** — phải trả rỗng đúng **30/30**.

**Việc — UC027:**

- [ ] 🤖 Endpoint feedback; **4 mã lý do chê** — *verify: ràng buộc **chê thì bắt buộc chọn lý do**;
      `ai.ai_feedback` (V204) đã có `rating`, `reason_code`, `rater_type` và chỉ mục `uq_feedback_rater`.*
- [ ] 🖐 **Tín hiệu rẻ chạy 100% lượt:** độ phủ trích dẫn · tỉ lệ từ chối · tỉ lệ suy giảm ·
      tỉ lệ chuyển giao. **LLM chấm điểm LẤY MẪU 5%.**
- [ ] 🖐 **Mẫu số của tỉ lệ đánh giá tích cực tính trên SỐ LƯỢT CÓ ĐÁNH GIÁ**, không phải tổng
      số lượt. *Tính sai mẫu số là cách dễ nhất để báo cáo một con số đẹp vô nghĩa.*

**File sẽ đụng:** `src/ai/rag/retrieve/` · `src/ai/orchestrator/nodes/postguard.py` ·
`src/api/v1/endpoints/` · `tests/eval/`

**Chạm Dev B:** UC027 phụ thuộc UC039 (telemetry) của Dev B từ N8. **Cần nhận:** node `telemetry`
ghi được 4 metric. **Dự phòng:** chưa có → đọc thẳng từ `ai.ai_interactions` và ghi nợ.

**Phải giải thích được:**
- Vì sao huỷ câu trả lời đã sinh thay vì trả kèm cảnh báo?
- Vì sao mẫu số tỉ lệ tích cực phải là "số lượt có đánh giá"? Nếu tính trên tổng lượt thì con số
  bị bóp méo theo hướng nào?
- 4 lý do từ chối khác nhau ở đâu? Lý do (1) và (3) dễ nhầm — phân biệt thế nào?

**Cổng ra (DoD):** **30/30** câu ngoài phạm vi trả rỗng đúng.

**Minh chứng báo cáo:** 30/30 câu ngoài phạm vi · bảng 4 lý do từ chối × số ca · độ chính xác và
độ phủ của hành vi từ chối **so với baseline không ngưỡng** · bảng 7 tín hiệu chất lượng × tần suất đo.

---

## Ngày 11 — T5 01/10 — UC020 Quản lý kho tri thức (duyệt, sửa, nạp lại, gỡ)

> **Mục tiêu:** quản trị viên làm chủ được kho tri thức mà không có khoảng trống dữ liệu.

**Điều kiện vào:** UC019 nạp được tài liệu. `pg_trgm` và `unaccent` đã bật từ V201.

**Việc:**

- [ ] 🤖 Danh sách tài liệu **phân trang** + lọc theo `status`/`sourceType` + tìm kiếm **KHÔNG
      phân biệt hoa thường và KHÔNG phân biệt dấu** (`unaccent` + `pg_trgm`) — *verify: gõ
      `bao gia` phải khớp `báo giá`; dùng lại `normalize_vi` của Ngày 4, không viết hàm thứ hai.*
- [ ] 🤖 Xem chunk của một tài liệu — *verify: trả `heading` nhưng **KHÔNG trả cột `embedding`**
      (nặng và vô nghĩa với người đọc). Đây là lỗi AI hay mắc: `SELECT *`.*
- [ ] 🖐 `PATCH` siêu dữ liệu **không đụng chỉ mục vector**.
- [ ] 🖐 **Reindex — GIỮ NGUYÊN bản cũ tới khi bản mới nạp xong mới chuyển đổi.**
      **0 giây kho tri thức trống.** (Bản API đầy đủ của script đã viết Ngày 7.)
- [ ] 🖐 **DELETE — xoá đoạn TRƯỚC rồi mới chuyển `ARCHIVED`.**
      ⚠️ **Nếu xoá vector thất bại thì KHÔNG đánh dấu đã lưu trữ.**
      *Điểm 9 trong "Mười một điểm cần chốt" — đánh dấu trước rồi xoá lỗi là để lại vector mồ côi
      mà không ai biết.*
- [ ] 🖐 Reindex toàn tenant khi đổi `embedding_model`.
- [ ] 🖐 Test 4 mã lỗi: **`404`** cho tài liệu của tenant khác (*không phân biệt được với "không
      tồn tại" — đây là hành vi **ĐÚNG***) · **`409`** khi tài liệu đang bận · **`422`** khi trùng
      ràng buộc `title+version` · **`502`** thì giữ nguyên trạng thái.

**File sẽ đụng:** `src/api/v1/endpoints/` · `src/ai/db/repositories/` · `src/ai/rag/ingest/`

**Chạm Dev B:** Dev B làm UC029 hôm nay, cần node `generate` của mình (N9). Không giao cắt code.

**Phải giải thích được:**
- Vì sao tài liệu của tenant khác trả `404` chứ không phải `403`?
- Vì sao xoá đoạn **trước** rồi mới `ARCHIVED`, không làm ngược lại?
- Reindex làm sao để không có khoảnh khắc nào kho tri thức rỗng?

**Cổng ra (DoD):** 4 mã lỗi đúng · chứng minh **0 giây kho tri thức trống** trong lúc reindex.

**Minh chứng báo cáo:** bảng 4 mã lỗi × phản hồi đúng · ảnh chụp tìm kiếm `bao gia` khớp `báo giá` ·
chứng minh 0 giây kho tri thức trống · nhật ký kiểm toán đủ 3 thao tác (sửa, reindex, gỡ).

---

## Ngày 12 — T6 02/10 — UC026 + UC041 Tóm tắt hội thoại và xoá dữ liệu cá nhân

> **Mục tiêu:** tóm tắt tái lập được, và xoá dữ liệu cá nhân đúng luật mà không xoá nhầm dấu vết
> kinh doanh.

**Điều kiện vào:** worker Kafka chạy (N5).

⚠️ Track A đã có sẵn `summary_data`, `summary_trigger`, `summary_model_version` trên
`conversations` (V114) kèm ràng buộc `ck_conv_summary_complete` — **ai-service ghi QUA API,
không ghi thẳng.**

**Việc — UC026:**

- [ ] 🤖 Worker nhận sự kiện hội thoại đóng, sinh tóm tắt — *verify: **4 PHẦN BẮT BUỘC** (nhu cầu
      chính · thông tin khách đã cung cấp · vấn đề chưa giải quyết · bước tiếp theo đề xuất);
      thiếu phần nào là vi phạm `ck_conv_summary_complete`.*
- [ ] 🖐 **`temperature = 0`** để tái lập được.
- [ ] 🖐 **GHIM phiên bản model làm ẢNH CHỤP**, không đọc tham chiếu.
      *Đổi model rồi đọc qua tham chiếu thì mọi bản tóm tắt cũ **tự khai sai** phiên bản.*
- [ ] 🤖 Lưu `jsonb` **qua API của java-core** — *verify: không có câu `INSERT`/`UPDATE` nào chạm
      schema `engagement` (ADR-0002).*

**Việc — UC041:**

- [ ] 🖐 Endpoint xoá dữ liệu cá nhân — xoá **mọi chunk theo `contact_id`**, xoá đặc trưng lead
      **QUA API** trên `sales.lead_scores`.
      ⚠️ *Không có `ai.lead_features` để xoá — bảng đó không tồn tại và sẽ không tạo (ADR-0016).*
- [ ] 🖐 **Xoá hội thoại nguồn KHÔNG kéo theo xoá cơ hội tiềm năng** — liên kết về rỗng, bản ghi
      vẫn còn.
      *Nghị định 13/2023/NĐ-CP yêu cầu xoá **dữ liệu cá nhân**, không phải xoá **dấu vết kinh doanh**.*
- [ ] 🤖 Nếu cần chỉ mục bộ phận theo `contact_id` → migration **V210** (hoặc số kế tiếp) —
      *verify: không trùng số với migration Dev B có thể đã tạo; `ls migration/` trước khi đặt tên.*
- [ ] 🖐 Test: câu trả lời sinh **SAU** khi xoá không còn trích dẫn dữ liệu đã xoá.

**File sẽ đụng:** `src/worker/consumers/` · `src/ai/rag/generate/` ·
`src/ai/integrations/java_core/` · `ai-service/migration/V21x__*.sql`

**Chạm Dev B:** UC041 xoá đặc trưng lead qua API — **cần nhận** đường gọi
`src/ai/integrations/java_core/` mà Dev B dựng ở N9.
**Dự phòng:** chưa có → mock lời gọi, ghi nợ, nối thật ở N18 (contract test).

**Phải giải thích được:**
- Vì sao `temperature = 0`? Nó có làm tóm tắt kém đi không?
- Vì sao ghim phiên bản model dạng "ảnh chụp" chứ không tham chiếu?
- Vì sao xoá hội thoại **không** xoá cơ hội tiềm năng? Lập luận pháp lý là gì?

**Cổng ra (DoD):** 4/4 phần tóm tắt xuất hiện trên 20 hội thoại mẫu · xoá xong thì câu trả lời
mới không còn trích dẫn dữ liệu đã xoá.

**Minh chứng báo cáo:** 4/4 phần tóm tắt trên 20 hội thoại mẫu · báo cáo xoá dữ liệu (số chunk +
số dòng đặc trưng đã xoá cho một contact) · chứng minh câu trả lời sinh sau đó không còn trích dẫn
dữ liệu đã xoá.

---

## Ngày 13 — T7 03/10 — Eval harness một lệnh + mở rộng bộ vàng

> **Mục tiêu:** gõ **một lệnh** ra toàn bộ bảng số liệu của báo cáo, chạy hai lần ra cùng con số.

**Điều kiện vào:** toàn bộ luồng trả lời chạy được.

**Việc:**

- [ ] 🖐 **MỞ RỘNG bộ vàng v1 (40–50 cặp) lên ≥ 80 cặp.**
      ⚠️ **GIỮ NGUYÊN 40–50 cặp cũ** để phần so sánh fine-tune vẫn dùng chung mẫu số; cặp mới
      chỉ dùng cho eval cuối.
- [ ] 🖐 Đóng băng và ghi **hash mới** vào `DATA_HASHES.txt`, **giữ nguyên hash cũ** để so sánh
      lịch sử vẫn hợp lệ.
- [ ] 🤖 Đóng gói eval harness thành **MỘT LỆNH** sinh toàn bộ bảng số liệu (recall@5, nDCG@5,
      độ phủ trích dẫn, tỉ lệ từ chối, p95 từng tầng) ở dạng **CSV và PNG** — *verify: `ranx` đã
      có trong `dev.txt`, dùng thư viện thay vì tự cài đặt công thức; ghim **seed**.*
- [ ] 🖐 Mỗi cấu hình thí nghiệm **một file** trong `tests/eval/configs/` (hiện chưa có file
      `.yaml` nào).
      *Một điểm Recall không kèm config là số **không dùng được** trong báo cáo.*
- [ ] 🖐 **Chứng minh tái lập: chạy 2 lần ra cùng con số.**

**File sẽ đụng:** `tests/eval/` · `tests/eval/configs/*.yaml` · `tests/eval/reports/` ·
`artifacts/DATA_HASHES.txt`

**Chạm Dev B:** Dev B gom test của mình thành một lệnh cùng ngày. **Đối chiếu cách đặt tên** để
Ngày 20 chạy nối nhau được. Bộ hồi quy đủ 17 UC vẫn hoãn — đừng làm.

**Phải giải thích được:**
- Vì sao giữ nguyên 40–50 cặp cũ thay vì trộn hết thành 80 cặp mới?
- Ghim seed ở đâu và ghim cái gì để chạy hai lần ra cùng số?

**Cổng ra (DoD) — ba chỉ số §1.6 đo lần đầu:**
- ✅ **recall@5 ≥ 0,85** trên bộ vàng ≥ 80 cặp
- ✅ **độ phủ trích dẫn ≥ 0,80**
- ✅ **tổng p95 ba service < 480 ms** (bảng tách 3 dòng: classify / embed / rerank)
- ✅ chạy 2 lần ra cùng con số

⚠️ *Ngưỡng recall là **0,85** theo §1.6, không phải 0,80.*

**Minh chứng báo cáo:** recall@5 · độ phủ trích dẫn · bảng p95 tách 3 service · chứng minh tái lập.

---

## Ngày 14 — CN 04/10 — 🏁 MỐC M2 · Demo luồng chính end-to-end

> **Mục tiêu:** có video chứng minh hệ thống chạy thật, không phải slide.

**Việc:**

- [ ] 🖐 Chạy end-to-end: khách gửi tin → `guard` → `route` → `retrieve` → `generate` →
      `postguard` → `handoff` → `telemetry`.
- [ ] 🖐 **Quay video 3 luồng:** (1) trả lời có trích dẫn · (2) từ chối khi thiếu căn cứ ·
      (3) chuyển giao nhân viên.
- [ ] 🤖 Dựng biểu đồ `latency_breakdown` **9 tầng** của một lượt thật — *verify: đặt **cạnh bảng
      ngân sách §5.3** để thấy tầng nào đang ăn vào khoản dự phòng 900 ms.*
- [ ] 🖐 **VIẾT:** phần báo cáo về UC020, UC023, UC025, UC026, UC027, UC041.
      *Viết lúc còn nhớ rẻ hơn nhiều so với viết ở Ngày 21.*
- [ ] 🖐 Bảng đối chiếu **7 chỉ số §1.6 ở mốc giữa kỳ** — **ô nào chưa đo thì ghi "chưa đo",
      không để trống.** *Ô trống đọc như một chỉ số bị giấu.*

**Chạm Dev B:** Dev B quay demo luồng nghiệp vụ + test ma trận suy giảm cùng ngày. **Ghép video
sau**, Ngày 21.

**Phải giải thích được:**
- Đi qua 8 node theo đúng thứ tự và nói mỗi node làm gì trong **một câu**. Đây là câu hỏi mở đầu
  gần như chắc chắn của buổi bảo vệ.
- Nhìn biểu đồ `latency_breakdown`: tầng nào đang ăn nhiều nhất, và nếu phải cắt 500 ms thì cắt ở đâu?
- Vì sao ngân sách §5.3 có khoản **dự phòng 900 ms**, và nó đã bị tiêu vào đâu?

**🏁 ĐIỀU KIỆN THOÁT M2:** 17/17 UC có endpoint/worker chạy + 1 test luồng chính + 1 con số minh
chứng; đã quay được demo luồng trả lời và luồng lead.

🚨 **TRƯỢT M2 → cắt UC038 (Ngày 17) và dồn Ngày 15–16 sang hoàn thiện UC còn thiếu.**

**Minh chứng báo cáo:** **VIDEO DEMO LUỒNG CHÍNH** · biểu đồ `latency_breakdown` 9 tầng của một
lượt thật · **bảng đối chiếu 7 chỉ số §1.6 ở mốc giữa kỳ**.

---
---

# TUẦN 3 — Đo đạc, triển khai, nghiệm thu

## Ngày 15 — T2 05/10 — Benchmark rút gọn + chốt cấp vCPU + ADR

> **Mục tiêu:** chốt cấu hình vCPU **bằng bảng số**, không bằng phỏng đoán.

**Điều kiện vào:** `inference/src/bench_cpu.py` hiện là khung rỗng (39 dòng docstring) — **phải
viết code thật trước khi chạy.**

**Việc:**

- [ ] 🤖 Viết `bench_cpu.py` thật — *verify: đo p50/p95/RSS, có warm-up, số lần lặp đủ lớn để
      p95 ổn định.*
- [ ] 🖐 Chạy bản rút gọn: **3 model** (encoder S, encoder M, cross-encoder S) × **2 mức vCPU**
      (2 và 4).
      ⚠️ **CHẠY TỪNG SERVICE MỘT, không song song** — chạy song song thì các service tranh CPU
      và **mọi con số đều vô nghĩa**.
      *(Ma trận đầy đủ đã cắt — xem sheet "Phạm vi cắt & làm sau".)*
- [ ] 🖐 **Chứng minh 2 điều:**
      (1) với model nhỏ, **tăng vCPU KHÔNG cải thiện p95**;
      (2) `OMP_NUM_THREADS` phải **BẰNG số CPU được cấp** — để mặc định thì ONNX Runtime đọc số
      CPU của **node** chứ không đọc limits của container, p95 có thể tệ gấp 3 lần mà không log
      nào báo.
- [ ] 🖐 Chốt cấp vCPU: `OMP_NUM_THREADS = limits.cpu`, `inter_op_num_threads = 1`.
- [ ] 🖐 **ADR chốt cấp vCPU.** Với model bị loại, ghi rõ **đã thử đòn bẩy nào và SỐ ĐO**.
      *Một dòng "quá chậm" không kèm bảng số là KHÔNG ĐỦ để loại một model trong báo cáo.*

**File sẽ đụng:** `inference/src/bench_cpu.py` · `inference/compose.inference.yml` · `docs/adr/`

**Chạm Dev B:** Dev B làm UC039 (mô hình đọc báo cáo) cùng ngày. Không giao cắt.

**Phải giải thích được:**
- Vì sao `inter_op_num_threads = 1`?
- Vì sao chạy benchmark từng service một? Nếu chạy song song thì số sai theo hướng nào?
- Vì sao model nhỏ tăng vCPU không nhanh hơn?

**Cổng ra (DoD):** có bảng benchmark đầy đủ · ADR chốt vCPU cho 3 service.

**Minh chứng báo cáo:** bảng benchmark rút gọn (model × vCPU × threads × p50 × p95 × RSS ×
đạt/không) · **bảng chênh lệch p95 khi ghim luồng và khi để mặc định** · ADR chốt cấp vCPU.

---

## Ngày 16 — T3 06/10 — Tối ưu độ trễ + semantic cache + GIẢM DUNG LƯỢNG IMAGE

> **Mục tiêu:** image xuống dưới 400 MB (nợ kỹ thuật bắt buộc trả), và cache không rò rỉ tenant.

**Điều kiện vào:** cổng CI dung lượng đã `exit 1` từ Ngày 1 → **đây là việc BẮT BUỘC, không phải
tuỳ chọn.**

**Nợ kỹ thuật đã ghi nhận (ADR-0015 mục 6):** image `ai-service` đang **776 MB**, ngưỡng
**< 400 MB**. Bóc tách: `scipy`+`numpy`+`sklearn` **252 MB** (phụ thuộc gián tiếp của `pyvi`) ·
`pymupdf` **63 MB** · `babel`+`zstandard` **55 MB** (gián tiếp của `trafilatura`).

**Việc:**

- [ ] 🤖 Giảm image xuống **< 400 MB** — tách layer worker, loại phụ thuộc chỉ dùng lúc build,
      cân nhắc thay `trafilatura` ở nhánh HTML — *verify: **KHÔNG được bỏ `pyvi`** (`rag/tsquery`
      cần `ViTokenizer`) và **KHÔNG được import `sklearn` trong `src/`** để suy luận. Chạy lại
      cổng CI cả hai luật.*
- [ ] 🖐 **Semantic cache trên Redis với KHOÁ BẮT BUỘC CÓ `tenant_id` — tự gõ.**
      ⚠️ *Thiếu nó là rò rỉ dữ liệu giữa các doanh nghiệp, và đây là **một trong 7 chỉ số nghiệm thu**.*
- [ ] 🖐 Đánh dấu `is_cached` và **KHÔNG tính chi phí** gọi model; **vô hiệu cache khi kho tri
      thức của tenant thay đổi**.
- [ ] 🖐 Tối ưu theo **số đo thật**: `ef_search` · `LIMIT` hybrid · độ dài prompt · số đoạn vào
      lời nhắc.
      ⚠️ *Các dòng ngân sách §5.3 **phân bổ lại được cho nhau**, chỉ dòng **TỔNG 4.000 ms** là
      bất biến — embedding cần 200 ms thay vì 120 ms thì lấy từ khoản dự phòng 900 ms, **KHÔNG
      loại model**.*
- [ ] 🖐 Test chứng minh **hai tenant hỏi cùng câu nhận hai câu trả lời khác nhau**.
- [ ] 🤝 PII trong log: grep tự động = 0 (làm cùng Dev B — Dev B làm phía UC040).

**File sẽ đụng:** `ai-service/Dockerfile` · `ai-service/requirements/base.in|txt` ·
`src/ai/rag/` · `.github/workflows/ci.yml`

**Chạm Dev B:** Dev B làm UC040 + UC006 cùng ngày, cũng grep PII. **Chia việc grep**, đừng làm
trùng.

**Phải giải thích được:**
- Vì sao khoá cache phải có `tenant_id`? Mô tả chính xác kịch bản rò rỉ nếu thiếu.
- `sklearn` là phụ thuộc gián tiếp của `pyvi` — vậy vì sao cổng CI chỉ chặn 3 gói chứ không chặn
  `sklearn`?
- Khi nào thì phải vô hiệu cache của một tenant?

**Cổng ra (DoD):**
- ✅ **Dung lượng image `ai-service` < 400 MB** (CI xanh ở cổng dung lượng)
- ✅ Test hai tenant cùng câu hỏi → hai câu trả lời khác nhau

**Minh chứng báo cáo:** dung lượng image < 400 MB · **bảng ngân sách §5.3 phiên bản ĐÃ PHÂN BỔ
LẠI** theo số đo thật, đặt cạnh bảng gốc · p95 end-to-end trước/sau tối ưu · tỉ lệ cache hit và
mức giảm chi phí · test cách ly cache.

---

## Ngày 17 — T4 07/10 — Kiểm thử bảo mật phần dữ liệu (3/5 bài)

> **Mục tiêu:** chứng minh mô hình ngôn ngữ **không trở thành đường vòng qua RLS**.

**Điều kiện vào:** `test_rls.py` từ Ngày 1 đang chạy trong CI. Ba bài hôm nay là **mức cao hơn:
tấn công qua ĐƯỜNG NGÔN NGỮ chứ không qua đường SQL.**

**Việc:**

- [ ] 🖐 **BÀI (1) — CÁCH LY TENANT QUA NGÔN NGỮ.** Hỏi tenant A một câu **chỉ trả lời được bằng
      tài liệu của B** → phải **TỪ CHỐI**, không phải trả lời sai và cũng không phải trả lời đúng.
      ⚠️ **Đây là bài quan trọng nhất:** RLS chặn được truy vấn, nhưng **chỉ bài này** chứng minh
      mô hình không trở thành đường vòng qua RLS.
- [ ] 🖐 **BÀI (2) — CÁCH LY CACHE.** Cùng một câu hỏi từ **2 tenant** phải trả **2 câu trả lời
      từ 2 kho tri thức** (kiểm chứng khoá cache của Ngày 16).
- [ ] 🖐 **BÀI (3) — PII TRONG LOG.** Grep tự động tìm số điện thoại, email, nội dung tin nhắn
      thô trên **TOÀN BỘ** log.
- [ ] 🖐 Xác nhận `ai-service` kết nối CSDL bằng role **`ai_app`** (không phải `crm_owner`).

**Chạm Dev B:** Dev B làm 2 bài còn lại (payload không định danh · bộ adversarial) + UC038.
**Tổng 5 bài** — bài thứ 6 về "quyền công cụ" thuộc sheet *Mở rộng sau đồ án*, ghi **"không áp
dụng" kèm lý do**, không để ô trống.

**Phải giải thích được:**
- Vì sao "trả lời đúng bằng tài liệu của B" cũng là **sai**, không chỉ "trả lời sai"?
- RLS đã chặn ở tầng SQL rồi, vậy bài (1) còn chứng minh thêm điều gì?

**Cổng ra (DoD):** **3/3 bài đạt** · kết quả grep PII = **0**.

**Minh chứng báo cáo:** 3/3 bài đạt · ảnh chụp tenant A **TỪ CHỐI đúng** khi được hỏi về tài liệu
của B · kết quả grep PII = 0 · ảnh chụp `SELECT current_user` = `ai_app`.

---

## Ngày 18 — T5 08/10 — Triển khai gọn trên 1 instance cloud + dữ liệu doanh nghiệp thật

> **Mục tiêu:** gọi được endpoint chat qua HTTPS từ Internet, và test RLS xanh **ở nơi thật sự chạy**.

⚠️ **ĐÃ CẮT:** cụm EKS 5 node group + ALB + HPA + PDB. `inference/k8s/` chỉ có `.gitkeep`.

**Việc:**

- [ ] 🤖 Deploy toàn bộ stack bằng `docker compose` **kiểu production** trên 1 instance cloud CPU:
      Nginx + TLS · biến môi trường **tách khỏi repo** (KHÔNG commit `.env`) · healthcheck ·
      restart policy · **giới hạn `cpus`/`mem` đúng cấp model đã chốt Ngày 15** — *verify: đối
      chiếu từng service với bảng ADR vCPU của Ngày 15, không đặt đại.*
- [ ] 🖐 Nạp dữ liệu test **đa tenant**.
- [ ] 🖐 **CHẠY LẠI test RLS trên môi trường triển khai.**
      *Test xanh ở CI không thay thế được test xanh ở nơi thật sự chạy.*
- [ ] 🖐 **DỮ LIỆU THẬT:** chuẩn đầu ra của đề tài ghi *"thử nghiệm với dữ liệu thực tế của ít
      nhất 1 doanh nghiệp"*. Nhóm đang dùng dữ liệu tự soạn/công khai.
      ⚠️ **HÔM NAY là chỗ cuối cùng còn kịp** nạp dữ liệu doanh nghiệp thật nếu xin được — phải
      **ẩn danh hoá trước** (Nghị định 13) và **KHÔNG commit** dữ liệu chưa ẩn danh.
      **Không kịp thì ghi thẳng vào mục Hạn chế của báo cáo** — đừng để người đọc tự phát hiện.

**Chạm Dev B:** Dev B làm **contract test hai chiều với Track A** cùng ngày, gồm vòng phản hồi
`crm.deal.closed` → cập nhật ngược `outcome`. **Cần phối hợp:** môi trường triển khai của mình
là nơi Dev B chạy contract test.

**Phải giải thích được:**
- Vì sao phải chạy lại test RLS trên môi trường deploy khi CI đã xanh?
- Dữ liệu dùng để thử nghiệm là loại nào, và ranh giới trung thực của nó?

**Cổng ra (DoD):** gọi được endpoint chat qua **HTTPS từ Internet** · **0 rò rỉ tenant** trên môi
trường triển khai.

**Minh chứng báo cáo:** endpoint chat qua HTTPS · 0 rò rỉ tenant trên môi trường triển khai ·
bảng cấu hình `cpus`/`OMP_NUM_THREADS` của 4 service khớp cấp model Ngày 15 · **ghi rõ dữ liệu
thử nghiệm là loại nào** (thật đã ẩn danh / tự soạn / công khai).

---

## Ngày 19 — T6 09/10 — Load test rút gọn

> **Mục tiêu:** chỉ số §1.6 đầu tiên — p95 < 4.000 ms **và không tăng dần**.

⚠️ **ĐÃ CẮT:** đỉnh tải 150 người dùng và soak 4 giờ. *Đỉnh tải 150u chỉ có nghĩa khi có
autoscaling; trên một instance đơn nó chỉ làm bão hoà CPU và cho ra con số không diễn giải được.*

**Việc:**

- [ ] 🖐 **Baseline: 10 người dùng đồng thời trong 10 phút.**
- [ ] 🖐 **TẢI MỤC TIÊU: 50 người dùng đồng thời trong 15 phút** (bản đầy đủ là 30 phút).
      *Đây là kịch bản **QUYẾT ĐỊNH** của chỉ số §1.6 đầu tiên.*
- [ ] 🖐 Đo `latency_breakdown` 9 tầng **DƯỚI TẢI** (khác hẳn với đo lúc rảnh) và ghi **đồ thị
      p95 theo thời gian**.
- [ ] 🖐 Kiểm chỉ tiêu **"không tăng dần"**.
      ⚠️ *Quan trọng **ngang** giá trị tuyệt đối: p95 phẳng ở 3.200 ms **tốt hơn nhiều** so với
      p95 khởi đầu 1.800 ms rồi bò lên 5.000 ms.*

**Chạm Dev B:** Dev B chạy **soak 30u/1 giờ** + 2 kịch bản đứt kết nối + runbook cùng ngày.
**Chia khung giờ** — chạy chồng lên nhau thì cả hai bộ số đều hỏng.

**Phải giải thích được:**
- Vì sao "không tăng dần" quan trọng ngang giá trị p95 tuyệt đối? p95 bò lên nghĩa là gì?
- Vì sao bỏ kịch bản đỉnh tải 150 người dùng?

**Cổng ra (DoD):**
- ✅ **BASELINE:** p95 **< 2.500 ms**, lỗi **0%**
- ✅ **TẢI MỤC TIÊU:** p95 **< 4.000 ms**, lỗi **< 1%**, **p95 KHÔNG TĂNG DẦN**

**Minh chứng báo cáo:** đồ thị p95 theo thời gian của **cả hai** kịch bản · bảng
`latency_breakdown` trung bình dưới tải.

---

## Ngày 20 — T7 10/10 — [Nghiệm thu] Chạy lại toàn bộ bộ test và eval cuối

> **Mục tiêu:** **một ảnh chụp toàn bộ bộ test xanh TRONG MỘT LẦN CHẠY.**

**Công cụ dùng lại:** eval harness một lệnh (N13) · `test_rls.py` (N1) · một lệnh test của Dev B (N13).

**Việc:**

- [ ] 🖐 **Chạy MỘT LƯỢT:** CI đầy đủ (gồm cổng chặn ML runtime **và** cổng dung lượng image) ·
      test RLS · eval RAG bằng lệnh đóng gói Ngày 13 · contract test.
- [ ] 🖐 Ghi kết quả **có dấu thời gian** làm bằng chứng cuối.
- [ ] 🖐 Xử lý mọi ca còn đỏ.
- [ ] 🖐 Điền **phần Dev A** của bảng chỉ số nghiệm thu (bảng cuối file này + sheet xlsx).

⚠️ **Nguyên tắc:** *một ảnh chụp toàn bộ bộ test xanh **trong một lần chạy** thuyết phục hơn mười
ảnh chụp rời rạc chụp ở mười thời điểm khác nhau.*

**Chạm Dev B:** Dev B điền 7 chỉ số §1.6 từ dữ liệu thật + soát gói bàn giao 7 hạng mục.
**Chạy nối nhau** để có một lần chạy chung.

**Phải giải thích được:**
- Con số recall@5 cuối cùng đo trên bộ vàng nào, bao nhiêu cặp, config nào? *(Không trả lời được
  cả ba thì con số đó không dùng được trong báo cáo.)*
- Vì sao phải chạy lại **toàn bộ** thay vì dùng lại kết quả đã đo ở Ngày 13?
- Chỉ số nào chưa đạt, nguyên nhân là gì, đã thử phương án nào? *(Chuẩn bị trước — im lặng ở câu
  này mất điểm hơn là chưa đạt.)*

**Cổng ra (DoD):**
- ✅ Ảnh chụp toàn bộ bộ test xanh **trong một lần chạy** có dấu thời gian
- ✅ **EVAL CUỐI: recall@5 ≥ 0,85 · độ phủ trích dẫn ≥ 0,80**, kèm file config đã dùng

---

## Ngày 21 — CN 11/10 — 🏁 MỐC M3 · Báo cáo cuối + tài liệu kiến trúc + ADR

> **Mục tiêu:** gói bàn giao nộp được.

**ADR sinh trong 21 ngày:** ADR-0017 (4 quyết định hợp đồng, N1) · ADR bỏ nhánh A router (N4,
Dev B) · ADR chốt nhánh router (N5, Dev B) · ADR fine-tune ship hay rollback (N7) · ADR cấp vCPU
(N15) · ADR bật/tắt rerank (N8) · ADR phạm vi.

**Việc:**

- [ ] 🖐 Ghép toàn bộ số liệu và biểu đồ vào báo cáo.
- [ ] 🖐 Hoàn thiện sổ ADR — mỗi mục có **bối cảnh, lựa chọn, SỐ ĐO, hệ quả**.
      ⚠️ **ADR không có số đo thì chỉ là ý kiến.**
- [ ] 🤖 Cập nhật ERD khớp migration cuối (V201–V209 + mọi V2xx thêm trong 21 ngày) — *verify:
      đối chiếu bằng `psql` với CSDL thật, không chép từ tài liệu.*
- [ ] 🤖 Vẽ **sơ đồ kiến trúc hai tầng** · **sơ đồ tuần tự một lượt chat** · **sơ đồ máy trạng
      thái LangGraph 8 node**.
- [ ] 🖐 **Viết mục HẠN CHẾ TRUNG THỰC:**
      · model lead scoring huấn luyện trên dữ liệu public/synthetic là **model tham chiếu về
        đường ống**, không phải model dự báo cho một doanh nghiệp cụ thể
      · chưa chạy trên cụm Kubernetes
      · chưa kiểm chứng ở đỉnh tải 150 người dùng
      · phần tích hợp hệ thống ngoài qua giao thức chuẩn nằm ở hướng phát triển
      *Nêu rõ ranh giới **mạnh hơn nhiều** so với công bố một chỉ số đẹp mà không ai biết đến từ đâu.*

**Chạm Dev B:** Dev B ghép **video demo 17 UC** + slide bảo vệ. **Cần giao cho Dev B:** mọi bảng
số liệu phần Dev A để đưa vào slide.

**Phải giải thích được — BA CÂU CHẮC CHẮN ĐƯỢC HỎI, chuẩn bị câu trả lời CÓ SỐ LIỆU:**
- **(a) Dữ liệu thử nghiệm lấy từ đâu và ranh giới trung thực của nó?** — trả lời thẳng là tự
  soạn / công khai / đã ẩn danh, kèm số lượng. Nói rõ mạnh hơn nhiều so với vòng vo.
- **(b) Vì sao chọn kiến trúc hai tầng?** — `ai-service` không nạp model, model chạy ở `inference/`.
  Dẫn số: image < 400 MB, cổng chặn CI 3 gói, p95 suy luận < 480 ms.
- **(c) Làm sao chắc chắn doanh nghiệp A không đọc được dữ liệu của B?** — bốn lớp: RLS FORCE ở
  CSDL · role `ai_app` không phải chủ bảng · lọc `tenant_id` trong chính câu truy vấn vector ·
  khoá cache có `tenant_id`. Dẫn bằng test: `test_rls.py` 3/3 (N1) + bài cách ly qua đường ngôn
  ngữ (N17) + bài cách ly cache (N17).

**🏁 ĐIỀU KIỆN THOÁT M3:** 7/7 chỉ số đạt · gói bàn giao · video demo 17 UC + slide.

**Minh chứng báo cáo:** báo cáo cuối kỳ hoàn chỉnh · sổ ADR ≥ 7 mục mới, **mỗi mục có số đo** ·
ERD khớp 100% migration · bảng nghiệm thu 17/17 UC × trạng thái × số liệu minh chứng.

---
---

# Bảng chỉ số Dev A chịu trách nhiệm

> Lọc từ sheet *Chỉ số nghiệm thu* (54 chỉ số). **Đo xong điền ngay — số đo không ghi lại là số
> đo đã mất.** Điền vào **cả** sheet xlsx (nguồn chính) lẫn bảng này.

| # | Chỉ số | Ngưỡng đạt | Ngày | Giá trị đo được | Kết luận |
|---|---|---|---|---|---|
| 1 | p95 độ trễ endpoint chat | < 4.000 ms và **KHÔNG tăng dần** | N19 | | |
| 2 | Tổng p95 phần suy luận CPU | < 480 ms (classify 60 + embed 120 + rerank 300) | N13, N15 | | |
| 3 | recall@5 trên bộ vàng | **≥ 0,85** (bộ vàng ≥ 80 cặp) | N13, N20 | | |
| 4 | Độ phủ trích dẫn | ≥ 0,80 | N13, N20 | | |
| 5 | Rò rỉ dữ liệu giữa tenant | **0 trường hợp** | N1, N7, N17, N18 | | |
| 6 | Flyway V201–V209 chạy sạch | 9 dòng history, 6 bảng, đủ chỉ mục | N1 | | |
| 7 | Test cách ly tenant trong CI | **3/3 ca xanh** | N1 | | |
| 8 | Dung lượng image `ai-service` | **< 400 MB** (đang 776 MB) | N1, N16, N20 | | |
| 9 | Parity cosine INT8 vs fp32 (encoder base) | ≥ 0,995 | N2 | | |
| 10 | Số chiều vector khớp lược đồ | **1024** — `INSERT` thật không lỗi | N2 | | |
| 11 | Chênh lệch recall@5 (1 tenant vs 20 tenant) | < 3 điểm | N6 | | |
| 12 | Hybrid thắng dense-only | **≥ 5 điểm recall@5** | N6 | | |
| 13 | Baseline recall@5 của model pretrained | Đo và **LƯU trước** khi reindex | N6 | | |
| 14 | Parity cosine bản **FINE-TUNE** | ≥ 0,995 — không đạt thì rollback | N7 | | |
| 15 | Hiệu số recall@5 fine-tune vs pretrained | KTC 95% paired bootstrap **không chứa 0** | N7 | | |
| 16 | Thời gian reindex toàn bộ chunk | Đo thật; **0 giây kho tri thức trống** | N7, N11 | | |
| 17 | Cổng quyết định bật rerank | ≥ 5 điểm nDCG@5 **VÀ** p95 < 4 s | N8 | | |
| 18 | 30 câu hỏi ngoài phạm vi trả rỗng đúng | **30/30** | N10 | | |
| 19 | Eval harness tái lập được | Chạy 2 lần ra cùng con số; mỗi số kèm config | N13, N20 | | |
| 20 | Cách ly tenant qua **ĐƯỜNG NGÔN NGỮ** | Hỏi A về tài liệu B → phải **TỪ CHỐI** | N17 | | |
| 21 | Cách ly bộ nhớ đệm ngữ nghĩa | 2 tenant → 2 câu trả lời từ 2 kho tri thức | N17 | | |
| 22 | PII trong log *(cùng Dev B)* | grep tự động = **0** | N16, N17 | | |
| 23 | Năm bài kiểm thử bảo mật *(cùng Dev B)* | 5/5 đạt (bài "quyền công cụ" ghi *không áp dụng*) | N17, N20 | | |
| 24 | Baseline 10 người dùng / 10 phút | p95 < 2.500 ms, lỗi 0% | N19 | | |
| 25 | Tải mục tiêu 50 người dùng / 15 phút | p95 < 4.000 ms, lỗi < 1%, KHÔNG tăng dần | N19 | | |
| 26 | Nguồn dữ liệu thử nghiệm *(cùng Dev B)* | Ghi rõ tự soạn/công khai hay đã ẩn danh | N18, N21 | | |
| 27 | Số use case hoàn thành *(cùng Dev B)* | 17/17 UC | N20 | | |

---

# Ba mốc — điều kiện thoát và hành động khi trượt

| Mốc | Hạn | Điều kiện thoát | 🚨 Trượt thì làm gì |
|---|---|---|---|
| **M1** Nền tảng dữ liệu | hết **N7** (27/09) | Tài liệu thật vào chunks · test cách ly tenant xanh · hybrid thắng dense ≥ 5 điểm · router chạy trong `ai-classify` | **Cắt rerank khỏi N8** và **bỏ semantic cache ở N16** |
| **M2** Demo luồng chính | hết **N14** (04/10) | 17/17 UC có endpoint/worker + 1 test + 1 con số · có video luồng trả lời và luồng lead | **Cắt UC038 (N17)**, dồn N15–16 sang hoàn thiện UC còn thiếu |
| **M3** Nghiệm thu | hết **N21** (11/10) | 7/7 chỉ số đạt · gói bàn giao · video demo 17 UC + slide | Không còn đường lùi — đây là hạn cuối |

---

# Ba buổi bắt buộc làm chung với Dev B

| Ngày | Buổi | Thời lượng | Vì sao không làm riêng được |
|---|---|---|---|
| **N1** | Chốt 4 mâu thuẫn hợp đồng → ADR-0017 | buổi sáng | Cả hai đều phụ thuộc; chốt muộn thì phải sửa cả code lẫn hợp đồng lẫn phần Track A đã gọi |
| **N2** | Gõ tay 200 câu hỏi thật | **~3 giờ** | Tài sản giá trị nhất của phần thực nghiệm. Gán nhãn **độc lập** rồi mới đối chiếu (N3, đo Cohen's kappa) |
| **N8** | Chốt cấu trúc `AgentState` | trước khi ai code node nào | Điểm hai đường gặp nhau. **Nguồn conflict số một** nếu bỏ qua |

---

# Nhịp làm việc bắt buộc

- **Đồng bộ 15 phút đầu ngày** — mỗi người đúng 3 câu: hôm qua xong gì, hôm nay làm gì, đang
  vướng gì. ⚠️ **Vướng quá NỬA NGÀY là phải nói ra và đổi hướng** — ở lịch 3 tuần, im lặng một
  ngày là mất 5% toàn dự án.
- **Merge mỗi ngày** — mỗi người một nhánh feature, merge vào nhánh chính ít nhất 1 lần/ngày.
- **Rà soát chéo bản nhẹ** — **không ai merge phần của mình mà không có người kia đọc qua PR.**
  Mỗi lần 10–15 phút.
- **Migration** — chỉ ghi dải **V2xx, bắt đầu từ V210**. `ls migration/` trước khi đặt tên: hai
  người tạo cùng số là lỗi merge khó chịu nhất và xảy ra rất thường.
- **Ghi số liệu ngay khi đo** — đừng để dồn tới Ngày 20.

---

# Việc cần làm sớm, không thuộc ngày nào

- [ ] 🖐 Tách nhánh `feat/ai-a` (cả hai đang cùng `feat/base`) + `.github/CODEOWNERS` theo bảng
      ranh giới ở mục *Ranh giới file* trên. Càng để lâu càng rối vì cả hai sắp chạm `service.py`
      và `state.py`.
- [ ] 🖐 **Ba tài khoản, theo hạn:** Kaggle xác minh số điện thoại **trước tối Ngày 4** (không
      verify thì không bật được GPU, đổ cả Ngày 5–7) · `ANTHROPIC_API_KEY` **trước Ngày 9** ·
      instance cloud **cho Ngày 18**.
- [ ] 🤖 Ghim phiên bản phụ thuộc bằng `uv pip compile --generate-hashes` (`base.txt` còn `>=`) ·
      ghim `ruff` trong CI (đang `pipx run ruff` không ghim — ruff ra bản mới là CI đỏ mà không
      ai sửa gì).
- [ ] 📖 `docs/adr/0015` dòng 221: khối lệnh kiểm chứng vẫn grep 5 gói — tự mâu thuẫn với quyết
      định của chính ADR đó. **Cố ý chưa đụng** (ADR là bản ghi quyết định) — quyết cách xử lý.

---

# Đọc thêm ở đâu — đừng đoán

| Cần biết | Đọc |
|---|---|
| Việc từng ngày, ngưỡng từng chỉ số | `docs/Ke-hoach-21-ngay-Module-AI-CRM.xlsx` — **nguồn chính** |
| Cây thư mục, "đặt file mới ở đâu" | `ai-service/README.md` · `ai-service/CLAUDE.md` |
| Vì sao chọn như vậy | `docs/adr/` — 16 ADR (0001–0016), ADR kế tiếp là **0017** |
| Đặc tả 20 UC AI (17 trong phạm vi) | `docs/Dac-ta-UseCase-Module-AI.docx` |
| Kiến trúc hai tầng, ngân sách độ trễ | `docs/MASTER_PLAN_AI_CRM_v8.md.docx` §3.2, §5.3 |
| Hợp đồng liên làn | `docs/openapi/` · `docs/events/` — nháp ở `docs/contracts/` |
| Bảo mật, dữ liệu cá nhân | `docs/threat-model.md` — T1–T8 |
| Cột · kiểu · khoá của bảng | `docs/erd-mermaid.md` |
| Quy ước code Python chi tiết | `.claude/rules/ai-service.md` · `.claude/rules/rag-eval.md` |

**Luật nào không truy được về `docs/` thì ghi `[CẦN XÁC NHẬN]` và hỏi — đừng đoán.**
