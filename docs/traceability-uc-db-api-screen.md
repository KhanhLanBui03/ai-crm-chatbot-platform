# Truy vết Use Case ↔ Database ↔ OpenAPI ↔ Màn hình

> Nguồn chân lý nghiệp vụ **duy nhất** là 42 use case ở `docs/plan/Dac-ta-UseCase-Dot*.docx`.
> Tài liệu này truy vết **ngược** từ đó xuống lược đồ, hợp đồng API và giao diện. Lược đồ, hợp
> đồng và màn hình phục vụ use case — không bao giờ ngược lại.
>
> Cập nhật lần cuối: **25/08/2026**, sau migration V113 (Track A) và V208 (Track B).

---

## 1. Chuẩn đánh giá

Một use case được coi là **đạt** khi **luồng sự kiện chính và hậu điều kiện** chạy được trên
lược đồ thật. Luồng thay thế chỉ bắt buộc khi nó là ràng buộc **an toàn** hoặc **tuân thủ**.

Chuẩn này quan trọng vì nó quyết định ranh giới. Ví dụ UC013 3.1 có "mẫu câu trả lời có sẵn",
nhưng luồng chính UC013 bước 4 dùng "gợi ý truy hồi từ kho tri thức" — hai cơ chế khác nhau cho
cùng một ô soạn thảo, và chỉ cơ chế thứ hai nằm trong luồng chính.

### Thứ tự ưu tiên khi có thiếu hụt

1. Ánh xạ DTO · 2. Trường suy ra · 3. Chỉnh màn hình · 4. Thêm cột · 5. **Thêm bảng**

Thêm bảng là lựa chọn cuối. Toàn bộ đợt rà soát này chỉ thêm **hai** bảng, và cả hai đều vì
hậu điều kiện của use case nêu tường minh chứ không phải vì một màn hình muốn có.

---

## 2. Ma trận truy vết — 42 dòng

Ký hiệu schema: `pf` = `platform` · `eg` = `engagement` · `sl` = `sales` · `an` = `analytics`
(Track A) · `kn` = `knowledge` · `ai` = `ai` · `ig` = `integration` (Track B).

### Nhóm A — Nền tảng, tài khoản, gói dịch vụ

| UC | Màn | Endpoint | Bảng · cột then chốt |
|---|---|---|---|
| **UC001** Đăng ký doanh nghiệp | SCR001, SCR002 | `POST /auth/register`, `/auth/verify-email`, `/auth/resend-verification` | `pf.tenants` · `pf.users.password_hash` `email_verified_at` · `pf.user_roles` · `pf.tenant_subscriptions` · `pf.usage_records` · `sl.pipelines` `deal_stages` (phễu mặc định) · `pf.audit_logs` · hàm `slug_is_taken()` |
| **UC002** Đăng nhập | SCR003 | `POST /auth/login` `/refresh` `/logout` | `pf.users.failed_login_count` `locked_until` `status` · `pf.roles.permissions` · `pf.audit_logs.ip_address` · hàm **`find_login_identity()`** |
| **UC003** Người dùng và phân quyền | SCR008, SCR009, SCR010 | `/users`, `/users/{id}`, `/users/{id}/disable`, `/users/{id}/resend-invitation`, `/roles` | `pf.users` · `pf.roles` · `pf.user_roles` · `pf.subscription_plans.max_users` (kiểm hạn mức b4) · `pf.audit_logs` |
| **UC004** Hồ sơ doanh nghiệp | SCR007 | `GET/PATCH /tenant` | `pf.tenants.business_hours` `ai_tone` `timezone` `locale` **`assignment_mode`** **`assignment_config`** · `pf.audit_logs.before_data/after_data` |
| **UC005** Xem và nâng cấp gói | SCR012+013 | `/plans`, `/subscription`, `/subscription/change` | `pf.subscription_plans` · `pf.tenant_subscriptions.scheduled_plan_id` `scheduled_effective_at` (hạ gói từ chu kỳ sau, 6.3) · `pf.usage_records.quota_value` |
| **UC006** Theo dõi hạn mức | SCR014, SCR015 | `/usage`, `/usage/daily` | `pf.usage_records` · **`an.metrics_daily`** (token, chi phí, tách theo kênh và nhánh — b4, b7) |
| **UC007** Quản lý doanh nghiệp thuê bao | *(cấp nền tảng, ngoài dashboard tenant)* | — | `pf.tenants.status` `suspended_reason` `suspended_at` · `pf.users.scope='PLATFORM'` · `pf.audit_logs` |

