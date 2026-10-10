# Kế hoạch 21 ngày — Dev A · Kho tri thức & Trả lời

> **8 Use Case:** UC018 · UC019 · UC020 · UC023 · UC025 · UC026 · UC027 · UC041
> **Kiêm:** hạ tầng CSDL, RLS, model nhúng, hybrid search, 4 node `guard`/`retrieve`/`generate`/`postguard`,
> eval harness, benchmark, triển khai, load test.
> **Lịch:** Ngày 1 = T2 21/09/2026 → Ngày 21 = CN 11/10/2026.

**Nguồn sự thật là `docs/Ke-hoach-21-ngay-Module-AI-CRM.xlsx`.** File này chỉ là bản lọc sẵn
phần của Dev A để mở cạnh code. **Số nào lệch thì xlsx đúng, file này sai** — sửa file này.

Thứ tự ưu tiên khi tài liệu mâu thuẫn: `repo` > `docs/adr/` > Master Plan > xlsx > file này.

---

## 🔁 Đổi kế hoạch tuần 3 — người dùng chốt 10/10/2026

Phần này **cố ý lệch xlsx**, xlsx chưa sửa theo.

| Ngày | Trước | Sau |
|---|---|---|
| N14 | Mốc M2: chạy luồng chat, video 3 luồng, biểu đồ `latency_breakdown`, viết báo cáo 6 UC, bảng 7 chỉ số giữa kỳ | **Chỉ chạy trọn luồng chat.** Bốn việc còn lại hoãn cùng N21 |
| N15 | Benchmark rút gọn + chốt cấp vCPU | **Thêm Khối A trước benchmark: rerank thật `BAAI/bge-reranker-v2-m3`**, thay bản giả Jaccard, đóng ô N8 "nDCG@5 có/không rerank" |
| N16 | Giảm image < 400 MB, semantic cache, tối ưu độ trễ | **Bỏ.** Ô ngày này dùng cho **buổi đọc số liệu kỹ thuật** |
| N18 | Triển khai 1 instance cloud HTTPS, test RLS ở môi trường triển khai, dữ liệu doanh nghiệp thật | **Hoãn** *(đổi lần hai)* — làm khi lên production |
| N19 | Load test 10 người / 10 phút và 50 người / 15 phút | **Hoãn** |
| N20 | Chạy lại toàn bộ bộ test + eval cuối trong một lượt, điền bảng chỉ số | **Hoãn** *(đổi lần hai)* — làm khi lên production |
| N21 | Mốc M3: báo cáo cuối, ADR, ERD, sơ đồ, mục hạn chế | **Hoãn** |

Thứ tự làm sau khi đổi: N13 → N14 → N15 (**rerank thật**, rồi benchmark) → **N16 đọc số** → **N17
là ngày cuối của đợt**. Ngả (c) của N14 chạy bù khi có `router_model.onnx`.

**Đổi lần hai, 10/10/2026 — người dùng chốt hoãn N18 và N20.** Sau N17, người dùng chuyển sang các
service khác (java-core, gateway, web-dashboard, web-widget), nối và kiểm các UC AI đã làm **trên
giao diện** cho tới khi chạy ổn. Lên production thì quay lại N18 rồi N20. Nội dung hai ngày giữ
nguyên bên dưới.

**Hệ quả:**

- Ba ô của N19 ghi **"chưa đo (hoãn)"**: p95 `/v1/ai/chat` dưới tải, baseline 10 người, tải mục
  tiêu 50 người. Đây là chỉ số §1.6 đầu tiên.
- **Không có lượt eval cuối:** số recall@5 và độ phủ trích dẫn mới nhất vẫn là của N13 (và của N15
  cho phần rerank). Bảng chỉ số và sheet xlsx chưa được điền phần N20.
- **Chưa có môi trường triển khai:** chưa test RLS ở nơi thật sự chạy, chưa gọi chat qua HTTPS, chưa
  nạp dữ liệu doanh nghiệp thật, chưa bật thanh toán Gemini (`cost_vnd` vẫn 0). Contract test của
  Dev B ở N18 và phần chỉ số §1.6 Dev B điền ở N20 cũng lùi theo — báo Dev B.
- Image `ai-service` vẫn **776 MB**, cổng CI dung lượng (ngưỡng 400 MB, ADR-0015/0017) không đạt.
- Không có semantic cache, nên bài (2) "cách ly cache" của N17 ghi **"không áp dụng"** kèm lý do.
- N15 nặng thêm một khối, nhiều khả năng tràn sang buổi thứ hai. Rerank không còn là mục cắt đầu
  tiên trong "Thứ tự cắt khi trượt lịch".

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

> **Đổi 05/10/2026 — thay cho phân tầng bên dưới:** AI viết **mọi ô** của mỗi ngày, kể cả ô 🖐
> và dữ liệu đánh giá (bộ vàng, tập test ý định — báo cáo ghi rõ nguồn là AI). Ô được tick khi
> **code + test + minh chứng** đã xong, kèm chú thích `(AI viết DD/MM)`. Cuối mỗi ngày AI viết
> ghi chú ôn tập ở [`docs/on-tap/`](../docs/on-tap/): hệ thống chạy thế nào, vì sao chọn như vậy,
> trả lời sẵn các câu "Phải giải thích được". Luật "không giải thích được thì chưa tick" chuyển
> thành **đọc ghi chú ôn tập trước buổi bảo vệ**.

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

Đây là khối lượng lõi thật sự. Mọi thứ khác là phụ trợ quanh mười thứ này.
*Từ 05/10: nhãn 🖐 nghĩa là "hội đồng chắc chắn hỏi" — ghi chú ôn tập phải viết kỹ nhất ở đây.*

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
| 10 | ~~Khoá semantic cache có `tenant_id`~~ — **bỏ cùng N16 (10/10)** | ~~N16~~ | Thiếu `tenant_id` = rò rỉ giữa doanh nghiệp, 1 trong 7 chỉ số §1.6 |

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

**KHÔNG cắt:** nguyên một use case · tập test đóng băng · test cách ly tenant trong CI · bộ vàng
≥ 80 cặp.

*Đổi 10/10/2026: người dùng chốt bỏ cả Ngày 16, gồm semantic cache và việc giảm image < 400 MB —
xem mục "Đổi kế hoạch tuần 3" ở đầu file. Cùng ngày, mục 1 (rerank) **không còn là việc cắt**:
người dùng chốt làm rerank thật với `bge-reranker-v2-m3` ở Ngày 15, Khối A.*

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

- [x] 🖐 **Bộ 20 tệp mẫu** PDF/DOCX/TXT/MD/HTML + **5 tệp lỗi** (quá 20 MB, sai MIME, PDF scan
      không trích được text).
      ⚠️ *Đây cũng là nguồn của bộ vàng Ngày 6 — chọn tài liệu có **nội dung nghiệp vụ thật**
      (bảng giá, chính sách bảo hành, quy trình đổi trả), không lấy văn bản ngẫu nhiên.*
      Kiểm kỹ: **không chứa dữ liệu cá nhân** trước khi commit (Nghị định 13).
- [x] 🤖 Route `POST` tải lên theo tên đã chốt — *verify: `tenant_id` lấy từ `get_tenant_id`
      của `src/api/deps.py` (header `X-Tenant-Id`), **không** từ body/query/path.*
- [x] 🤖 Kiểm phần mở rộng + dung lượng + hạn mức `max_documents` của gói — *verify: ngưỡng
      **cảnh báo 80%** và **chặn 100%** là hai nhánh khác nhau, không gộp.*
- [x] 🤖 Ghi bản ghi `PENDING` — *verify: `title` 3–255 ký tự (ADR-0020), `description` ≤ 500,
      `language` ∈ {`vi`,`en`}; ràng buộc `ck_doc_failed` của V202 không bị vi phạm.*
- [x] 🖐 **Lưu tệp theo đường dẫn CÓ CHỨA `tenant_id`** — cô lập ngay ở tầng kho lưu trữ chứ
      không chỉ ở truy vấn. *(Claude viết theo yêu cầu; bạn đã tự giải thích được — 27/09/2026)*
- [x] 🖐 Trùng tiêu đề → **tăng `version`**, không ghi đè (uq theo `(tenant, title, version)`).
      *(Claude viết theo yêu cầu; bạn đã tự giải thích được — 27/09/2026)*
- [x] 🤖 Trả `202` + `job_id`; phát sự kiện với **khoá phân vùng = `tenant_id`** — *verify: khoá
      phân vùng đúng là `tenant_id`, nếu không thì thứ tự sự kiện trong một tenant không đảm bảo.*
- [ ] 🖐 **Test 5 mã lỗi tách bạch:** `413` (tệp > 20 MB) · `415` (sai định dạng) · `409` (chạm
      hạn mức gói) · `422` · `PARSE_NO_TEXT_EXTRACTED`.
      *Đây là điểm 1 trong "Mười một điểm cần chốt" của đặc tả UC.*
      **27/09: 4/5 xong** (413/415/409/422 — `docs/report/uc018-e2e-2026-09-27.md`).
      `PARSE_NO_TEXT_EXTRACTED` chỉ đo được khi có parser → tick ở Ngày 4.
      **27/09 (phiên Ngày 4): mã thứ 5 đã có test** — `test_pdf_scan_chuyen_failed_kem_parse_no_text_extracted`
      (`tests/integration/test_phan_tich_tai_lieu.py`). Đủ 5/5 → tick khi bạn tự giải thích lại được.

**File sẽ đụng:** `src/api/v1/router.py` · `src/api/v1/endpoints/` · `src/ai/rag/ingest/` ·
`src/ai/service.py` (facade — Dev B duyệt) · `data/` (tệp mẫu)

**Chạm Dev B:** 🤝 **Gán nhãn chéo tập test 200 mẫu** — mỗi người gán **ĐỘC LẬP** rồi mới đối
chiếu, đo **Cohen's kappa**, ngồi lại giải quyết mọi ca bất đồng.
*Bất đồng nhãn ở đây biến thành sai số hệ thống ở MỌI chỉ số về sau.*
**Phải giao:** không có. **Cần nhận:** không có.
**27/09: dời sang Ngày 4** — buổi gõ tay 200 câu chưa diễn ra nên chưa có tập để gán chéo.

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
      *(27/09: Claude viết — `rag/ingest/phan_tich.py` + `tien_trinh.py`; test giết-rồi-dựng-lại
      `test_qua_gio_thi_giet_tien_trinh_con_va_dung_pool_moi`. Chờ bạn đọc từng dòng rồi tick.)*
- [ ] 🖐 **`normalize_vi` — tự gõ.** Xử lý zero-width, NFD/NFC, `hoà`/`hòa`, ký tự lặp.
      ⚠️ **MỘT HÀM DUY NHẤT dùng cho CẢ hai đầu** — lúc nạp và lúc truy vấn.
      *Hai hàm khác nhau là lỗi thầm lặng: không có exception, chỉ có recall tụt.*
      *(27/09: Claude viết theo yêu cầu — `src/ai/rag/chuan_hoa.py`. Tick khi bạn tự giải thích lại được.)*
- [ ] 🖐 **Hàm chia đoạn — tự gõ.** ~500 token, **GIỮ số trang và heading** để trích dẫn được
      (ví dụ `"Bảng giá 2026 > Gói Pro"`).
      *(27/09: Claude viết theo yêu cầu — `rag/ingest/chia_doan.py`. Tick khi bạn tự giải thích lại được.)*
- [ ] ~~🤖 Ghi `content_segmented` bằng `pyvi`~~ → **ĐỔI 27/09 (bạn chốt):** `content_segmented` là
      cột **GENERATED** `to_tsvector('simple', knowledge.f_unaccent(content))` theo **âm tiết**;
      `pyvi` chỉ chạy **phía câu hỏi** (`tsquery.py`) để dựng `<->`. Lý do đã đo: (1) pyvi không
      ghép được từ trong câu không dấu; (2) Postgres coi `_` là dấu tách nên `chính_sách` vẫn thành
      hai âm tiết — tách từ phía tài liệu không đổi được chỉ mục. Ghi trong V210.
      *verify: `test_cau_khong_dau_tim_duoc_doan_co_dau`, `test_lien_ke_loai_doan_…`.*
- [ ] 🖐 `tsvector` bọc `unaccent` trong hàm **IMMUTABLE** (bắt buộc để đánh chỉ mục được).
      *(27/09: Claude viết theo yêu cầu — V210 `knowledge.f_unaccent`. Đã kiểm ngược: đổi thành
      STABLE thì V210 lỗi `generation expression is not immutable`. Tick khi bạn tự giải thích lại được.)*
- [ ] 🖐 **Dựng phrase query — tự gõ:** toán tử **liền kề** cho cụm nhiều âm tiết, phép **OR**
      giữa các từ.
      ⚠️ *Dùng `AND` sẽ trả rỗng ngay khi khách gõ thừa một từ.*
      *(27/09: Claude viết theo yêu cầu — `src/ai/rag/tsquery.py`. Tick khi bạn tự giải thích lại được.)*
- [ ] 🤖 Nếu cần cột mới → migration **bắt đầu từ V210** — *verify: không sửa V201–V209 (đã chạy),
      không đụng dải V1xx của Track A.*
      *(27/09: `V210__unaccent_va_lan_tu_khoa.sql` — Flyway 10 chạy V201→V210 sạch trên CSDL dùng
      một lần; **CSDL dev đã lên v210** (`scripts/migrate-ai.sh`, 27/09).)*
- [ ] 🖐 Unit test: `normalize_vi` · `build_tsquery` với câu **KHÔNG DẤU** · PDF scan phải chuyển
      `FAILED` kèm `error_message`.
      *(27/09: Claude viết theo yêu cầu — `tests/unit/test_{normalize,tsquery,chia_doan,phan_tich}.py`,
      `tests/integration/test_{tim_khong_dau,phan_tich_tai_lieu}.py`. `pytest tests` **218 passed**.
      Kiểm ngược: OR→AND, bỏ NFC, bỏ lặp tiêu đề bảng, bỏ điều kiện PENDING → đều đỏ.)*

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
*27/09: `python -m tests.eval.ngay4_minh_chung --dsn …` in đủ 4 bảng. Số đo lần đầu: trích xuất
20/20 tệp hợp lệ (PDF scan ra đúng `PARSE_NO_TEXT_EXTRACTED`) · 190 đoạn, trung vị **87** token ước
lượng (không phải ~500 — ranh giới heading là ranh giới đoạn, xem `chia_doan.py`) · khớp không dấu
**28,9% → 88,8%**, top-5 `ts_rank` **10,7% → 40,1%** (187 truy vấn sinh từ heading). Bản đầy đủ:
`docs/report/uc019-ngay4-2026-09-27.md`.*

---

## Ngày 5 — T6 25/09 — UC019 (2/2) Nhúng theo lô + worker Kafka + DLQ

> **Mục tiêu:** tài liệu thật nằm trong `knowledge_chunks` với vector, có chỉ mục HNSW.

**Điều kiện vào:** chunk có heading từ Ngày 4. Bộ topic Kafka đã chốt (Ngày 1, Dev B).

**Việc:**

- [ ] 🤖 `/v1/embed/batch` — lô **32 đoạn** — *verify: không gom toàn bộ vector vào RAM; một tài
      liệu 3.000 đoạn phải chạy được mà RSS không phình.*
      *(27/09: `src/ai/rag/ingest/nhung.py` + client `src/ai/inference/{clients,remote}.py`. ai-embed
      CHƯA có ⇒ `AI_MODE=mock` (seed cố định, nhãn `mock-hash-1024`). `tracemalloc` 3.000 đoạn: đỉnh
      **2,2 MB** (gom hết: 100,4 MB). e2e 3.840 đoạn: RSS đỉnh worker +38 MB so với tài liệu 413 đoạn.)*
- [ ] 🖐 Semaphore giới hạn **ĐÚNG 1 job nạp đồng thời** (dùng chung hàng đợi với UC020 ở N11).
      *(27/09: Claude viết theo yêu cầu — `XuLyTaiLieu._mot_job` ở `src/worker/consumers/tai_lieu.py`,
      dùng chung cho luồng Kafka và bộ quét; nhả trong lúc chờ thử lại. Tick khi bạn tự giải thích lại.)*
- [ ] 🖐 **Worker thật thay cho `NotImplementedError`** (`src/worker/main.py:38`) — tự gõ phần
      cốt lõi: `enable_auto_commit=False`, `max_poll_interval_ms=600000`, **xác nhận offset SAU
      khi xử lý thành công**.
      *Auto-commit đánh dấu xử lý xong TRƯỚC khi thực sự xong; một lần pod chết là mất sự kiện.*
      *(27/09: Claude viết theo yêu cầu — `src/worker/main.py` (`Worker._tao_consumer`,
      `_xu_ly_mot`, `chay`). Kiểm ngược: xác nhận offset trước khi xử lý ⇒ test khởi động lại đỏ.)*
- [ ] 🖐 Chống trùng bằng `INSERT ... ON CONFLICT DO NOTHING` vào `processed_events` — **0 dòng
      ảnh hưởng thì bỏ qua sự kiện**. *Giao nhận ít nhất một lần: nhận trùng là chắc chắn, không
      phải rủi ro.*
      *(27/09: bảng là **`ai.processed_events`** (V211), KHÔNG phải `analytics.` — `ai_app` không có
      USAGE trên schema của Track A (ADR-0024). `processed_event_repository.ghi_nhan`, ghi CÙNG
      transaction với bước nhận việc trong `service.nap_tai_lieu`. Tick khi bạn tự giải thích lại.)*
- [ ] 🤖 Chuyển tài liệu sang `READY` + `chunk_count` + `indexed_at`; lỗi vĩnh viễn đẩy sang
      **DLQ** — *verify: phân biệt lỗi tạm thời (retry) và lỗi vĩnh viễn (DLQ); đừng đẩy hết vào DLQ.*
      *(27/09: `service.nap_tai_lieu`. DLQ `ai.dlq` chỉ cho sự kiện KHÔNG thành trạng thái tài liệu
      (sai lược đồ, CSDL chết 3 lần); `PARSE_*` → `FAILED` trên SCR033, không DLQ; S3/ai-embed chết
      → `PENDING`, thử lại 5 s/30 s, 3 lượt → `FAILED INGEST_RETRY_EXHAUSTED`. ADR-0024 quyết định 4–5.)*
- [ ] 🤖 Endpoint trả **6 bước tiến độ** của job.
      *(27/09: `GET /v1/ai/kb/ingestion-jobs/{job_id}` — `service.tien_do_nap` + `rag/ingest/tien_do.py`;
      DTO bám `CongViecNap`. Hợp đồng ai-service → java-core còn TODO.)*
- [ ] 🖐 **Chạy `create_hnsw_index.sql` LẦN ĐẦU** — sau khi đã có chunk thật.
      `m=16`, `ef_construction=64`, `CONCURRENTLY`.
      *(27/09: chạy trên CSDL e2e sau 4.488 đoạn thật — `scripts/e2e-uc018.sh nap`; `\di+` thấy
      `ix_chunk_embedding` hnsw 6,8 MB, EXPLAIN tự chọn Index Scan. **CSDL dev chưa**: chưa lên V211,
      chưa có đoạn nào.)*
- [ ] 🖐 Test: ép lỗi lược đồ để kiểm chứng DLQ · **restart worker giữa chừng**, job phải hoàn
      tất hoặc được nhận lại **nguyên vẹn**.
      *(27/09: Claude viết theo yêu cầu — `tests/integration/test_worker_kafka.py` (Kafka thật: DLQ,
      SIGTERM giữa chừng, chết cứng giữa chừng) + `test_nap_tai_lieu.py` (thẻ sở hữu, bộ quét).
      `pytest tests` **291 passed**; kiểm ngược 7/7 đỏ đúng chỗ.)*

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
*27/09: `docs/report/uc019-ngay5-2026-09-27.md` (e2e java-core → Kafka → worker, `AI_MODE=mock`):
44 tài liệu thật nạp xong trong 6,3 s · PDF 100 trang **19,4 s**, 413 đoạn, 21 đoạn/giây (97% là
`find_tables` của PDF dày bảng — nợ) · MD 3.840 đoạn 5,2 s, 742 đoạn/giây · bản tin DLQ kèm header
`dlq.*` · 2 biểu đồ 6 bước + CSV · `\di+` HNSW. Thời gian KHÔNG gồm nhúng thật — đo lại Ngày 7.*

---

## Ngày 6 — T7 26/09 — Hybrid Search + bộ vàng v1 + khai thác dữ liệu fine-tune

> **Mục tiêu:** hybrid thắng dense-only ≥ 5 điểm recall@5, và phóng GPU fine-tune qua đêm.

**Điều kiện vào:** có chunk thật + chỉ mục HNSW và GIN. Chỗ đặt bộ vàng đã chốt (Ngày 1).

**Việc:**

- [x] 🖐 **MỘT câu SQL gộp hai làn — tự gõ, đây là code lõi nhất của phần truy hồi.** *(AI viết 27/09)*
      Làn vector (HNSW cosine) + làn từ khoá (GIN tsvector), hợp nhất bằng **RRF hằng số 60**.
      **Mỗi làn 30 ứng viên.**
      ⚠️ Chỉ dùng **THỨ HẠNG**, không dùng điểm thô — nên không phải chuẩn hoá hai thang điểm
      khác nhau. **KHÔNG "cải tiến" RRF thành weighted sum** (ADR-0006).
      **27/09: Claude viết theo yêu cầu** — `src/ai/rag/retrieve/hybrid.py` (toán tử `<=>` khớp
      `vector_cosine_ops`; lọc tenant + `READY` + model/version ở cả hai làn), 23 test tích hợp ở
      `tests/integration/test_tim_kiem_lai.py`, **kiểm ngược 11/11** đột biến đỏ đúng test. Tick
      khi bạn tự giải thích được.
- [x] 🖐 `SET LOCAL hnsw.ef_search=100` và `hnsw.iterative_scan='relaxed_order'` trong **CÙNG
      transaction** với truy vấn.
      **27/09:** `hybrid.dat_tham_so_truy_hoi` — `set_config(..., true)` + `plan_cache_mode =
      force_custom_plan`. Khoá bởi `test_tham_so_hnsw_chet_theo_transaction` và
      `test_quet_lap_cuu_tenant_nho_trong_kho_dong` (tắt quét lặp → tenant nhỏ hụt kết quả).