### Nhóm B — Kênh và hội thoại

| UC | Màn | Endpoint | Bảng · cột then chốt |
|---|---|---|---|
| **UC008** Cấu hình kênh | SCR016, SCR017 | `/channels`, `/channels/{id}`, `/channels/{id}/verify` | `eg.channels.credential_encrypted` `credential_key_id` `webhook_secret_encrypted` `status` `last_error` · `pf.audit_logs` |
| **UC009** Nhúng Web Widget | SCR018 | `/widget-config`, `/widget-config/snippet` | `eg.channels.widget_key` `config` (màu, vị trí, lời chào, tên miền cho phép) · hàm **`resolve_widget_key()`** |
| **UC010** Khách gửi tin nhắn | *(web-widget)* | *(gateway → java-core)* | `eg.conversations` · `eg.messages` · `pf.usage_records` (hết hạn mức → 6.2) · `ai.ai_interactions` |
| **UC011** Tiếp nhận tin và hợp nhất danh tính | — | *(webhook)* | `eg.messages.external_message_id` **UNIQUE** (chống trùng webhook, 4.1) · `eg.channel_identities` · `eg.contacts` · `pf.outbox_events` (cùng transaction, b9) |
| **UC012** Hộp thư hợp nhất | SCR019+020 | `/conversations`, `/{id}`, `/{id}/messages`, `/{id}/context`, `/{id}/read` | `eg.conversations.last_message_at` `unread_count` `message_count` `summary` · `eg.messages.sender_type` · WebSocket (ADR-0013) |
| **UC013** Nhân viên trả lời | SCR019+020 | `POST /conversations/{id}/messages`, `POST /knowledge/search` | `eg.messages.direction` `delivery_status` · `eg.conversations.first_response_at` (b9) · `kn.knowledge_chunks` (gợi ý b4) |
| **UC014** Chuyển giao AI → nhân viên | SCR021 | `POST /conversations/{id}/handoff` | `eg.conversations.status` `handover_at` `handover_reason` `priority` · `pf.tenants.assignment_mode` (chọn nhân viên, b6) · `an.metrics_daily.handover_count` (b9) |
| **UC015** Gán hội thoại | SCR021 | `POST /conversations/{id}/assign` | `eg.conversations.assigned_user_id` `assigned_at` · `pf.outbox_events` (b7) · `pf.audit_logs` (4.2) |
| **UC016** Quản lý danh bạ | SCR024, SCR025, SCR026, SCR027 | `/contacts`, `/{id}`, `/{id}/merge` | `eg.contacts.merged_into_contact_id` (hợp nhất mềm, 5a) · `eg.channel_identities` · `pf.audit_logs` |
| **UC017** Ghi chú và gắn thẻ | SCR028 | `/contacts/{id}/notes`, `/tags`, `/contacts/{id}/tags/{tagId}` | `eg.contact_notes.author_user_id` · `eg.tags.usage_count` · `eg.contact_tags` |

### Nhóm C — Tri thức và tích hợp