- [x] 🖐 **Bộ vàng v1: 40–50 cặp** câu hỏi/đoạn đúng từ 20 tệp mẫu Ngày 3, đặt đúng chỗ đã chốt.
      *Bắt buộc có TRƯỚC khi đo — recall@5 phải có mẫu số.*
      **27/09: đổi thành 100 cặp** — Gemini sinh câu hỏi CHỈ từ mục lục, bạn gán căn cứ (tệp +
      câu trích). Công cụ: `python -m tests.eval.bo_vang muc-luc | doan | kiem`.
      **06/10 — xong (AI viết 06/10):** AI làm cả hai bước (ADR-0020 mục 5). 134 ứng viên viết từ
      mục lục, khoá sha256 `06ea38a5…` trước khi xem đoạn; cắt ở 100 câu có đáp án + 12 ngoài kho.
      `bo_vang kiem` SẠCH, đóng băng sha256 `323baf73…` (bản LF, `.gitattributes` ghim `eol=lf`).
- [x] 🖐 **ĐO BASELINE (model pretrained):** dense-only vs sparse-only vs hybrid · **1 tenant vs
      20 tenant**. *(AI chạy 06/10)*
      ⚠️ *Đây là MỐC SO SÁNH DUY NHẤT của phần fine-tune — không đo hôm nay thì ngày mai không
      có gì để so.* Lưu bảng này lại cẩn thận.
      **27/09:** câu ⚠️ trên hết hiệu lực vì fine-tune đã bỏ — baseline này giờ là mốc cho phép so
      fp32 ↔ INT8 (ADR-0021). **Công cụ sẵn**, chờ ai-embed + bộ vàng: `tests/eval/gieo_kho.py`
      (`nap` tenant gốc · `nhan-ban --den 20` · `xoa`) · `tests/eval/danh_gia_truy_hoi.py` (`chay`
      · `so-sanh`) · 4 cấu hình `tests/eval/configs/e3_*.yaml`. Đã chạy thử trên CSDL dev bằng mock
      (20 tenant × 190 đoạn) rồi dọn sạch.
      **06/10 — số thật** (bge-m3 INT8 qua ai-embed thật, `inference/src/roles/embed.py` thay bản
      giả của Dev B): recall@5 dense **0,800** · sparse 0,530 · hybrid 0,740 trên đường container
      (số chính thức; chạy tay trên macOS ra dense 0,790 — vector INT8 phụ thuộc nền tảng); 20 tenant y hệt.
      Minh chứng: [`docs/report/uc023-ngay6-2026-10-06.md`](../docs/report/uc023-ngay6-2026-10-06.md).
- [ ] ~~🤖 Khai thác cặp huấn luyện từ **chính kho tri thức**~~ — **BỎ khỏi Ngày 6 (27/09, người
      dùng quyết: ra kết quả trước).** *verify gốc: `positive` = (câu hỏi sinh
      từ đoạn, đoạn đó); `hard negative` = đoạn **lọt top-5 hybrid nhưng SAI** — chỉ có được SAU
      khi hybrid chạy, nên đúng thứ tự là hôm nay.*
- [ ] ~~🖐 **Tách tập giữ lại theo TÀI LIỆU, không theo đoạn.**~~ — **BỎ cùng fine-tune (27/09).**
      *Tách theo đoạn thì các đoạn cùng một tài liệu lọt cả hai bên, model học thuộc văn phong
      tài liệu đó và chỉ số bị thổi phồng.*
- [ ] ~~🤖 Notebook `07_finetune_embedding.ipynb`~~ — **BỎ khỏi Ngày 6 (27/09).** *verify gốc: ghim
      seed, ghim phiên bản thư viện, ghi hash dữ liệu, xuất metric ra file (4 điều kiện tái lập).*
- [ ] ~~🖐 **CUỐI NGÀY: phóng notebook lên Kaggle GPU.**~~ — **BỎ khỏi Ngày 6 (27/09).** Ngày 7
      (export, parity, reindex bản fine-tune) phụ thuộc mục này — cần chốt lại Ngày 7.

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
- ❌ **Hybrid thắng dense-only ≥ 5 điểm recall@5** — **TRƯỢT 06/10:** hybrid − dense = −6,0 điểm,
  KTC 95% [−13,0; +1,0] (container; macOS: −5,0 [−12; +2]). Làn từ khoá yếu (0,53) kéo RRF xuống ở câu có dấu; hybrid chỉ thắng ở câu
  không dấu (0,43 vs 0,29). Chưa đổi gì — chờ quyết định (xem ghi chú ôn tập Ngày 6).
- ✅ **Chênh lệch recall@5 giữa 1 tenant và 20 tenant < 3 điểm** — Δ = 0,0. Giới hạn: bộ tối ưu
  không dùng HNSW ở 190 đoạn/tenant (tìm chính xác), nên chưa thử thách đường HNSW lọc sau.
- ~~✅ Notebook đang chạy trên Kaggle GPU~~ — bỏ cùng fine-tune (27/09)

**Minh chứng báo cáo:** bảng 3 dòng (dense / sparse / hybrid) · bảng 1 tenant vs 20 tenant ·
**bảng baseline recall@5 và nDCG@5 của model pretrained** (cột đối chứng của toàn bộ phần
fine-tune) · số cặp huấn luyện khai thác được + tỉ lệ hard negative.

---

## Ngày 7 — CN 27/09 — 🏁 MỐC M1 · Chốt encoder INT8 + bảng thoát M1

> **Viết lại 06/10/2026.** Bản cũ là vòng fine-tune (export, parity, reindex, so fine-tune ↔
> pretrained). Bản đó đã bỏ hẳn từ 27/09 — xem [ADR-0026](../docs/adr/0026-bo-fine-tune-embedding.md).
> Ngày 06/10 người dùng bỏ thêm phép đo fp32 ↔ INT8, vì muốn **hệ thống chạy được trước**
> ([ADR-0021](../docs/adr/0021-cong-parity-int8-truot-phan-xu-bang-recall.md) cập nhật 2).

> **Mục tiêu:** chốt encoder sẽ ship, ghi đủ quyết định, đóng M1 bằng bảng thật — kể cả ô ❌.

**Việc:**

- [x] 🖐 **Chốt encoder: `bge-m3-int8`, pretrained, chạy lô 1** trong `ai-embed`. Căn cứ là recall@5
      tuyệt đối trên bộ vàng v1 (dense 0,800 · hybrid 0,740, đường container), không phải phép so
      với fp32. *(AI viết 06/10)*
- [x] 🤖 **ai-embed chạy được trong compose:** `inference/compose.inference.yml`, cổng **8091** (8081
      là của java-core), mount `../artifacts`. Image `ai-inference:dev` 383 MB (< 900 MB); container
      cho lại đúng recall@5 của bản chạy tay. *(AI viết 06/10)*
- [x] 🖐 **Ghi quyết định Ngày 6–7** *(AI viết 06/10)*:
      - ADR-0026: bỏ fine-tune;
      - ADR-0021 cập nhật 2: ship INT8, bỏ phân xử fp32, vector phụ thuộc nền tảng;
      - ADR-0006 cập nhật 06/10: 30 ứng viên, kết quả E3, giữ hybrid, không cắt rerank.
- [x] 🤖 `artifacts/MODEL_REGISTRY.md`: INT8 → ship; fp32 → bỏ đo đối chứng. *(AI viết 06/10)*
- [ ] ~~Export / parity / reindex bản fine-tune · `MODEL_CARD_embedding` v2 · script reindex~~ — bỏ
      cùng fine-tune (ADR-0026). Nhúng lại toàn kho vẫn cần khi đổi model **hoặc đổi nền tảng
      `ai-embed`** — làm ở Ngày 11 (UC020, API reindex).
- [ ] ~~Đo Recall@5 fp32 ↔ INT8~~ — bỏ 06/10. Lệnh tái lập nằm ở ADR-0021 nếu sau này muốn đo.

**Ràng buộc mới, giữ cho mọi ngày sau:** kho và câu hỏi phải nhúng bằng **cùng một đường `ai-embed`**
(cùng image). Cùng `int8-71e2aa91`, nhưng vector trên macOS lệch vector trong container (cos min
0,982), vì INT8 động khuếch đại sai khác số học giữa nền tảng.

**Phải giải thích được** (trả lời ở [`docs/on-tap/ngay-07-moc-m1.md`](../docs/on-tap/ngay-07-moc-m1.md)):
- Vì sao ship INT8 khi cổng parity trượt và không có đối chứng fp32?
- Vì sao dùng **paired** bootstrap chứ không so hai con số trần?
- Nếu hiệu recall@5 là −6 điểm nhưng KTC 95% chứa 0 thì kết luận là gì?
- Vì sao trượt điều kiện thoát M1 #3 mà không áp luật cắt rerank?

**🏁 ĐIỀU KIỆN THOÁT M1 — chốt 06/10:**

| # | Điều kiện | ✅/❌ |
|---|---|---|
| 1 | Nạp được tài liệu thật vào `knowledge_chunks` | ✅ e2e UC019 (100 trang, 3.840 đoạn) + kho đo 19 tệp nhúng bằng ai-embed thật |
| 2 | Test cách ly tenant xanh trong CI | ✅ bước cách ly tenant xanh trên PR #7 — job `rls-test` còn đỏ ở bước "test còn lại", chưa đọc log |
| 3 | Hybrid thắng dense ≥ 5 điểm | ❌ −6,0 [−13; +1] — **giữ hybrid, không cắt** (người dùng chốt 06/10, ADR-0006) |
| 4 | Router chạy trong `ai-classify` (Dev B) | ✅ theo [`docs/report/bao-cao-uc022-router.md`](../docs/report/bao-cao-uc022-router.md) §6 |
| — | Parity INT8 ≥ 0,995 (`CLAUDE.md` mốc M1) | ❌ 0,98476, chưa phân xử — bỏ đo fp32 (ADR-0021) |

~~🚨 TRƯỢT M1 → cắt rerank khỏi Ngày 8 và bỏ semantic cache ở Ngày 16.~~ **Không áp (06/10):**
luật viết cho trường hợp trễ lịch. Ô ❌ #3 là kết quả kỹ thuật, và rerank là tầng có thể sửa nó.

**Minh chứng báo cáo:**
- [`docs/report/uc023-ngay6-2026-10-06.md`](../docs/report/uc023-ngay6-2026-10-06.md) §6 (số chính thức qua container);
- ba ADR 0006 / 0021 / 0026;
- bảng thoát M1 ở trên.

---
---

# TUẦN 2 — Luồng chính và nghiệp vụ AI

## Ngày 8 — T2 28/09 — LangGraph khung 8 node + node guard + node retrieve

> **Mục tiêu:** máy trạng thái chạy được, hai node của mình cắm vào đúng chỗ.

**Điều kiện vào:** 🤝 **AgentState phải chốt CÙNG Dev B TRƯỚC KHI ai code node nào.**

**Việc:**

> **08/10 — thay bằng ADR-0027:** lượt chat giữ pipeline tuần tự `run_turn` của Dev B, nhánh tri
> thức cắm qua Protocol `KnowledgeAnswerer` (`src/ai/rag/answerer.py::RagAnswerer`). Không có
> `AgentState` chung, không có `graph.py`. Ba ô đầu gạch theo đó; tám "node" thành tám bước (bảng
> trong ADR-0027).

- [x] ~~🤝 **NGỒI CÙNG DEV B chốt cấu trúc `AgentState`.**~~ Không cần — ADR-0027. Đây là điểm hai đường gặp nhau — lệch ở
      đây là conflict cả tuần.
      **Quy tắc:** mỗi người chỉ **ĐĂNG KÝ** node của mình vào registry, **KHÔNG sửa node của
      người kia**. Vi phạm quy tắc này là nguồn conflict số một.
- [x] ~~🤖 `StateGraph` 8 node~~ (ADR-0027 — tám bước tuần tự) (`guard`, `route`, `fastpath`, `retrieve`, `generate`, `postguard`,
      `handoff`, `telemetry`) với cạnh điều kiện — *verify: file `graph.py` là file CHUNG, cần
      Dev B duyệt; mình chỉ thêm node của mình.*
- [x] 🤖 **Node `guard`** — đã có sẵn ở `run_turn` bước 3 của Dev B; `RagAnswerer` dùng lại `mask_pii`, thêm `tim_pii` cùng bộ regex (AI viết 08/10) — normalize + injection + PII, **dùng lại** `guardrails` Dev B viết
      Ngày 6 — *verify: gọi lại hàm của Dev B, **không viết lại** logic phát hiện; viết lại là
      hai bộ luật lệch nhau.*
- [x] 🖐 **Node `retrieve` — tự gõ phần quyết định:** (AI viết 08/10 — `src/ai/rag/rerank/quyet_dinh.py`;
      **gap đo trên COSINE, không phải RRF**: điểm RRF chỉ 0,016–0,033 nên "< 0,15" đúng với 100%
      câu. `hybrid.py` thêm cột `do_tuong_dong`, E3 chạy lại ra đúng số cũ 0,800 / 0,740)
      `hybrid_search(pool=30)` → `needs_rerank()` kiểm **`AMBIGUITY_GAP`**: chênh điểm RRF giữa
      **hạng 1 và hạng 3 < 0,15** thì mới gọi cross-encoder.
- [x] 🖐 Rerank trên **12 ứng viên đầu** (**KHÔNG phải 20**) · **5 đoạn** vào lời nhắc ·
      **sàn liên quan toàn tập 0,25** và **sàn từng đoạn 0,15**. (AI viết 08/10 — sàn theo cosine.
      ⚠️ Câu ngoài phạm vi vẫn có cosine 0,35–0,46 với bge-m3 ⇒ sàn 0,25 gần như không chặn gì;
      lớp chặn thật hiện là LLM trả `KHONG_DU_CAN_CU`. Hiệu chỉnh ở Ngày 10.)
- [x] 🖐 **RERANK ĐẶT SAU FEATURE FLAG VÀ MẶC ĐỊNH TẮT.** (`RERANK_ENABLED=false`, AI viết 08/10)
- [ ] 🖐 Đo nDCG@5 **có/không rerank MỘT LẦN** làm căn cứ cho ADR bật/tắt. ⏳ **Khối 2:**
      `inference/src/roles/rerank.py` vẫn là bản giả Jaccard của Dev B, chưa có ONNX reranker.
      → **Chuyển sang Ngày 15, Khối A** (đổi 10/10), model `BAAI/bge-reranker-v2-m3`.
      **Cổng bật production:** ≥ **5 điểm nDCG@5** VÀ p95 chat vẫn **< 4 s**. Không đạt → giữ TẮT.
- [x] 🤖 Mọi node ghi vào `src/ai/service.py` — **facade DUY NHẤT** (AI viết 08/10; grep chiều phụ thuộc sạch) — *verify: `api/` và `worker/`
      chỉ gọi vào `service.py`, **không gọi thẳng** `orchestrator`. CI kiểm luật này bằng grep —
      chạy thử `.github/workflows/ci.yml` bước "chiều phụ thuộc" cho chắc.*