| UC | Màn | Endpoint | Bảng · cột then chốt |
|---|---|---|---|
| **UC018** Tải lên tài liệu | SCR029 | `POST /documents` | `kn.knowledge_documents.status='PENDING'` `file_path` · `pf.subscription_plans.max_documents` (5.6) · `pf.outbox_events` |
| **UC019** Nạp và lập chỉ mục | SCR030, SCR033 | `/ingestion-jobs`, `/documents/{id}/reindex` | `kn.knowledge_documents.status` `chunk_count` `error_message` `indexed_at` · `kn.knowledge_chunks.embedding` `content_segmented` `embedding_model` `embedding_version` |
| **UC020** Quản lý kho tri thức | SCR030, SCR031, SCR032 | `/documents`, `/{id}`, `/{id}/chunks`, `POST /knowledge/search` | `kn.knowledge_documents.version` (thay thế không để trống tri thức, 10a) · `kn.knowledge_chunks.heading` |
| **UC021** Cấu hình MCP | SCR037, SCR038, SCR039 | `/mcp-servers`, `/{id}/handshake`, `/tools`, `/tools/{toolId}` | `ig.mcp_servers.spec_version` `credential_encrypted` `allowed_tools` · **`tool_schema_cache`** — sổ đăng ký: `schema_hash`, `enabled` (mặc định false, b7), `risk_level`, `requires_approval` (9.2) |

### Nhóm D — Xử lý của tác tử AI

| UC | Màn | Endpoint | Bảng · cột then chốt |
|---|---|---|---|
| **UC022** Phân loại ý định và định tuyến | SCR036 | `/ai-interactions` | `ai.ai_interactions.intent` `intent_confidence` `branch` `model_name` `model_version` · **`safety_flag`** (chỉ thị ẩn, 5.2) · `eg.conversations.primary_intent` |
| **UC023** Trả lời theo tri thức | SCR031, SCR036 | *(nội bộ)* + `POST /knowledge/search` | `kn.knowledge_chunks` (HNSW + GIN) · `ai.ai_interactions.retrieved_chunk_ids` `retrieval_top_score` `prompt_tokens` `completion_tokens` `cost_vnd` `latency_ms` |
| **UC024** Truy vấn hệ thống ngoài qua MCP | SCR035, SCR040 | `/tool-calls`, `/tool-calls/{id}/approval` | `ai.ai_tool_calls.tool_name` `arguments` `latency_ms` `outcome` `approval_status` · `ai.ai_interactions.safety_flag` (kết quả có dạng chỉ thị, 6.2) |
| **UC025** Từ chối khi thiếu căn cứ | SCR034, SCR051 | `GET /knowledge-gaps` | `ai.ai_interactions.is_answered=false` `refusal_reason` `retrieval_top_score` · `safety_flag='INTERNAL_DATA_PROBE'` (3.4) · danh sách khoảng trống = **truy vấn gộp**, không phải bảng |
| **UC026** Tóm tắt hội thoại | SCR019+020 | `/conversations/{id}/context` | `eg.conversations.summary` `summarized_at` · `ai.ai_interactions.branch='SUMMARY'` |
| **UC027** Đánh giá chất lượng | SCR019+020 | `POST /ai-interactions/{id}/feedback` | `ai.ai_feedback.rating` `reason_code` `rater_type` (khách vs nhân viên tách riêng, 1a-2a) · chỉ mục `uq_feedback_rater` |
| **UC028** Chặn lời gọi vi phạm | SCR035, SCR040, SCR054 | `/tool-calls`, `/safety-events` | `ai.ai_tool_calls.decision` `block_reason` `risk_level` · `ig.mcp_servers.tool_schema_cache[].schema_hash` (**b3 — đối chiếu hash đã duyệt**) |

### Nhóm E — Bán hàng và cơ hội

| UC | Màn | Endpoint | Bảng · cột then chốt |
|---|---|---|---|
| **UC029** Trích xuất tín hiệu | SCR042 | *(nội bộ)* `POST /internal/leads` | `sl.leads.interested_product` `budget_min/max` `budget_confidence` (4.4) `urgency` `interest_summary` · `ai.ai_interactions.branch='EXTRACTION'` |
| **UC030** Chấm điểm tiềm năng | SCR042 | `GET /leads/{id}/scores` · `PUT /internal/leads/{id}/score` | **`sl.lead_scores`** · `score` `model_version` `features` `top_factors` `confidence` `scored_at` — **append-only**, `REVOKE UPDATE` · `sl.leads.current_score` là ảnh chụp dòng mới nhất · `pf.tenants.lead_score_threshold` |
| **UC031** Tự động tạo Lead | SCR041 | *(nội bộ)* | `sl.leads.source='AI_AUTO'` `source_conversation_id` · `pf.tenants.auto_lead_creation` `assignment_mode` (b5) |
| **UC032** Quản lý Lead | SCR041, SCR042, SCR043 | `/leads`, `/{id}`, `/{id}/scores` | `sl.leads.status` `disqualified_reason` (7.2) · **`sl.lead_scores`** (lịch sử điểm, b6) · `pf.audit_logs` |
| **UC033** Chuyển Lead thành Deal | SCR042, SCR046 | `POST /leads/{id}/convert` | `sl.leads.converted_at` `status='CONVERTED'` (giữ bản ghi, b7) · `sl.deals.lead_id` UNIQUE · `deals.source='AI_LEAD'` (7.2) |
| **UC034** Deal theo phễu | SCR044, SCR045 | `/pipelines`, `/deals`, `/{id}`, `/{id}/stage` | `sl.deal_stages.required_fields` (5.1) `is_won` `is_lost` · `sl.deals.stage_changed_at` (b6) `close_reason` (4.2) · khoá ngoại kép `(pipeline_id, stage_id)` |
| **UC035** Hoạt động chăm sóc | SCR047 | `/activities`, `/{id}` | `sl.activities.type` `outcome` `remind_at` `remind_status` `source` (AUTO vs MANUAL, 6.2) |

### Nhóm F — Thống kê, kiểm toán, tuân thủ

| UC | Màn | Endpoint | Bảng · cột then chốt |
|---|---|---|---|
| **UC036** Bảng điều khiển tổng quan | SCR006, SCR048 | `/analytics/overview` | **`an.metrics_daily`** — hậu điều kiện nói rõ *"đọc từ mô hình đọc đã tổng hợp sẵn, không truy vấn trực tiếp vào bảng giao dịch"* |
| **UC037** Phễu chuyển đổi | SCR050 | `/analytics/funnel` | `eg.conversations` · `sl.leads.source` (so AI_AUTO với MANUAL, b7-8) · `sl.deals` · `sl.deal_stages` |
| **UC038** Thống kê chủ đề | SCR052 | `/analytics/topics` | `eg.conversations.topic` · `an.metrics_daily.ai_handled_count` (tỉ lệ xử lý trọn vẹn theo chủ đề, b6) |
| **UC039** Hiệu quả và chi phí AI | SCR051, SCR034 | `/analytics/ai-performance`, `/knowledge-gaps` | **`an.metrics_daily`** · `cost_vnd` `prompt_tokens` `latency_p50/p95_ms` `refusal_count` tách theo `branch` và `model_name` (2.2) · `ai.ai_feedback` |
| **UC040** Nhật ký kiểm toán | SCR054 | `/audit-logs`, `/{id}/reveal`, `/safety-events` | `pf.audit_logs` — `REVOKE UPDATE, DELETE` (2.2 chỉ-ghi-thêm) · cảnh báo an toàn hợp nhất **ba nguồn** (xem §5) |
| **UC041** Xoá dữ liệu cá nhân | SCR055, SCR056, SCR057, SCR058 | `/erasure-requests`, `/preview`, `/{id}`, `/{id}/execute` | `pf.data_erasure_requests.items` (tiến độ theo bảng, 6.4) `legal_basis` `certificate_uri` · `eg.contacts.anonymized_at` · `eg.messages.is_redacted` |
| **UC042** Xuất báo cáo ra tệp | *(nút trên SCR048–SCR052)* | `POST /reports/exports` | `pf.audit_logs` `action='REPORT_EXPORTED'` — hiện thực **nhánh 4.2** (xuất đồng bộ), xem §6 |

**42/42 đạt** theo chuẩn ở §1.

---

## 3. Phân loại 54 màn hình

### CORE — 47 mã màn

Bắt buộc để thực hiện ít nhất một use case; gỡ đi là use case đó không hoàn thành được.