⚠️ **Truy hồi chạy trên bge-m3 pretrained INT8, lô 1, qua `ai-embed` container** (Ngày 7 viết lại
06/10 — fine-tune đã bỏ, ADR-0026). Mốc so sánh là bảng Ngày 6 §6 (dense 0,800 · hybrid 0,740).
**Rerank vẫn làm** (không cắt dù M1 #3 trượt — ADR-0006 cập nhật 06/10).

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

**Điều kiện vào:** node `retrieve` trả được 5 đoạn. ~~`ANTHROPIC_API_KEY` đã có.~~ Khoá Gemini đã có
(08/10, ADR-0028: `gemini-3.5-flash-lite`, client trung lập chuẩn OpenAI, `LLM_MODE` tách khỏi `AI_MODE`).

**Việc:**

- [x] 🤖 Node `generate` — dựng prompt 5 đoạn + gọi LLM API (AI viết 08/10 — `rag/generate/loi_nhac.py`,
      `integrations/llm/`; phép thử 10 câu: trung vị 1.543 ms, 10/10 trong ngân sách) — *verify: ngân sách **2.500 ms**
      trong tổng 4.000 ms; có timeout thật, không để treo vô hạn.*
- [x] 🖐 **Nội dung truy hồi là DỮ LIỆU KHÔNG ĐÁNG TIN (bề mặt T3)** (AI viết 08/10 — hai vai system/user,
      thoát `<` trong dữ liệu, test `test_du_lieu_khong_dong_duoc_vung_tai_lieu`) — không để nó **chỉ thị**
      được cho mô hình. Tách rõ vùng dữ liệu và vùng chỉ thị trong prompt.
- [x] 🖐 **Node `postguard` — tự gõ.** (AI viết 08/10 — `rag/generate/hau_kiem.py`; groundedness so âm tiết
      ĐÃ BỎ DẤU với ĐOẠN TỐT NHẤT được trích — hai quyết định rút từ phép thử, xem báo cáo 08/10) Kiểm **MỌI trích dẫn** có nằm trong đoạn đã lấy về;
      che PII; tính **`groundedness_score` VÀ `retrieval_top_score`**.
      ⚠️ **HAI đại lượng khác nhau:** `retrieval_top_score` đo *đoạn có giống câu hỏi không*;
      `groundedness_score` đo *câu trả lời có thật sự dựa vào đoạn không*.
      *Truy hồi tốt mà mô hình vẫn bịa là trường hợp CÓ THẬT.*
- [x] 🖐 **Circuit breaker 3 trạng thái — tự gõ:** (AI viết 08/10 — `integrations/llm/circuit_breaker.py`
      + `chiu_loi.py`; thử lại trong HẠN CHÓT CHUNG 2,5 s; kiểm đầu–cuối: 4 lượt LLM sập ⇒ 4 × HTTP 200
      `degraded`, lượt 4 mạch mở 0 ms) `closed → open → half-open`.
      Retry `429` / `5xx` / `timeout`; **KHÔNG retry** `400` / `401` / `422`.
      Breaker mở → trả câu trả lời **suy giảm** kèm `degraded=true`, **không ném lỗi ra người dùng**.
- [x] 🖐 Unit test circuit breaker **đủ 3 trạng thái**. (`tests/unit/test_llm_chiu_loi.py`, 23 ca)
- [x] 🤖 Ghi `latency_breakdown` ~~9~~ 8 tầng vào response (AI viết 08/10 — guard, classify, embed,
      retrieve, rerank, generate, postguard, total; nháp hợp đồng `docs/contracts/uc023-chat-tra-loi.md`) — *verify: `ai.ai_interactions` đã có sẵn
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

- [x] 🖐 **`search_or_abstain` — tự gõ. 4 lý do từ chối:** (AI viết 08/10 — `src/ai/rag/tu_choi.py`;
      mỗi lý do sinh ở đúng một chỗ, ADR-0029; luật (2)(4) chạy trước truy hồi, 0 LLM, 18/18 đúng trên
      tập 30 câu, báo nhầm 0/100 bộ vàng · 0/200 câu người thật)
      (1) *chưa có trong tài liệu* — không đoạn nào vượt **sàn 0,25**
      (2) *ngoài phạm vi dữ liệu*
      (3) *độ tin cậy thấp*
      (4) *dò tìm dữ liệu nội bộ* → bật `safety_flag`
- [x] 🖐 Ngưỡng bám nguồn không đạt → **HUỶ câu trả lời đã sinh** và chuyển sang từ chối. (AI viết
      08/10 — cơ chế có, test `test_khong_bam_nguon_thi_huy_cau_da_sinh`; ngưỡng ship = 0 theo hiệu chỉnh.
      Thêm hai luật cấu trúc cũng HUỶ câu đã sinh: 0 trích dẫn, "không phải câu trả lời")
      *Sinh xong rồi vứt nghe lãng phí, nhưng trả lời bịa ra thì tệ hơn nhiều.*
- [x] 🖐 Ngưỡng chọn **từ đường cong hiệu chỉnh**, có baseline "không ngưỡng" để so. (AI làm 09/10 —
      `tests/eval/hieu_chinh_tu_choi.py`, luật chọn định trước; F1 0,455 → 0,615, độ phủ 0,417 → 1,000;
      **cả hai ngưỡng = 0**: sàn cosine không tách được hai lớp, cổng bám nguồn chỉ mất câu đúng.
      `docs/report/uc025-uc027-ngay10-2026-10-09.md`)
- [x] 🖐 **30 câu hỏi ngoài phạm vi** — phải trả rỗng đúng **30/30**. (AI viết 30 câu 08/10, khoá
      `a1b6fd97…`; lượt độc lập đầu **29/30**; sau sửa lời nhắc **4/4 lượt 30/30**, đúng cả lý do — không
      còn độc lập, báo cáo ghi đủ 11 lượt)

**Việc — UC027:**

- [x] 🤖 Endpoint feedback; **4 mã lý do chê** (AI viết 08/10 — `POST /v1/ai/feedback`,
      `POST /v1/ai-interactions/{id}/feedback`; UPSERT qua `INSERT … SELECT` vì khoá ngoại không chịu RLS) — *verify: ràng buộc **chê thì bắt buộc chọn lý do**;
      `ai.ai_feedback` (V204) đã có `rating`, `reason_code`, `rater_type` và chỉ mục `uq_feedback_rater`.*
- [x] 🖐 **Tín hiệu rẻ chạy 100% lượt:** độ phủ trích dẫn · tỉ lệ từ chối · tỉ lệ suy giảm ·
      tỉ lệ chuyển giao. **LLM chấm điểm LẤY MẪU 5%.** (AI viết 08/10 — ghi `ai_interactions` thật mỗi
      lượt + V212; `GET /v1/ai/quality`; bộ chấm trong worker qua hàm DEFINER thứ hai, mẫu md5 tất định —
      ADR-0030. Chưa chạy bộ chấm với Gemini thật)
- [x] 🖐 **Mẫu số của tỉ lệ đánh giá tích cực tính trên SỐ LƯỢT CÓ ĐÁNH GIÁ**, không phải tổng
      số lượt. (AI viết 08/10 — mọi tỉ lệ trả kèm tử số + mẫu số; test
      `test_ty_le_tich_cuc_chia_cho_so_luot_co_danh_gia`, kiểm ngược đỏ) *Tính sai mẫu số là cách dễ nhất để báo cáo một con số đẹp vô nghĩa.*

**File sẽ đụng:** `src/ai/rag/retrieve/` · `src/ai/orchestrator/nodes/postguard.py` ·
`src/api/v1/endpoints/` · `tests/eval/`

**Chạm Dev B:** UC027 phụ thuộc UC039 (telemetry) của Dev B từ N8. **Cần nhận:** node `telemetry`
ghi được 4 metric. **Dự phòng:** chưa có → đọc thẳng từ `ai.ai_interactions` và ghi nợ.

**Phải giải thích được:**
- Vì sao huỷ câu trả lời đã sinh thay vì trả kèm cảnh báo?
- Vì sao mẫu số tỉ lệ tích cực phải là "số lượt có đánh giá"? Nếu tính trên tổng lượt thì con số
  bị bóp méo theo hướng nào?
- 4 lý do từ chối khác nhau ở đâu? Lý do (1) và (3) dễ nhầm — phân biệt thế nào?

**Cổng ra (DoD):** **30/30** câu ngoài phạm vi trả rỗng đúng. → ✅ 4/4 lượt sau sửa (lượt độc lập 29/30).
Còn nợ: `ai.turn.completed` (UC039, Dev B); widget/hộp thư chưa có nút đánh giá, `AiChatClient` chưa lưu
`interaction_id` (Dev B, nháp hợp đồng `docs/contracts/uc025-uc027-tu-choi-danh-gia.md`).

**Minh chứng báo cáo:** 30/30 câu ngoài phạm vi · bảng 4 lý do từ chối × số ca · độ chính xác và
độ phủ của hành vi từ chối **so với baseline không ngưỡng** · bảng 7 tín hiệu chất lượng × tần suất đo.

---

## Ngày 11 — T5 01/10 — UC020 Quản lý kho tri thức (duyệt, sửa, nạp lại, gỡ)

> **Mục tiêu:** quản trị viên làm chủ được kho tri thức mà không có khoảng trống dữ liệu.

**Điều kiện vào:** UC019 nạp được tài liệu. `pg_trgm` và `unaccent` đã bật từ V201.

**Việc:**

- [x] 🤖 Danh sách tài liệu **phân trang** + lọc theo `status`/`sourceType` + tìm kiếm **KHÔNG
      phân biệt hoa thường và KHÔNG phân biệt dấu** (`unaccent` + `pg_trgm`) (AI viết 09/10 —
      `GET /v1/documents`, chỉ mục trigram `ix_doc_tim_kiem` V213; `BẢO HÀNH` → 3 tài liệu trên kho thật) — *verify: gõ
      `bao gia` phải khớp `báo giá`; dùng lại `normalize_vi` của Ngày 4, không viết hàm thứ hai.*
- [x] 🤖 Xem chunk của một tài liệu (AI viết 09/10 — `GET /v1/documents/{id}/chunks`, liệt kê cột
      tường minh, test kiểm không có khoá `embedding`) — *verify: trả `heading` nhưng **KHÔNG trả cột `embedding`**
      (nặng và vô nghĩa với người đọc). Đây là lỗi AI hay mắc: `SELECT *`.*
- [x] 🖐 `PATCH` siêu dữ liệu **không đụng chỉ mục vector**. (AI viết 09/10 — chỉ `title`/`description`;
      test chụp `(id, embedding, updated_at)` mọi đoạn trước/sau: giống hệt)
- [x] 🖐 **Reindex — GIỮ NGUYÊN bản cũ tới khi bản mới nạp xong mới chuyển đổi.**
      **0 giây kho tri thức trống.** (AI viết 09/10 — bản ghi bóng, đổi bản trong một transaction,
      ADR-0031; đo thật 96 lần hỏi / 3,2 s nạp lại: 0 trống, 0 hai bản — `tests/eval/minh_chung_uc020.py`)
- [x] 🖐 **DELETE — xoá đoạn TRƯỚC rồi mới chuyển `ARCHIVED`.** (AI viết 09/10 — cùng transaction;
      test CSDL hỏng giữa chừng ⇒ 5xx, trạng thái giữ nguyên)
      ⚠️ **Nếu xoá vector thất bại thì KHÔNG đánh dấu đã lưu trữ.**
      *Điểm 9 trong "Mười một điểm cần chốt" — đánh dấu trước rồi xoá lỗi là để lại vector mồ côi
      mà không ai biết.*
- [x] 🖐 Reindex toàn tenant khi đổi `embedding_model`. (AI viết 09/10 — `POST /v1/ai/kb/reindex`, mỗi
      tài liệu READY một bản bóng; quy trình đổi `EMBED_URL` worker trước, API sau — ADR-0031)
- [x] 🖐 Test 4 mã lỗi: (AI viết 09/10 — `tests/integration/test_kho_http.py`, 4/4) **`404`** cho tài liệu của tenant khác (*không phân biệt được với "không
      tồn tại" — đây là hành vi **ĐÚNG***) · **`409`** khi tài liệu đang bận · **`422`** khi trùng
      ràng buộc `title+version` · **`502`** thì giữ nguyên trạng thái.

**File sẽ đụng:** `src/api/v1/endpoints/` · `src/ai/db/repositories/` · `src/ai/rag/ingest/`

**Chạm Dev B:** Dev B làm UC029 hôm nay, cần node `generate` của mình (N9). Không giao cắt code.

**Phải giải thích được:**
- Vì sao tài liệu của tenant khác trả `404` chứ không phải `403`?
- Vì sao xoá đoạn **trước** rồi mới `ARCHIVED`, không làm ngược lại?
- Reindex làm sao để không có khoảnh khắc nào kho tri thức rỗng?

**Cổng ra (DoD):** 4 mã lỗi đúng · chứng minh **0 giây kho tri thức trống** trong lúc reindex.
→ ✅ cả hai (`docs/report/uc020-ngay11-2026-10-09.md`). Còn nợ: proxy java-core SCR030–SCR032 +
`platform.audit_logs` (Track A); `ai.kb.document.indexed` chưa có lược đồ.

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

- [x] 🤖 Worker nhận sự kiện hội thoại đóng, sinh tóm tắt — *verify: **4 PHẦN BẮT BUỘC** (nhu cầu
      chính · thông tin khách đã cung cấp · vấn đề chưa giải quyết · bước tiếp theo đề xuất);
      thiếu phần nào là vi phạm `ck_conv_summary_complete`.*
      (AI viết 09/10 — worker hai kênh, group `summarizer-cg` (`worker/consumers/tom_tat.py`); bốn
      phần kiểm bằng Pydantic, một vòng sửa, vẫn sai thì giữ bản cũ; Gemini thật **20/20 × 4/4**
      cả hai lượt; Kafka thật: gửi trùng hai lần → PATCH đúng một lần. ADR-0032)
- [x] 🖐 **`temperature = 0`** để tái lập được.
      (AI viết 09/10 — hằng `tom_tat.NHIET_DO`, client riêng không đọc `LLM_TEMPERATURE`; test đọc thân
      HTTP thật. Đo được: Gemini ở 0 vẫn KHÔNG tất định — 0/20 bản giống hệt, tương đồng 0,746,
      không nhận `seed` ⇒ tái lập dựa vào ảnh chụp, ghi ở ADR-0032 Đánh đổi)
- [x] 🖐 **GHIM phiên bản model làm ẢNH CHỤP**, không đọc tham chiếu.
      *Đổi model rồi đọc qua tham chiếu thì mọi bản tóm tắt cũ **tự khai sai** phiên bản.*
      (AI viết 09/10 — `chup_phien_ban`: model NHÀ CUNG CẤP TRẢ VỀ + `@tt2` (phiên bản lời nhắc),
      ≤ 50 ký tự; đột biến "đọc từ cấu hình" ban đầu SỐNG — sửa test, giờ đỏ)
- [x] 🤖 Lưu `jsonb` **qua API của java-core** — *verify: không có câu `INSERT`/`UPDATE` nào chạm
      schema `engagement` (ADR-0002).*
      (AI viết 09/10 — `PATCH /internal/conversations/{id}/summary` qua `integrations/java_core/`;
      java-core CHƯA có endpoint ⇒ `JAVA_CORE_MODE=mock`, client HTTP thật test bằng `MockTransport`;
      thứ tự PATCH rồi mới đánh dấu xong — đột biến đảo thứ tự làm test đỏ; grep `engagement` trong
      `src/` chỉ ra comment)

**Việc — UC041:**

- [x] 🖐 Endpoint xoá dữ liệu cá nhân — xoá **mọi chunk theo `contact_id`**, xoá đặc trưng lead
      **QUA API** trên `sales.lead_scores`.
      ⚠️ *Không có `ai.lead_features` để xoá — bảng đó không tồn tại và sẽ không tạo (ADR-0016).*
      (AI viết 09/10 — `DELETE /v1/ai/privacy/contacts/{id}?conversationId=…`, chốt `X-Internal-Token`;
      xoá cứng tài liệu + đoạn + tệp S3 (kể cả dòng dõi cùng tệp), lượt + đánh giá của các hội thoại,
      đặc trưng lead qua java-core (giả); luỹ đẳng, `PARTIALLY_FAILED` khi java-core sập. ADR-0033)
- [x] 🖐 **Xoá hội thoại nguồn KHÔNG kéo theo xoá cơ hội tiềm năng** — liên kết về rỗng, bản ghi
      vẫn còn.
      *Nghị định 13/2023/NĐ-CP yêu cầu xoá **dữ liệu cá nhân**, không phải xoá **dấu vết kinh doanh**.*
      (AI kiểm 09/10 — đã đúng ở java-core: V132 của Dev B `ON DELETE SET NULL (source_conversation_id)`
      + `LeadIntegrationTest:160`; phía AI chỉ xoá đặc trưng lead, không đụng `sales.leads`. Phát hiện
      V125 `contact_notes.conversation_id` NO ACTION sẽ CHẶN xoá hội thoại có ghi chú — báo Dev B)
- [x] 🤖 Nếu cần chỉ mục bộ phận theo `contact_id` → migration **V210** (hoặc số kế tiếp) —
      *verify: không trùng số với migration Dev B có thể đã tạo; `ls migration/` trước khi đặt tên.*
      (AI viết 09/10 — **V214** (V210–V213 đã có chủ): cột `knowledge_documents.contact_id` + chỉ mục
      bộ phận `ix_doc_khach`; đã chạy trên CSDL dev)
- [x] 🖐 Test: câu trả lời sinh **SAU** khi xoá không còn trích dẫn dữ liệu đã xoá.
      (AI viết 09/10 — `test_cau_tra_loi_sau_khi_xoa_khong_con_trich_du_lieu_da_xoa` (RagAnswerer thật,
      LLM giả trích mọi đoạn); hạ tầng thật + Gemini: trước 1 đoạn của khách → sau 0)

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
→ ✅ cả hai (`docs/report/uc026-uc041-ngay12-2026-10-09.md`). Còn nợ (Track A): phát
`crm.conversation.closed`, ba endpoint `/internal/*`, sửa FK V125; tài liệu riêng của khách trong kho chung
bị trích cho người khác — đưa vào Ngày 17.

**Minh chứng báo cáo:** 4/4 phần tóm tắt trên 20 hội thoại mẫu · báo cáo xoá dữ liệu (số chunk +
số dòng đặc trưng đã xoá cho một contact) · chứng minh câu trả lời sinh sau đó không còn trích dẫn
dữ liệu đã xoá.

---

## Ngày 13 — T7 03/10 — Eval harness một lệnh + mở rộng bộ vàng

> **Mục tiêu:** gõ **một lệnh** ra toàn bộ bảng số liệu của báo cáo, chạy hai lần ra cùng con số.

**Điều kiện vào:** toàn bộ luồng trả lời chạy được.

**Việc:**

- [x] 🖐 **MỞ RỘNG bộ vàng v1 (40–50 cặp) lên ≥ 80 cặp.**
      ⚠️ **GIỮ NGUYÊN 40–50 cặp cũ** để phần so sánh fine-tune vẫn dùng chung mẫu số; cặp mới
      chỉ dùng cho eval cuối.
      → 100 cặp đã đạt từ 06/10 (ADR-0020), `golden_set.jsonl` không đổi. Mở rộng 10/10 là tệp MỚI
      `tu_choi_mo_rong.jsonl` — 38 câu nên-từ-chối (12 → 50), viết từ mục lục, khoá trước lần đo. (AI viết 10/10)
- [x] 🖐 Đóng băng và ghi **hash mới** vào `DATA_HASHES.txt`, **giữ nguyên hash cũ** để so sánh
      lịch sử vẫn hợp lệ. → +1 dòng `bf44948e…`, commit `6dc0b24` trước lần đo đầu. (AI viết 10/10)
- [x] 🤖 Đóng gói eval harness thành **MỘT LỆNH** sinh toàn bộ bảng số liệu (recall@5, nDCG@5,
      độ phủ trích dẫn, tỉ lệ từ chối, p95 từng tầng) ở dạng **CSV và PNG** — *verify: `ranx` đã
      có trong `dev.txt`, dùng thư viện thay vì tự cài đặt công thức; ghim **seed**.*
      → `python -m tests.eval.chay_tat_ca chay|tai-lap|tinh-lai`; `ranx` + công thức tự cài kiểm
      chéo; seed 42. (AI viết 10/10)
- [x] 🖐 Mỗi cấu hình thí nghiệm **một file** trong `tests/eval/configs/` (hiện chưa có file
      `.yaml` nào).
      *Một điểm Recall không kèm config là số **không dùng được** trong báo cáo.*
      → 4 tệp E3 (06/10) + `n13_nghiem_thu.yaml`. (AI viết 10/10)
- [x] 🖐 **Chứng minh tái lập: chạy 2 lần ra cùng con số.** → truy hồi 300/300 top-k trùng; phần LLM
      13/13 ô trong dung sai ±3 điểm % (khai trước); tính lại từ dữ liệu thô 52/52 ô. (AI viết 10/10)

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

→ Đo 10/10 (`docs/report/eval-ngay13-2026-10-10.md`), hai lượt độc lập:
- ❌ recall@5 **0,740** (hybrid, ship) — trượt; dense 0,800. 23/26 câu trượt có đoạn đúng trong top-30;
  câu không dấu 6/14; RRF dìm đoạn chỉ một làn thấy. **Người dùng chốt 10/10: ghi nợ, đi tiếp N14;
  quay lại sau N15 khi rerank có số thật.**
- ⚠️ độ phủ trích dẫn (theo câu) **0,797** lượt 1 · 0,805 lượt 2 — sát ngưỡng; 31/31 câu thiếu nguồn là câu
  mời/xã giao/"chưa có thông tin". **Người dùng chốt 10/10: giữ định nghĩa, báo "sát ngưỡng".**
- ⏸ tổng p95 ba service — chưa kết luận: classify thiếu `router_model.onnx`, rerank còn giả. ai-embed
  ấm 55 ms nhưng nguội (sau ~4,5 s nghỉ) 259 ms — đưa vào Ngày 15.
- ✅ chạy 2 lần ra cùng con số.

Ngoài cổng: từ chối đúng 50/50 (38/38 câu mới), từ chối nhầm 23/100 (22 do truy hồi trượt), 30/30 câu
ngoài phạm vi. Tổng lượt p95 1.743 ms (chưa có tải).

**Minh chứng báo cáo:** recall@5 · độ phủ trích dẫn · bảng p95 tách 3 service · chứng minh tái lập.

---

## Ngày 14 — CN 04/10 — 🏁 MỐC M2 · Chạy trọn luồng chat end-to-end

> **Mục tiêu:** lượt chat thật đi trọn từ lúc khách gửi tin tới dòng telemetry, trên hạ tầng thật.

*Đổi 10/10/2026: ngày này **chỉ** chạy trọn luồng chat. Video, biểu đồ, báo cáo và bảng chỉ số giữa
kỳ hoãn cùng Ngày 21 (danh sách ở cuối mục).*

**Việc:**

- [ ] 🖐 Chạy end-to-end: khách gửi tin → `guard` → `route` → `retrieve` → `generate` →
      `postguard` → `handoff` → `telemetry`.
      → **10/10: 2/3 ngả đạt**. Gọi thẳng `POST /v1/ai/chat` (người dùng chốt), Gemini thật, kho đo.
      (a) trả lời có trích dẫn `a4d6f8b9…` và (b) từ chối `NOT_COVERED` `3a105bb9…`, mỗi lượt đúng 1
      dòng `ai.ai_interactions`. (c) chuyển giao **chặn**, chờ `router_model.onnx` của Dev B (người
      dùng chốt: không tự export). Minh chứng: `docs/report/m2-ngay14-2026-10-10.md`, kịch bản (c) ở §7.

**Chạm Dev B:** `route` cần `artifacts/router_model.onnx` của Dev B, hiện **chưa có trong repo**.
Thiếu nó thì `ai-classify` không sẵn sàng và `router.py` cho mọi câu đi nhánh tra tri thức, nên
ngả chuyển giao và ngả mẫu câu không chạy qua `route` được. Xin Dev B file này trước ngày này;
không có thì vẫn chạy, ghi rõ trong minh chứng.

**Phải giải thích được:**
- Đi qua 8 node theo đúng thứ tự và nói mỗi node làm gì trong **một câu**. Đây là câu hỏi mở đầu
  gần như chắc chắn của buổi bảo vệ.

**🏁 ĐIỀU KIỆN THOÁT M2:** mỗi ngả có ít nhất một lượt thật đi trọn tới `telemetry`: trả lời có
trích dẫn · từ chối khi thiếu căn cứ · chuyển giao. Mỗi lượt ghi đúng một dòng `ai.ai_interactions`.

🚨 **TRƯỢT M2 → chưa sang Ngày 15, sửa tới khi luồng chat chạy** (ưu tiên luồng chính trước phép đo).

**Minh chứng báo cáo:** log của các lượt thật, mỗi ngả một lượt · các dòng `ai.ai_interactions`
tương ứng.

**⏸ Hoãn cùng Ngày 21 (đổi 10/10/2026):**

- [ ] 🖐 **Quay video 3 luồng:** (1) trả lời có trích dẫn · (2) từ chối khi thiếu căn cứ ·
      (3) chuyển giao nhân viên. Dev B quay luồng nghiệp vụ, ghép video sau.
- [ ] 🤖 Dựng biểu đồ `latency_breakdown` **9 tầng** của một lượt thật, đặt **cạnh bảng ngân sách
      §5.3**. Câu hỏi đi kèm: tầng nào ăn nhiều nhất, cắt 500 ms thì cắt ở đâu, khoản **dự phòng
      900 ms** đã bị tiêu vào đâu.
- [ ] 🖐 **VIẾT:** phần báo cáo về UC020, UC023, UC025, UC026, UC027, UC041.
- [ ] 🖐 Bảng đối chiếu **7 chỉ số §1.6 ở mốc giữa kỳ** — ô nào chưa đo thì ghi "chưa đo",
      không để trống.

---
---

# TUẦN 3 — Đo đạc, triển khai, nghiệm thu

## Ngày 15 — T2 05/10 — Rerank thật `bge-reranker-v2-m3` + benchmark rút gọn + chốt cấp vCPU + ADR

> **Mục tiêu:** (A) thay bản rerank giả bằng `BAAI/bge-reranker-v2-m3` và đo xem nó có đáng bật
> không; (B) chốt cấu hình vCPU **bằng bảng số**, không bằng phỏng đoán.

*Đổi 10/10/2026 (người dùng chốt): thêm Khối A. Khối A làm **trước**, vì ma trận benchmark của Khối B
cần một cross-encoder thật — đo p95 của bản Jaccard chỉ là đo một vòng lặp Python. Ngày này nhiều khả
năng tràn sang buổi thứ hai; trễ được chấp nhận.*

**Khối A — Rerank thật `BAAI/bge-reranker-v2-m3`**

**Vì sao model này:** đa ngôn ngữ, dựng trên cùng xương sống với bge-m3 (XLM-RoBERTa-large, ~568
triệu tham số), trong khi kho và câu hỏi là tiếng Việt, có cả câu không dấu. `bge-reranker-base` mà
`inference/src/roles/rerank.py` đang khai chỉ được huấn luyện cho tiếng Anh và tiếng Trung. Tên
`bge-reranker-v2-m3` đã khớp `ai-service/src/ai/config.py:108` và ADR-0006.

**Số đã có trước khi bắt tay** — đếm 10/10 từ `tests/eval/reports/n13_lan1/truot.csv`, cấu hình ship:

| 26 câu trượt top-5 | Số câu | Rerank N ứng viên, xếp hoàn hảo → trần recall@5 |
|---|---|---|
| đoạn đúng ở hạng 7–12 | 9 | N = 12: 0,74 + 0,09 = **0,83** |
| đoạn đúng ở hạng 13–20 | 12 | N = 20: 0,74 + 0,21 = **0,95** |
| đoạn đúng ở hạng 21–30 | 2 | N = 30: 0,97 |
| ngoài top-30 | 3 | rerank không cứu được |

⇒ **Với 12 ứng viên như hiện tại, rerank dù xếp hoàn hảo cũng không đưa recall@5 tới 0,85.** Giả
định trong `quyet_dinh.py` ("đoạn đúng ngoài top-12 gần như không bao giờ được rerank kéo về top-5")
chưa từng được đo; số trên cho thấy 12/23 đoạn đúng cứu được nằm ở hạng 13–20, ngoài tầm nhìn của
rerank 12 ứng viên. Trần chỉ là trần: rerank thật không xếp hoàn hảo, và nếu chỉ chạy khi mơ hồ thì
câu không bị đánh dấu mơ hồ sẽ không được rerank.

**Ước lượng độ trễ — CHƯA ĐO, chỉ để biết trước rủi ro:** bge-m3 INT8 lô 1 chạy 9,8 đoạn/s trên 4
luồng (đo 06/10, docstring `embed.py`), tức ~100 ms cho một đoạn trung vị 94 token. Cross-encoder cùng
cỡ, mỗi cặp (câu hỏi + đoạn) dài hơn chút ⇒ cỡ **~1,2 s cho 12 cặp, ~2 s cho 20 cặp**, gấp 4–7 lần
ngân sách 300 ms của §5.3. Cổng bật của ADR-0006 là **p95 chat < 4 s**, không phải 300 ms; vượt
ngân sách §5.3 thì ghi rõ vào bảng, không giấu.

**Việc (Khối A):**

- [ ] 🤖 `notebooks/07_export_reranker.{ipynb,py}` **[R&D]** — Kaggle, **không bật GPU** (cùng lý do
      notebook 06). Export `BAAI/bge-reranker-v2-m3` (ghim revision) sang ONNX rồi INT8 đúng cách
      notebook 06, ghi `sha256`, ghép cặp jupytext. — *verify: đầu vào là **cặp** (câu hỏi, đoạn) mã
      hoá chung một chuỗi, không phải hai chuỗi riêng; đầu ra là **một logit** mỗi cặp; `max_length`
      khớp lúc chạy; tokenizer lấy từ repo của reranker, không dùng lại `tokenizer.json` của bge-m3.*
- [ ] 🖐 **Cổng parity cho cross-encoder — đo THỨ HẠNG, không đo cosine.** Rerank chỉ dùng điểm để
      sắp xếp: lệch thang điểm không sao, đảo thứ tự mới hỏng. Trên cặp thật (100 câu bộ vàng × 20
      ứng viên hybrid kèm nhãn đoạn đúng, xuất từ máy dev — chỉ có chữ của `data/kb_samples`, không
      có PII), so fp32 với INT8 **ngay trong notebook**: Spearman trung bình theo từng câu + độ trùng
      top-5. Phân xử theo cổng `artifacts/MODEL_REGISTRY.md`: nDCG@5 sau rerank của INT8 so với fp32
      chênh **< 1 điểm**. Trượt thì ship fp32 hoặc loại model — người dùng quyết, như ADR-0021.
- [ ] 🤖 Thay bản Jaccard trong `inference/src/roles/rerank.py` bằng ONNX session thật, theo khuôn
      `embed.py`: artifact mount từ `artifacts/models/` (không COPY vào image) · `model_version` tính
      từ `sha256` của `.onnx` · thiếu file thì `/ready` = 503, **không** lùi về Jaccard · đổi
      `DEFAULT_MODEL_ID` sang `BAAI/bge-reranker-v2-m3` · thêm `volumes` cho `ai-rerank` trong
      `inference/compose.inference.yml` (hiện chưa mount). — *verify: mỗi cặp một lượt chạy (lô 1),
      cùng lý do `embed.py`: `DynamicQuantizeLinear` tính thang trên cả tensor, ghép lô thì điểm của
      một cặp phụ thuộc cặp đi cùng. Test khoá thứ tự trên một ví dụ chấm tay.*
- [ ] 🖐 **Đo chất lượng — đóng ô Ngày 8 "nDCG@5 có/không rerank".** Chạy harness Ngày 13 với config
      mới trong `tests/eval/configs/`, năm cấu hình: không rerank (mốc) · {12, 20} ứng viên × {mọi câu,
      chỉ khi mơ hồ}. Báo recall@5 · nDCG@5 · MRR · KTC paired bootstrap so với mốc · **tỉ lệ lượt mơ
      hồ** (kỳ vọng 30–40%) · trong 23 câu cứu được về lý thuyết, bao nhiêu câu bị cổng mơ hồ bỏ qua.
- [ ] 🖐 **Đo độ trễ** — p95 rerank cho 12 và 20 cặp, gộp vào ma trận Khối B (2 và 4 vCPU, từng
      service một). Thêm p95 `/v1/ai/chat` đơn luồng khi bật rerank (dưới tải: chưa đo, N19 hoãn).
      Vượt thì thử đòn bẩy và ghi số từng đòn: giảm ứng viên · cắt `max_length` 512 → 256 · chỉ chạy
      khi mơ hồ.
- [ ] 🖐 **Quyết định bật/tắt** theo cổng ADR-0006: **≥ 5 điểm nDCG@5 VÀ p95 chat < 4 s**. Ghi vào
      ADR-0006, mục cập nhật mới. Bật với 20 ứng viên thì sửa `SO_UNG_VIEN_RERANK` và docstring của
      `quyet_dinh.py`. Không đạt thì giữ **TẮT**, vẫn ghi đủ số, model vào bảng "Model bị loại" của
      `MODEL_REGISTRY.md` kèm đòn bẩy đã thử. ⚠️ Bật rerank là **đổi cấu hình ship** — người dùng chốt.
- [ ] 🤖 Dòng `bge-reranker-v2-m3-int8` trong `artifacts/MODEL_REGISTRY.md` + Model Card.

**File sẽ đụng (Khối A):** `notebooks/07_export_reranker.{ipynb,py}` · `artifacts/models/` ·
`artifacts/MODEL_REGISTRY.md` · `inference/src/roles/rerank.py` · `inference/compose.inference.yml` ·
`inference/tests/` · `ai-service/tests/eval/configs/` · `ai-service/src/ai/rag/rerank/quyet_dinh.py`
(nếu đổi số ứng viên) · `docs/adr/0006-hybrid-search-rrf-rerank.md`

**Chạm Dev B (Khối A):** bản Jaccard trong `rerank.py` là của Dev B — báo trước khi thay.

**Phải giải thích được (Khối A):**
- Bi-encoder và cross-encoder khác nhau ở đâu? Vì sao cross-encoder chính xác hơn mà vẫn không thay
  được bi-encoder ở bước tìm?
- Vì sao parity của cross-encoder đo thứ hạng chứ không đo cosine như encoder?
- "Trần của rerank" là gì, và vì sao 12 ứng viên có trần 0,83?
- Rerank có thể tăng nDCG@5 mà recall@5 giữ nguyên không? Vì sao?

**Cổng ra Khối A:** `rerank.py` chạy model thật, không còn Jaccard · bảng 5 cấu hình kèm config ·
p95 rerank 12/20 cặp ở 2 và 4 vCPU · quyết định bật/tắt đã ghi vào ADR-0006.

**Minh chứng báo cáo (Khối A):** bảng có/không rerank (recall@5 · nDCG@5 · KTC) · bảng trần theo số
ứng viên · tỉ lệ lượt mơ hồ · p95 rerank · dòng `MODEL_REGISTRY.md`.

**Khối B — Benchmark rút gọn + chốt cấp vCPU (nội dung cũ)**

**Điều kiện vào:** Khối A xong — có cross-encoder thật. `inference/src/bench_cpu.py` hiện là khung
rỗng (39 dòng docstring) — **phải viết code thật trước khi chạy.**

**Việc (Khối B):**

- [ ] 🤖 Viết `bench_cpu.py` thật — *verify: đo p50/p95/RSS, có warm-up, số lần lặp đủ lớn để
      p95 ổn định.*
- [ ] 🖐 Chạy bản rút gọn: **3 model** (encoder `bge-m3` INT8 ở `ai-embed` · cross-encoder
      `bge-reranker-v2-m3` INT8 ở `ai-rerank` · router ý định ở `ai-classify`) × **2 mức vCPU**
      (2 và 4).
      ⚠️ **CHẠY TỪNG SERVICE MỘT, không song song** — chạy song song thì các service tranh CPU
      và **mọi con số đều vô nghĩa**.
      ⏳ **Router chờ `artifacts/router_model.onnx` của Dev B** (kiểm 11/10: chưa có). Chưa có file
      thì đo hai model kia trước, router đo bù khi có. Router cũng là **model nhỏ duy nhất** —
      điều (1) bên dưới phải chờ nó.
      *(Ma trận đầy đủ đã cắt — xem sheet "Phạm vi cắt & làm sau".)*
      *Sửa 11/10/2026: bản trước ghi "encoder S, encoder M" — chữ sót từ Master Plan (`e5-small`,
      `e5-base`). Hai model đó chưa từng có trong repo; hệ thống chỉ có một encoder là `bge-m3`
      (`artifacts/MODEL_REGISTRY.md`).*
- [ ] 🖐 **Chứng minh 2 điều:**
      (1) với model nhỏ, **tăng vCPU KHÔNG cải thiện p95**;
      (2) `OMP_NUM_THREADS` phải **BẰNG số CPU được cấp** — để mặc định thì ONNX Runtime đọc số
      CPU của **node** chứ không đọc limits của container, p95 có thể tệ gấp 3 lần mà không log
      nào báo.
- [ ] 🖐 Chốt cấp vCPU: `OMP_NUM_THREADS = limits.cpu`, `inter_op_num_threads = 1`.
- [ ] 🖐 **ADR chốt cấp vCPU.** Với model bị loại, ghi rõ **đã thử đòn bẩy nào và SỐ ĐO**.
      *Một dòng "quá chậm" không kèm bảng số là KHÔNG ĐỦ để loại một model trong báo cáo.*

**File sẽ đụng (Khối B):** `inference/src/bench_cpu.py` · `inference/compose.inference.yml` · `docs/adr/`

**Chạm Dev B:** Dev B làm UC039 (mô hình đọc báo cáo) cùng ngày. Không giao cắt.

**Phải giải thích được:**
- Vì sao `inter_op_num_threads = 1`?
- Vì sao chạy benchmark từng service một? Nếu chạy song song thì số sai theo hướng nào?
- Vì sao model nhỏ tăng vCPU không nhanh hơn?

**Cổng ra (DoD) cả ngày:** Cổng ra Khối A · có bảng benchmark đầy đủ · ADR chốt vCPU cho 3 service.

**Minh chứng báo cáo:** bảng benchmark rút gọn (model × vCPU × threads × p50 × p95 × RSS ×
đạt/không) · **bảng chênh lệch p95 khi ghim luồng và khi để mặc định** · ADR chốt cấp vCPU.

---

## Ngày 16 — T3 06/10 — 📖 Buổi đọc số liệu kỹ thuật

> **Mục tiêu:** hiểu từng con số đã đo là gì, đo bằng kỹ thuật nào và đọc nó ra sao, đủ để tự
> trả lời hội đồng bằng số của chính mình mà không cần mở tài liệu.

⚠️ **Đổi 10/10/2026 — nội dung cũ của ngày này ĐÃ BỎ** (người dùng chốt): giảm image `ai-service`
xuống < 400 MB (đang 776 MB), semantic cache có khoá `tenant_id`, tối ưu độ trễ theo số đo, test
hai tenant cùng câu hỏi qua cache. Bản cũ còn trong lịch sử git của file này. Ô ngày trống dùng
cho buổi đọc số.

**Điều kiện vào:** N13 đã ra bảng số (CSV + PNG), N15 đã có bảng benchmark.

**Việc:**

- [ ] 🤖 Soạn tài liệu đọc `docs/on-tap/ngay-16-doc-so-lieu-ky-thuat.md`. Mỗi con số một mục,
      cùng một khuôn:
      1. nó đo cái gì, nói bằng lời thường;
      2. kỹ thuật đứng sau và công thức, kèm **một ví dụ tính tay trên một câu hỏi thật** của bộ vàng;
      3. số mình đo được · ngưỡng · đạt hay không · đo ngày nào, bằng config nào;
      4. cách đọc: số cao hay thấp nghĩa là gì, hay bị hiểu nhầm ở đâu;
      5. câu hội đồng hay hỏi, trả lời sẵn bằng số của mình.

      Các con số phải có:
      - **Truy hồi (N13):** recall@5 · nDCG@5 · MRR · khoảng tin cậy paired bootstrap · hybrid
        so với dense.
      - **Trả lời (N13):** độ phủ trích dẫn · tỉ lệ từ chối (từ chối đúng, từ chối nhầm).
      - **Độ trễ và tài nguyên (N13, N15):** p50 và p95 (vì sao báo p95 chứ không báo trung bình) ·
        p95 từng service classify / embed / rerank · RSS · vCPU × `OMP_NUM_THREADS`.
      - **Rerank (N15 Khối A):** nDCG@5 có/không rerank · trần recall@5 theo số ứng viên (12 → 0,83,
        20 → 0,95) · tỉ lệ lượt mơ hồ · parity thứ hạng fp32 ↔ INT8.
      - **Số đã đo ở N1–N12 sẽ vào báo cáo:** parity cosine INT8 · 30/30 câu ngoài phạm vi ·
        4/4 phần tóm tắt · tỉ lệ lượt không gọi LLM (nếu đã đo).
- [ ] 🖐 **Buổi đọc — người dùng tự làm, không giao AI:** đọc tài liệu, mở CSV/PNG của N13 và
      bảng N15 bên cạnh, **tự tính tay recall@5 của 3 câu hỏi** rồi đối chiếu với số harness in ra.
- [ ] 🤝 Hỏi đáp với agent `mentor` theo kiểu hội đồng: nó hỏi, bạn trả lời bằng số của mình.
      Câu nào chưa trả lời được thì ghi lại, AI bổ sung lời giải vào tài liệu.

**File sẽ đụng:** `docs/on-tap/ngay-16-doc-so-lieu-ky-thuat.md` — chỉ tài liệu, không đụng code.

**Chạm Dev B:** không giao cắt.

**Phải giải thích được:**
- recall@5 và nDCG@5 khác nhau ở đâu? Khi nào recall@5 cao mà nDCG@5 vẫn thấp?
- Vì sao báo p95 mà không báo độ trễ trung bình?
- Khoảng tin cậy bootstrap "chứa 0" nghĩa là gì, và vì sao khi đó không được nói "A tốt hơn B"?
- Độ phủ trích dẫn 0,80 nghĩa là gì trên một câu trả lời cụ thể?

**Cổng ra (DoD):** tự giải thích được mỗi con số trong 2–3 câu, kèm số của mình · tính tay
recall@5 của 3 câu hỏi khớp số harness · mọi câu chưa trả lời được đã có lời giải trong tài liệu.

**Minh chứng báo cáo:** không có — đây là buổi học. Tài liệu đọc là nguồn để viết chương đánh giá.

---

## Ngày 17 — T4 07/10 — Kiểm thử bảo mật phần dữ liệu (3/5 bài, bài cache không áp dụng)

> **Mục tiêu:** chứng minh mô hình ngôn ngữ **không trở thành đường vòng qua RLS**.

**Điều kiện vào:** `test_rls.py` từ Ngày 1 đang chạy trong CI. Ba bài hôm nay là **mức cao hơn:
tấn công qua ĐƯỜNG NGÔN NGỮ chứ không qua đường SQL.**

**Việc:**

- [ ] 🖐 **BÀI (1) — CÁCH LY TENANT QUA NGÔN NGỮ.** Hỏi tenant A một câu **chỉ trả lời được bằng
      tài liệu của B** → phải **TỪ CHỐI**, không phải trả lời sai và cũng không phải trả lời đúng.
      ⚠️ **Đây là bài quan trọng nhất:** RLS chặn được truy vấn, nhưng **chỉ bài này** chứng minh
      mô hình không trở thành đường vòng qua RLS.
- ~~🖐 **BÀI (2) — CÁCH LY CACHE.**~~ **Không áp dụng** (đổi 10/10/2026): Ngày 16 đã bỏ nên không
  có semantic cache để kiểm. Ghi "không áp dụng" kèm lý do vào bảng 5 bài, không để trống.
- [ ] 🖐 **BÀI (3) — PII TRONG LOG.** Grep tự động tìm số điện thoại, email, nội dung tin nhắn
      thô trên **TOÀN BỘ** log.
- [ ] 🖐 Xác nhận `ai-service` kết nối CSDL bằng role **`ai_app`** (không phải `crm_owner`).

**Chạm Dev B:** Dev B làm 2 bài còn lại (payload không định danh · bộ adversarial) + UC038.
**Tổng 5 bài** — bài thứ 6 về "quyền công cụ" thuộc sheet *Mở rộng sau đồ án*, ghi **"không áp
dụng" kèm lý do**, không để ô trống.

**Phải giải thích được:**
- Vì sao "trả lời đúng bằng tài liệu của B" cũng là **sai**, không chỉ "trả lời sai"?
- RLS đã chặn ở tầng SQL rồi, vậy bài (1) còn chứng minh thêm điều gì?

**Cổng ra (DoD):** **2/2 bài đạt** (bài 2 không áp dụng) · kết quả grep PII = **0**.

**Minh chứng báo cáo:** 2/2 bài đạt, bài 2 ghi "không áp dụng" · ảnh chụp tenant A **TỪ CHỐI đúng** khi được hỏi về tài liệu
của B · kết quả grep PII = 0 · ảnh chụp `SELECT current_user` = `ai_app`.

---

## Ngày 18 — T5 08/10 — Triển khai gọn trên 1 instance cloud + dữ liệu doanh nghiệp thật · ⏸ HOÃN

⏸ **HOÃN (đổi lần hai 10/10/2026, người dùng chốt):** không làm trong đợt này. Sau N17, người dùng
chuyển sang nối và kiểm các UC AI trên giao diện; khi lên production thì làm ngày này trước N20. Nội
dung giữ nguyên bên dưới.

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

## Ngày 19 — T6 09/10 — Load test rút gọn · ⏸ HOÃN

⏸ **HOÃN (đổi 10/10/2026, người dùng chốt):** không làm trong đợt này, nội dung giữ nguyên bên dưới
để làm sau. Ở N20, ba ô #1, #24, #25 của bảng chỉ số ghi "chưa đo (hoãn)".

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

## Ngày 20 — T7 10/10 — [Nghiệm thu] Chạy lại toàn bộ bộ test và eval cuối · ⏸ HOÃN

⏸ **HOÃN (đổi lần hai 10/10/2026, người dùng chốt):** không làm trong đợt này, làm sau N18 khi lên
production. Nội dung giữ nguyên bên dưới. Đợt này kết thúc ở N17.

> **Mục tiêu:** **một ảnh chụp toàn bộ bộ test xanh TRONG MỘT LẦN CHẠY.**

**Công cụ dùng lại:** eval harness một lệnh (N13) · `test_rls.py` (N1) · một lệnh test của Dev B (N13).

**Việc:**

- [ ] 🖐 **Chạy MỘT LƯỢT:** CI đầy đủ (gồm cổng chặn ML runtime **và** cổng dung lượng image) ·
      test RLS · eval RAG bằng lệnh đóng gói Ngày 13 · contract test.
      *Đổi 10/10: cổng dung lượng sẽ đỏ vì Ngày 16 đã bỏ — ghi nhận, không sửa trong đợt này.*
- [ ] 🖐 Ghi kết quả **có dấu thời gian** làm bằng chứng cuối.
- [ ] 🖐 Xử lý mọi ca còn đỏ.
- [ ] 🖐 Điền **phần Dev A** của bảng chỉ số nghiệm thu (bảng cuối file này + sheet xlsx). Ô của
      Ngày 19 ghi "chưa đo (hoãn)", không để trống.

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

## Ngày 21 — CN 11/10 — 🏁 MỐC M3 · Báo cáo cuối + tài liệu kiến trúc + ADR · ⏸ HOÃN

⏸ **HOÃN (đổi 10/10/2026, người dùng chốt):** không làm trong đợt này, nội dung giữ nguyên bên dưới
để làm sau, cùng bốn việc hoãn từ Ngày 14 (video, biểu đồ `latency_breakdown`, báo cáo 6 UC, bảng
chỉ số giữa kỳ).

> **Mục tiêu:** gói bàn giao nộp được.

**ADR sinh trong 21 ngày:** ADR-0017 (4 quyết định hợp đồng, N1) · ADR bỏ nhánh A router (N4,
Dev B) · ADR chốt nhánh router (N5, Dev B) · ADR fine-tune ship hay rollback (N7) · ADR cấp vCPU
(N15) · ADR bật/tắt rerank (N15, ghi vào ADR-0006) · ADR phạm vi.

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
| 1 | p95 độ trễ endpoint chat | < 4.000 ms và **KHÔNG tăng dần** | N19 ⏸ | chưa đo (hoãn) | |
| 2 | Tổng p95 phần suy luận CPU | < 480 ms (classify 60 + embed 120 + rerank 300) | N13, N15 | | |
| 3 | recall@5 trên bộ vàng | **≥ 0,85** (bộ vàng ≥ 80 cặp) | N13, N20 ⏸ | | |
| 4 | Độ phủ trích dẫn | ≥ 0,80 | N13, N20 ⏸ | | |
| 5 | Rò rỉ dữ liệu giữa tenant | **0 trường hợp** | N1, N7, N17, N18 ⏸ | | |
| 6 | Flyway V201–V209 chạy sạch | 9 dòng history, 6 bảng, đủ chỉ mục | N1 | | |
| 7 | Test cách ly tenant trong CI | **3/3 ca xanh** | N1 | | |
| 8 | Dung lượng image `ai-service` | **< 400 MB** (đang 776 MB) | N1, N20 ⏸ (N16 đã bỏ) | | |
| 9 | Parity cosine INT8 vs fp32 (encoder base) | ≥ 0,995 | N2 | | |
| 10 | Số chiều vector khớp lược đồ | **1024** — `INSERT` thật không lỗi | N2 | | |
| 11 | Chênh lệch recall@5 (1 tenant vs 20 tenant) | < 3 điểm | N6 | | |
| 12 | Hybrid thắng dense-only | **≥ 5 điểm recall@5** | N6 | | |
| 13 | Baseline recall@5 của model pretrained | Đo và **LƯU trước** khi reindex | N6 | | |
| 14 | Parity cosine bản **FINE-TUNE** | ≥ 0,995 — không đạt thì rollback | N7 | | |
| 15 | Hiệu số recall@5 fine-tune vs pretrained | KTC 95% paired bootstrap **không chứa 0** | N7 | | |
| 16 | Thời gian reindex toàn bộ chunk | Đo thật; **0 giây kho tri thức trống** | N7, N11 | | |
| 17 | Cổng quyết định bật rerank | ≥ 5 điểm nDCG@5 **VÀ** p95 < 4 s | N8 → N15 | | |
| 18 | 30 câu hỏi ngoài phạm vi trả rỗng đúng | **30/30** | N10 | | |
| 19 | Eval harness tái lập được | Chạy 2 lần ra cùng con số; mỗi số kèm config | N13, N20 ⏸ | | |
| 20 | Cách ly tenant qua **ĐƯỜNG NGÔN NGỮ** | Hỏi A về tài liệu B → phải **TỪ CHỐI** | N17 | | |
| 21 | Cách ly bộ nhớ đệm ngữ nghĩa | 2 tenant → 2 câu trả lời từ 2 kho tri thức | N17 | không áp dụng — N16 đã bỏ, không có cache | |
| 22 | PII trong log *(cùng Dev B)* | grep tự động = **0** | N17 | | |
| 23 | Năm bài kiểm thử bảo mật *(cùng Dev B)* | 5/5 đạt (bài "quyền công cụ" ghi *không áp dụng*) | N17, N20 ⏸ | | |
| 24 | Baseline 10 người dùng / 10 phút | p95 < 2.500 ms, lỗi 0% | N19 ⏸ | chưa đo (hoãn) | |
| 25 | Tải mục tiêu 50 người dùng / 15 phút | p95 < 4.000 ms, lỗi < 1%, KHÔNG tăng dần | N19 ⏸ | chưa đo (hoãn) | |
| 26 | Nguồn dữ liệu thử nghiệm *(cùng Dev B)* | Ghi rõ tự soạn/công khai hay đã ẩn danh | N18 ⏸, N21 ⏸ | | |
| 27 | Số use case hoàn thành *(cùng Dev B)* | 17/17 UC | N20 ⏸ | | |

⏸ = ngày đó đã hoãn (đổi 10/10/2026; N18 và N20 hoãn ở lần đổi thứ hai).

---

# Ba mốc — điều kiện thoát và hành động khi trượt

| Mốc | Hạn | Điều kiện thoát | 🚨 Trượt thì làm gì |
|---|---|---|---|
| **M1** Nền tảng dữ liệu | hết **N7** (27/09) | Tài liệu thật vào chunks · test cách ly tenant xanh · hybrid thắng dense ≥ 5 điểm · router chạy trong `ai-classify` | **Cắt rerank khỏi N8** và **bỏ semantic cache ở N16** |
| **M2** Luồng chat chạy trọn | hết **N14** (04/10) | Mỗi ngả một lượt thật đi trọn tới `telemetry`: trả lời có trích dẫn · từ chối · chuyển giao *(đổi 10/10)* | Chưa sang N15, sửa tới khi luồng chat chạy |
| **M3** Nghiệm thu | ⏸ **hoãn** cùng N21 *(đổi 10/10)* | 7/7 chỉ số đạt · gói bàn giao · video demo 17 UC + slide | Hạn thật của đồ án là 31/12/2026 |

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
      instance cloud **cho Ngày 18** (N18 đã hoãn 10/10 — chưa cần trong đợt này).
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