SCR001 SCR002 SCR003 SCR004 SCR005 · SCR007 SCR008 SCR009 SCR010 · SCR012+013 SCR014 ·
SCR016 SCR017 SCR018 · SCR019+020 SCR021 · SCR024 SCR025 SCR026 SCR027 SCR028 ·
SCR029 SCR030 SCR031 SCR032 · SCR035 SCR037 SCR038 SCR039 SCR040 ·
SCR041 SCR042 SCR043 SCR044 SCR045 SCR046 SCR047 · SCR048 SCR050 SCR051 SCR052 ·
SCR054 SCR055 SCR056 SCR058

### SUPPORTING — 7 mã màn

Hỗ trợ quan sát hoặc quản trị; use case vẫn hoàn thành được nếu thiếu, nhưng người vận hành mất
đường nhìn vào hệ thống.

| Màn | Vì sao giữ dù không bắt buộc |
|---|---|
| SCR006 | Cùng component với SCR048, khác khung dẫn theo người đọc — chi phí thêm gần bằng không |
| SCR015 Mức dùng theo ngày | UC006 b5 có biểu đồ theo ngày, nhưng b3 (số hội thoại trên hạn mức) mới là thứ quyết định |
| SCR033 Tiến độ nạp | UC019 b1 "theo dõi tiến độ" — chiếu từ `knowledge_documents.status`, không có dữ liệu riêng |
| SCR034 Khoảng trống tri thức | UC039 b9-10 là luồng chính, nhưng đây là màn đọc thuần |
| SCR036 Giám sát lượt xử lý | Không UC nào đòi danh sách từng lượt. **Giữ vì giá trị chứng minh**: `retrieved_chunk_ids` là câu trả lời cho *"làm sao chứng minh bot không bịa?"* |
| SCR049 Hội thoại theo ngày | UC036 b4 biểu đồ xu hướng — tách ra thành màn riêng là tiện ích |
| SCR057 Tiến độ xoá theo bảng | UC041 6.4 (xoá dở dang phải chạy lại được) là luồng thay thế, nhưng là **ràng buộc tuân thủ** nên vẫn thuộc chuẩn đạt |

47 + 7 = **54 mã màn**. Số trang thực tế ít hơn: SCR012+013 và SCR019+020 mỗi cặp chung một
trang, SCR006 và SCR048 chung một component khác khung dẫn.

### FUTURE — 0 màn

Sau đợt rà soát, không còn màn nào không truy vết được tới use case. Bốn màn thuộc nhóm này đã
gỡ khỏi repo (xem §4).

---

## 4. Kết quả — tám danh sách

### 4.1. Cột thực sự cần thêm

| Cột | Bảng | Use case đòi | Mức |
|---|---|---|---|
| `assignment_mode` `assignment_config` | `pf.tenants` | UC014 b6 · UC015 · UC031 b5 | P2 |
| `safety_flag` | `ai.ai_interactions` | UC022 5.2 · UC024 6.2 · UC025 3.4 · **UC040 b8** | P1 |
| cấu trúc `tool_schema_cache` (`schema_hash`, `enabled`, `risk_level`, `requires_approval`) | `ig.mcp_servers` | UC021 hậu điều kiện · **UC028 b3** | P1 |

Ba mục, **không** mục nào cần bảng mới.

### 4.2. Bảng thực sự cần thêm — hai bảng

| Bảng | Vì sao không tránh được |
|---|---|
| `sl.lead_scores` | UC030 hậu điều kiện nêu tường minh *"các bản ghi điểm cũ được giữ lại thành lịch sử thay vì bị ghi đè"*. `leads.current_score` chỉ giữ giá trị mới nhất. Hợp đồng `java-core-to-ai-service.yaml` đã khai bảng `sales.LEAD_SCORES` từ trước — nó vốn phải có ở V108 |
| `an.metrics_daily` | Không phải vì dashboard chậm mà vì **ranh giới quyền**: chi phí, token và độ trễ nằm ở `ai.ai_interactions` (Track B), `crm_app` không có `USAGE` trên schema `ai` (V111), mà `/analytics/*` do java-core phục vụ. Không có bảng đích thì UC039 không có đường lấy số. UC036 hậu điều kiện cũng đòi "mô hình đọc" tường minh |

### 4.3. Cột có thể bỏ — **liệt kê, không gỡ**

| Cột | Không use case nào dùng |
|---|---|
| `eg.conversations.csat_score` | UC027 là đánh giá **câu trả lời của AI** (`ai_feedback`), không phải khảo sát hài lòng hội thoại |
| `eg.conversations.subject` | Hộp thư hiển thị tên khách + trích tin cuối (UC012 b3) |
| `eg.contacts.consent_marketing` | Không có use case marketing nào |
| `ai.ai_feedback.correction_text` | UC027 b5 chỉ có "nhận xét bổ sung" = `comment` |
| `sl.deal_stages.probability` | UC034 không nêu xác suất thắng ở bất kỳ bước nào |
| `pf.tenants.phone` | UC004 b2 liệt kê đúng sáu trường, không có số điện thoại |

**Vì sao không gỡ:** gỡ sáu cột này buộc phải sửa entity, DTO và tầng mock đang xanh, đổi lại
tiết kiệm vài byte mỗi dòng. Ghi chú chúng ở đây và trong ERD rẻ hơn, và trả lời được câu
*"cột này phục vụ use case nào?"* nếu hội đồng hỏi: **không cái nào — đây là dự phòng có ý thức.**

### 4.4. API dư so với use case — đã gỡ

| Đường dẫn | Kết luận |
|---|---|
| `GET /me/sessions` · `DELETE /me/sessions/{id}` | **REMOVE.** Không UC nào cho người dùng tự quản lý phiên |
| `GET /canned-responses` | **REMOVE.** Chỉ ở UC013 3.1 (thay thế); luồng chính dùng `/knowledge/search` |
| `GET/POST /assignment-rules` · `PATCH/DELETE /{ruleId}` | **SIMPLIFY** → hai trường của `GET/PUT /tenant` |
| `PATCH /knowledge-gaps/{gapId}` | **REMOVE.** Không UC nào cho phép đóng một khoảng trống bằng tay |
| `GET /reports/exports` · `GET /reports/exports/{exportId}` | **REMOVE.** Xuất đồng bộ thì không có tệp nào lưu lại để liệt kê |

**85 → 78 đường dẫn · 109 → 99 thao tác.** Kèm theo đó năm schema mồ côi bị gỡ
(`PhienDangNhap`, `MauCauTraLoi`, `QuyTacPhanCong`, `LuuQuyTacPhanCongRequest`, `TepBaoCao`),
một tham số (`SessionId`), một enum (`TrangThaiTepBaoCao`), và `KhoangTrongTriThuc` bỏ hai
trường `status` / `resolvedDocumentId`.

### 4.5. Màn dư so với use case — đã gỡ

| Màn | Vì sao |
|---|---|
| **SCR011** Phiên đăng nhập | Không truy vết được tới UC nào. UC003 3a và UC007 b10 đòi **hệ thống** thu hồi phiên, việc đó nằm trong `/users/{id}/disable` |
| **SCR053** Tệp báo cáo | UC042 hiện thực nhánh 4.2 — không có tệp lưu lại |

### 4.6. Màn nên gộp — đã gộp

| Trước | Sau |
|---|---|
| **SCR022** Quy tắc phân công + **SCR023** Tạo quy tắc | Một khối "Phân công" trong **SCR007** Hồ sơ doanh nghiệp, dùng lại mẫu M4 |

**58 → 54 màn.**

### 4.7. Bảy nhóm endpoint mock — kết luận

| Nhóm | Kết luận | Cách phục vụ sau đợt này |
|---|---|---|
| `/leads/{id}/scores` | **KEEP** | Bảng thật `sl.lead_scores` (V113) |
| `/tools`, `/tools/{toolId}` | **KEEP** | `ig.mcp_servers.tool_schema_cache` có cấu trúc cam kết (V208) |
| `/safety-events` | **KEEP** | Truy vấn hợp nhất ba nguồn (V208 + sẵn có) — xem §5 |
| `GET /knowledge-gaps` | **SIMPLIFY** | Truy vấn gộp trên `ai.ai_interactions`; `PATCH` loại khỏi phạm vi |
| `/canned-responses` | **REMOVE FROM SCOPE** | Thay bằng `/knowledge/search` đã có |
| `/assignment-rules` | **SIMPLIFY** | Gộp vào `GET/PUT /tenant` |
| `/reports/exports` | **SIMPLIFY** | `POST` giữ, chuyển sang xuất đồng bộ; hai `GET` loại khỏi phạm vi |

### 4.8. Đánh giá cuối

| Chỉ tiêu | Trước rà soát | Sau |
|---|---|---|
| **Use Case Coverage** | 38/42 (UC030, UC036, UC039, UC040 gãy ở hậu điều kiện hoặc luồng chính) | **42/42** |
| **Database Coverage** | 30 bảng · 1 hợp đồng nội bộ trỏ vào bảng không tồn tại · 1 ranh giới quyền không có đường vượt | **32 bảng** · +3 nhóm cột |
| **Screen Coverage** | 58 màn · 3 màn không truy vết được | **54 mã màn** · 47 CORE, 7 SUPPORTING, 0 FUTURE |
| **API Coverage** | 85 đường dẫn · 7 nhóm chạy mock không bảng | **78 đường dẫn** · 2 nhóm có bảng thật, 2 nhóm là truy vấn gộp, 3 nhóm bỏ |
| **Thesis Scope Consistency** | ERD, OpenAPI và bản đặc tả lệch nhau ở 7 chỗ | Tài liệu này là nguồn chung; ERD §8 và §11 đã cập nhật theo |
| **Production Readiness** | — | **Chưa.** Xem §7 |

---

## 5. Ba quyết định đáng giải thích

### 5.1. Vì sao `/safety-events` không có bảng riêng

UC040 b8 đòi xem ba loại sự kiện cùng một chỗ, nhưng chúng có **ba chủ sở hữu khác nhau**:

| Loại | Nguồn | Ai ghi |
|---|---|---|
| Lời gọi công cụ bị chặn | `ai.ai_tool_calls.decision='BLOCKED'` | ai-service |
| Chỉ thị ẩn trong tin nhắn / kết quả công cụ / tài liệu | `ai.ai_interactions.safety_flag` | ai-service |
| Nỗ lực truy cập ngoài phạm vi doanh nghiệp | `pf.audit_logs.severity='CRITICAL'` | java-core |

`ai_app` **không** có `USAGE` trên schema của Track A — đó là ADR-0002, không phải thiếu sót.
Nếu dựng bảng `ai.safety_events` chung thì java-core phải ghi vào schema của Track B, tức mở
đúng cái đường mà ADR-0002 đóng lại. Gộp ở **tầng đọc** rẻ hơn nhiều và không đụng ranh giới.

`safety_flag` là **cột** chứ không phải bảng vì cả ba tình huống đều phát sinh trong một lượt
xử lý đã có bản ghi.

### 5.2. Vì sao sổ đăng ký công cụ nằm trong `jsonb`

UC028 b3 chạy **trước mọi lời gọi công cụ** — đó là đường nóng nhất của nhánh MCP. Công cụ
không có vòng đời độc lập với máy chủ: ngắt máy chủ là toàn bộ công cụ mất hiệu lực (UC021 1a).

**Đánh đổi thật:** PostgreSQL không cưỡng chế được từng trường bên trong `jsonb`, nên ràng buộc
"`risk_level = WRITE` thì `requires_approval` bắt buộc true và không tắt được" (UC021 9.2) rơi
về tầng ứng dụng. CSDL chỉ giữ được `CHECK (jsonb_typeof(...) = 'array')`.

### 5.3. Vì sao danh sách khoảng trống tri thức là truy vấn, không phải bảng

UC025 b7 đưa câu hỏi **vào** danh sách; UC039 b9-10 **đọc** nó, sắp theo tần suất. Không thao
tác nào của người dùng ghi vào nó, và mọi thuộc tính đều suy ra được từ chính các lượt từ chối:
`ai_interactions` với `is_answered = false`, nhóm theo `user_query` chuẩn hoá, đếm theo
`conversation_id` phân biệt.

**Đánh đổi:** gom nhóm bằng chuẩn hoá chuỗi chứ không bằng ngữ nghĩa, nên hai cách hỏi khác hẳn
về câu chữ của cùng một vấn đề sẽ nằm ở hai dòng. Chấp nhận được ở quy mô SME; nâng lên gom cụm
theo vector là việc của `conversation_metrics_daily` về sau.

---

## 6. UC042 — chỗ duy nhất thu hẹp có tuyên bố

UC042 luồng chính (b5-8) mô tả công việc chạy nền có trạng thái và hạn dùng của liên kết tải.
Nhưng **nhánh 4.2 của chính use case** nói: *"Nếu khối lượng dữ liệu nhỏ → xuất trực tiếp và
trả tệp ngay, không cần tạo công việc chạy nền."*

Ở quy mô SME, mọi báo cáo trong 42 use case đều rơi vào nhánh đó — dữ liệu một chu kỳ của một
tenant xuất hết trong một request. Nên hệ thống hiện thực **nhánh 4.2**:

- `POST /reports/exports` sinh tệp đồng bộ, trả thẳng nội dung.
- Hậu điều kiện *"ghi thao tác xuất vào nhật ký kiểm toán"* → `pf.audit_logs`,
  `action = 'REPORT_EXPORTED'`, `after_data` chứa loại báo cáo và phạm vi.
- Cảnh báo dữ liệu cá nhân (2.2) → 422 nếu thiếu `confirmPersonalData`.

**Cái mất:** không có danh sách tệp đã xuất, không có hạn dùng của liên kết. SCR053 gỡ theo.
Khi một lần xuất bắt đầu vượt 30 giây thì thêm `an.report_exports` — một migration cộng thêm,
không đòi sửa gì đang có.

Đây là **chỗ duy nhất** trong 42 use case mà hệ thống chọn một nhánh thay thế làm mặc định.
Nếu bảo vệ trước hội đồng, phải nói ra chỗ này chứ không lờ đi.

---

## 7. Production Readiness — chưa đạt, và thiếu đúng ba thứ

Lược đồ đã sẵn sàng cho cả ba; đây là việc ở tầng mã, không phải tầng thiết kế.

| Thiếu | Ảnh hưởng |
|---|---|
| Consumer `analytics-cg` ghi `an.metrics_daily` từ `crm.ai-interaction.v1` + `crm.conversation.v1` | UC006, UC036, UC038, UC039 chạy trên bảng rỗng cho tới khi có consumer |
| `web-widget` chưa có dòng mã nào | UC009 và UC010 chưa chạy đầu-cuối được |
| Nợ kỹ thuật: tách chunk khi build (gói chính 1,52 MB), ADR-0008 và ADR-0009 còn TODO | Không chặn nghiệp vụ |

---

## Phụ lục — kiểm chứng đã chạy

| Phép kiểm | Kết quả |
|---|---|
| `flyway migrate` hai làn | Track A **v113**, Track B **v208** |
| RLS: bảng thiếu `ENABLE`+`FORCE` | Đúng ba ngoại lệ (`subscription_plans`, `outbox_events`, `processed_events`) — hai bảng mới **đều** bật |
| Cô lập tenant trên `lead_scores` và `metrics_daily` | Tenant A thấy đúng 1 dòng của mình (điểm 85), tenant B thấy đúng 1 dòng của mình (điểm 40), không rò chéo |
| Quên `SET LOCAL app.tenant_id` | Nổ `42501` kèm thông báo chỉ đúng chỗ thiếu, không trả rỗng lặng lẽ |
| `ai_app` chạm `sales` / `analytics` | `ERROR: permission denied for schema sales` |
| `crm_app` `UPDATE sales.lead_scores` | `ERROR: permission denied` — append-only cưỡng chế bằng quyền, không bằng quy ước |
| `npm run gen:api` · `typecheck` · `build` | Sạch cả ba |
| Bộ kiểm CDP trên các màn bị đụng | **13/13 đạt**, console sạch — gồm ba route đã gỡ không render trang cũ |
