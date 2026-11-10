# Hợp đồng đợt tích hợp giao diện GD1–GD4 (nháp 24/10/2026, cập nhật 10/11 — thêm GD2)

⚠️ Nháp phía module AI. Kế hoạch đợt: [`docs/plan/ke-hoach-tich-hop-giao-dien.md`](../plan/ke-hoach-tich-hop-giao-dien.md)
(mục 1 liệt kê 11 thay đổi). **Người dùng chốt 24/10:** 8 UC AI là việc của Dev A từ dashboard tới
java-core tới ai-service, nên làm theo nháp này luôn, không chờ — Dev B được **báo** những chỗ đã đổi
ở file dùng chung (mục 0) để kéo về và góp ý.

Thứ tự ưu tiên khi lệch: đặc tả UC > `dashboard-api.yaml` > nháp này > code.

---

## 0. Tin gửi Dev B (dán nguyên)

> GD1 (UC018–UC020, kho tri thức) đã nối trọn dashboard → gateway → java-core → ai-service, nhánh
> `feat/giao-dien-gd1-kho`. Có đụng vài file chung, báo để bạn kéo về:
>
> 1. **`SecurityConfig` (java-core)** — thêm 3 dòng: `PATCH`/`DELETE /api/v1/documents/*` và
>    `POST /api/v1/documents/*/reindex` chỉ `TENANT_ADMIN`. Đọc vẫn mở cho mọi nhân viên.
> 2. **`docs/openapi/dashboard-api.yaml`** — phần Tri thức: thêm `PATCH /api/v1/documents/{id}` + schema
>    `SuaTaiLieu`; mô tả lại `reindex` (trả việc nạp của **bản bóng**, id mới — ADR-0031) và `DELETE`
>    (trả hạn mức, ADR-0023 (f)); tách mã 409/413/415/422 của tải lên theo đặc tả UC018; thêm response
>    dùng chung `AiKhongPhanHoi` (502). **Đã chạy `npm run gen:api`** — `api-schema.d.ts` sinh lại từ bản
>    này; bạn sửa YAML chỗ khác thì sinh lại đè lên là được.
> 3. **`UsageQuotaService`** — thêm `release(metric, amount)` (trả lại chỗ cho chỉ số tồn kho), không
>    đổi `lockForConsumption`/`consume`.
> 4. **`ListPage`** (dashboard) — thêm prop tuỳ chọn `loi`/`onThuLai`: truy vấn hỏng thì hiện
>    "Không tải được dữ liệu" thay cho "chưa có dữ liệu". Màn nào không truyền thì y như cũ.
> 5. **`features/audit/nhan.ts`** (màn nhật ký UC040 của bạn) — thêm 3 nhãn `DOCUMENT_UPDATED`,
>    `DOCUMENT_REINDEXED`, `DOCUMENT_ARCHIVED` mà GD1 ghi. Trước đó màn hiện mã thô và bộ lọc "Hành động"
>    không có ba mã này. Nhánh đã gộp `develop` (`4ae448d`), `mvn test` 283/283, đi lại đủ GD1 ngày 10/11.
> 6. Thấy khi chạy thật, **không thuộc GD1, chưa sửa**:
>    - **Thuê bao dùng thử hết hạn thì không gia hạn được** (UC006): `changePlan` chuyển `status` sang
>      `ACTIVE` nhưng không dời `period_end`, và không job nào chuyển `TRIALING` → `EXPIRED`. Tenant hết hạn
>      nhận 409 "Hãy gia hạn hoặc chọn gói" mà cả hai đường đều không cứu được. Tenant demo B hết hạn 01/11,
>      mình đã dời `period_end` tới 31/12 bằng SQL trên CSDL dev để kiểm tiếp.
>    - Gateway không có route `/ws` và java-core chưa có endpoint STOMP → WebSocket 404, thanh trên luôn
>      "Mất kết nối".
>    - `GET /api/v1/tool-calls` trả **500** (không có controller — route lạ rơi vào handler chung thành 500
>      thay vì 404). `audit-logs` thì đã ổn sau PR UC040 của bạn.
>    - `FormDialog`: `handleSubmit` `await onGui()` không bắt lỗi → mỗi lượt máy chủ từ chối (409/422) để
>      lại một unhandled rejection trên console. Giao diện vẫn hiện lỗi đúng, chỉ là tiếng ồn.
>    - ai-service chưa tự đăng ký Eureka (java-core dùng danh sách dự phòng).
>
> Còn mở cho GD3 (chưa đụng): mục 6, 7, 10 của kế hoạch — tạo/xác minh yêu cầu xoá, `/internal/**` bằng
> `X-Internal-Token`, phát `crm.conversation.closed`.

### 0.1 Tin gửi Dev B — GD2 (dán nguyên)

> GD2 (UC023 · UC025 · UC027 — chat có trích dẫn, từ chối, đánh giá) đã nối trọn widget/dashboard → gateway →
> java-core → ai-service, nhánh `feat/giao-dien-gd2-chat`. Đụng vài file của bạn, báo để bạn kéo về:
>
> 1. **`AiPerformanceService` (UC039)** — ô "Phản hồi tích cực" giờ lấy từ ai-service `GET /v1/ai/quality`
>    (khách + nhân viên, cộng tử với tử, mẫu với mẫu, bỏ nhãn máy `AUTO_EVAL`), không cộng
>    `metrics_daily.positive_feedback/negative_feedback` nữa. Lý do: `ai.turn.completed` phát ngay khi lượt chat
>    xong, trước khi có ai bấm 👍/👎, nên hai cột đó không có nguồn nào cộng — màn luôn báo 0. ai-service lỗi thì
>    riêng ô này trống, `errorMessage` có câu, các ô khác vẫn có số. Hai cột trong `metrics_daily` để trống, bạn
>    muốn bỏ thì bỏ ở V1xx. `AiPerformancePage.tsx`: thêm câu phụ khi có `errorMessage`.
> 2. **`dashboard-api.yaml`** — `LuotXuLyAi` thêm `userQuery`, `answerText`, `retrievalTopScore`, `degraded`,
>    `handoff`, `feedbacks[]`; `DanhGiaAi` thêm `correctedAnswer`, `ratedByUserId`; `GET /ai-interactions` thêm
>    `rating`; thân `POST …/feedback` thêm `correctedAnswer`; `knowledge-gaps` sắp theo `distinctContactCount`, bỏ
>    `q`; mô tả `HieuQuaAi.positiveFeedbackRate`/`errorMessage`. **Đã chạy `npm run gen:api`.**
> 3. **Widget (`WidgetDtos`, `WidgetService`, `WidgetController`, `WidgetRepository`, `AiChatClient`)** — tin BOT
>    ghi `ai_interaction_id` vào cột có sẵn, `metadata` thêm `refusalReason`, `degraded`; `MessageDto` thêm
>    `rateable`, `degraded`; endpoint mới `POST /api/v1/widget/messages/{messageId}/feedback` (token widget,
>    chỉ tin BOT của chính khách đó, `rater_type = CUSTOMER` do máy chủ đặt).
> 4. **`MessageThread.tsx` (Hộp thư)** — dưới tin BOT có 👍/👎 của nhân viên và danh sách đánh giá; một lời gọi
>    `GET /api/v1/ai-interactions?conversationId=…&size=100` cho cả hội thoại.
> 5. **`features/ai-agent/nhan.ts`** — `NHAN_LY_DO_DANH_GIA` chuyển sang `components/ai/DanhGiaDialog.tsx` (dùng chung
>    hai feature), `nhan.ts` xuất lại. **Test:** `FakeAiServer` thêm 4 đường giả (`/v1/ai-interactions`,
>    `/v1/knowledge-gaps`, `/v1/ai/quality`) và `interaction_id` trong câu trả lời mẫu.
> 6. **Migration V216** (Track B) — `ai.ai_interactions.latency_breakdown`. Nếu bạn đang giữ số V216 ở nhánh nào
>    thì báo mình đổi số.
> 7. Thấy khi chạy, **không thuộc GD2, chưa sửa**:
>    - **Khoá Resend lộ trong gói JS của dashboard** — `RegisterPage.tsx`, `ForgotPasswordPage.tsx` đọc
>      `import.meta.env.VITE_RESEND_API_KEY`, Vite nhúng giá trị vào `dist/assets/*.js` (đã thấy trong bản build).
>      Ai mở trang đăng ký cũng lấy được khoá. Nên chuyển gửi thư về java-core và **thu hồi khoá đang dùng**.
>    - Hai test `tests/unit/test_duong_dan_canh_bao_an_toan.py` (UC040/UC038) đỏ với FastAPI 0.141 — router được
>      gói thành `_IncludedRouter` nên `app.routes` không còn đường `/v1/...`; đường thật vẫn chạy. `fastapi>=0.121`
>      không ghim trần.
>    - `ruff` ai-service: 102 lỗi có sẵn (E501, I001), phần lớn ở `clustering/`, `safety_repository.py`.

---

## 1. ai-service — thay đổi GD1

### 1.1 `GET /v1/ai/kb/ingestion-jobs?state&page&size` — mới (UC019, SCR033)

Hàng đợi nạp của tenant theo `X-Tenant-Id` (RLS), **mới nhất trước**. Không có bảng `ingestion_jobs`:
mỗi tài liệu chưa `ARCHIVED` là một việc, chiếu qua cùng hàm với `GET /v1/ai/kb/ingestion-jobs/{id}`.

| Tham số | Kiểu | Ghi chú |
|---|---|---|
| `state` | `QUEUED` · `EXTRACTING` · `CHUNKING` · `EMBEDDING` · `INDEXING` · `DONE` · `FAILED` · `PAUSED` | Giá trị lạ ⇒ 422. `PAUSED` hợp lệ nhưng luôn rỗng (chưa có nguồn) |
| `page` | ≥ 0, mặc định 0 | |
| `size` | 1–100, mặc định 10 | |

Phản hồi `IngestionJobPage`: `{items: IngestionJobProgress[], total, page, size}`.

Bỏ `ARCHIVED` có chủ đích: bản cũ đã được bản bóng thay (hoặc đã gỡ) không còn việc nạp nào để theo dõi —
giữ lại thì mỗi lượt nạp lại hiện thành hai dòng "Hoàn tất" cùng tiêu đề.

### 1.2 `IngestionJobProgress.trigger` — `UPLOAD` | `REINDEX`

`REINDEX` khi dòng là bản bóng (`replaces_document_id` khác `null`, ADR-0031). `REPLACE` của
`CongViecNap` chưa có nguồn — tải lại cùng tiêu đề tạo version mới chứ không thay bản cũ.

### 1.3 `DocumentDeleted` thêm hai trường (cho ADR-0023 (f))

```yaml
DocumentDeleted:
  success: true
  message: string
  chunks_deleted: integer
  file_size_bytes: [integer, 'null']   # mới
  quota_released: boolean              # mới
```

`quota_released = true` khi lượt gỡ **này** vừa chuyển một tài liệu **được đếm hạn mức** sang `ARCHIVED`.
`false` khi: tài liệu đã gỡ từ trước (gỡ lại luỹ đẳng — không được trả hai lần) · đó là bản bóng nạp lại
đã `FAILED` (bản bóng chỉ thế chỗ bản cũ trong bộ đếm lúc nó `READY`; chưa `READY` thì chưa từng được
đếm). ai-service quyết định chứ không để java-core suy, vì chỉ ai-service biết trạng thái trước lượt gỡ.

Hệ quả cho bộ đếm (đã kiểm đầu-cuối trên CSDL dev): tải lên +1 · nạp lại 0 (bản bóng dùng chung tệp,
lúc đổi bản ai-service tự `ARCHIVED` bản cũ — tổng vẫn 1) · gỡ −1 và −`file_size_bytes`.

Test: `test_nap_tai_lieu.py` (2 ca hàng đợi + `REINDEX`), `test_kho_http.py`
(`test_go_bao_tra_han_muc_mot_lan_va_khong_tra_cho_ban_bong_hong`).

---

## 2. java-core — bề mặt cho dashboard

Mọi lời gọi đi qua lớp chuyển tiếp chung (`AiServiceClient.get/post/patch/delete` → gương DTO ở
`AiKnowledgeClient` → `KnowledgeMapper`). `X-Tenant-Id` lấy từ JWT, `X-Trace-Id` từ MDC; giá trị người
dùng gõ (từ khoá) đi qua **biến URI** nên `&`, `=` không chèn thêm được tham số.

| Dashboard gọi | java-core chuyển sang | Quyền | Ghi chú |
|---|---|---|---|
| `GET /api/v1/documents?q&status&sourceType&page&size` | `GET /v1/documents?keyword&…` | mọi nhân viên | `size` mặc định **10** (đặc tả UC020) |
| `GET /api/v1/documents/{id}` | `GET /v1/documents/{id}` + `GET /v1/ai/kb/ingestion-jobs/{reindex_document_id ?? id}` | mọi nhân viên | `latestJob` `null` nếu đọc tiến độ hỏng |
| `GET /api/v1/documents/{id}/chunks` | `GET /v1/documents/{id}/chunks` | mọi nhân viên | |
| `PATCH /api/v1/documents/{id}` `{title, description}` | `PATCH /v1/documents/{id}` | `TENANT_ADMIN` | kiểm toán `DOCUMENT_UPDATED` |
| `POST /api/v1/documents/{id}/reindex` → **202** | `POST /v1/documents/{id}/reindex` + đọc tiến độ bản bóng | `TENANT_ADMIN` | trả `CongViecNap` **của bản bóng** · kiểm toán `DOCUMENT_REINDEXED` |
| `DELETE /api/v1/documents/{id}` | `DELETE /v1/ai/kb/documents/{id}` (đường đặc tả ghi) | `TENANT_ADMIN` | trả hạn mức + kiểm toán `DOCUMENT_ARCHIVED`, **một** transaction |
| `GET /api/v1/ingestion-jobs?state&page&size` | `GET /v1/ai/kb/ingestion-jobs` | mọi nhân viên | |

Ánh xạ trường: kế hoạch mục UC019, UC020. Thêm một điểm: `TaiLieu.errorMessage` bỏ tiền tố mã
`"{MÃ}: "` mà ai-service lưu kèm — mã nằm ở `CongViecNap.errorCode`.

### 2.1 Bảng dịch lỗi (`AiServiceErrors`)

| ai-service | java-core trả |
|---|---|
| 404 | 404, giữ `code` — câu "Không tìm thấy tài liệu." (không lộ UUID) |
| 409 · 422 | giữ mã và `code`; `DOCUMENT_BUSY` · `DOCUMENT_ARCHIVED` có câu viết lại cho người đọc |
| 400 · 401 · 403 · khác | 500 `INTERNAL_ERROR` — hai dịch vụ lệch nhau, người dùng không sửa được gì |
| 5xx · hết giờ · mất nối | **502 `AI_SERVICE_UNAVAILABLE`** — "Thao tác chưa được thực hiện" |

Đường tải lên UC018 giữ bảng riêng (503 khi ai-service không phản hồi) — không đổi.

### 2.2 Kiểm toán — không ghi giá trị người dùng nhập

`after_data` của `DOCUMENT_UPDATED` chỉ có **tên trường** đã sửa và `version`, không có tiêu đề/mô tả mới:
tiêu đề có thể chứa tên khách ("Báo giá riêng anh A"), mà nhật ký kiểm toán sống lâu hơn dữ liệu khách
(NĐ 13, UC041). Lượt bị từ chối (403/409/422/502) không sinh dòng nào.

---

## 3. Lệch có chủ đích so với ADR-0023 (f)

| ADR ghi | Làm | Vì sao |
|---|---|---|
| Trả hạn mức "cùng transaction với dòng outbox `DocumentDeleted`" | Trả hạn mức + dòng kiểm toán cùng transaction, **không** phát `DocumentDeleted` | `crm.document.v1.json` chưa có payload (TODO) và không consumer nào đọc topic này; phát sự kiện không ai nhận là thêm một hợp đồng phải giữ mà không được gì. Đặc tả UC020 cũng không yêu cầu |
| "Mốc 80%/100% khi gỡ bớt: chốt ở UC020" | **Không xoá** `warned_at`/`blocked_at` | Mốc là thời điểm lần đầu chạm ngưỡng trong chu kỳ (UC006 hiển thị nó như một sự kiện); cổng chặn chỉ so `used_value` với trần nên gỡ bớt là tải lên được ngay |

Còn nợ: UC041 xoá tài liệu theo khách (`xoa_tai_lieu_theo_khach`) chưa trả hạn mức — làm ở GD3.

---

## 4. GD2 — lượt xử lý, đánh giá, khoảng trống (10/11/2026)

### 4.1 ai-service `GET /v1/ai-interactions` — mới (SCR036, UC023 b10 · UC025 b4 · UC027 b8)

| Tham số | Kiểu | Ghi chú |
|---|---|---|
| `route` | 7 nhánh của V204 | giá trị lạ ⇒ 422 `INVALID_REQUEST` |
| `refused` | bool | `true` = `NOT is_answered` |
| `rating` | `POSITIVE` · `NEGATIVE` | lượt có ít nhất một đánh giá của NGƯỜI mang giá trị đó (`AUTO_EVAL` không tính) |
| `conversation_id` | uuid | hộp thư lấy cả hội thoại một lần |
| `tu`, `den` | datetime | nửa khoảng `[tu, den)` — java-core quy ngày theo múi giờ doanh nghiệp, như `/v1/ai/quality` |
| `page`, `size` | ≥ 0 · 1–100, mặc định 20 | mới nhất trước |

Phản hồi `InteractionPage {items, total, page, size}`; `InteractionItem` là `LuotXuLyAi` ở snake_case, thêm
`user_query` (đã che PII), `answer_text`, `retrieval_top_score`, `status`, `llm_called`, `degraded`, `handoff`,
`citations[]` (nối `retrieved_chunk_ids` với đoạn + tài liệu, giữ thứ tự `[1]`, `[2]`…; đoạn đã xoá thì vắng) và
`feedback[]` (đánh giá của người, mới nhất trước, có `rater_user_id`, `corrected_answer`, `rated_at`). Ba truy vấn
cho một trang, không N+1. Tenant do RLS. Test: `test_luot_va_danh_gia.py` (3 ca mới).

**`discarded_answer`** chỉ có ở lượt bị HUỶ sau hậu kiểm (`LOW_CONFIDENCE` + `llm_called` + có điểm bám nguồn):
đường RAG nay lưu câu ĐÃ SINH vào `response_text` của lượt đó (câu mẫu từ chối suy lại được từ lý do). Công thức
cũ `is_answered = false ? response_text : null` hiện câu mẫu mà khách ĐÃ nhận thành "câu bị huỷ".

**V216** `ai.ai_interactions.latency_breakdown jsonb NOT NULL DEFAULT '{}'` — khoá `<chặng>_ms` như
`TurnRecord`, bỏ `total_ms`. Lượt trước V216 là `{}`.

### 4.2 java-core — bề mặt cho dashboard và widget

| Gọi | java-core chuyển sang | Quyền | Ghi chú |
|---|---|---|---|
| `GET /api/v1/ai-interactions?route&refused&rating&conversationId&from&to&page&size` | `GET /v1/ai-interactions` | mọi nhân viên | `from`/`to` là NGÀY → `[from 00:00, to+1 00:00)` giờ doanh nghiệp; gộp chặng `retrieve` (= embed + retrieve) · `rerank` · `generate` · `tool` · `guard` (= guard + postguard) · `classify`; `ratedByName` tra `platform.users`; `feedback` = phần tử đầu của `feedbacks` |
| `POST /api/v1/ai-interactions/{id}/feedback` → **201** | `POST /v1/ai-interactions/{id}/feedback` | mọi nhân viên | `rater_type = AGENT`, `rater_user_id` từ JWT; chê thiếu lý do → 422 `REASON_REQUIRED` ngay ở java-core; khen thì bỏ lý do |
| `GET /api/v1/knowledge-gaps?gapType&page&size` | `GET /v1/knowledge-gaps` | mọi nhân viên | `questionText ← query_text` · `occurrenceCount ← unanswered_count` · `distinctContactCount ← distinct_conversation_count` · `priority` 1 (≥ 5 khách) / 2 (≥ 2) / 3 · `firstSeenAt` · `lastSeenAt` |
| `GET /api/v1/analytics/ai-performance` (UC039) | thêm `GET /v1/ai/quality?tu&den` | quản trị | chỉ ô "Phản hồi tích cực" — chốt Q2 hướng B |
| `POST /api/v1/widget/messages/{messageId}/feedback` (token widget) | `POST /v1/ai-interactions/{id}/feedback` | khách giữ token | tin phải là BOT của hội thoại của CHÍNH khách đó và có `ai_interaction_id`, nếu không 404; `rater_type = CUSTOMER`, không có câu sửa |

Bảng dịch lỗi (`AiServiceErrors`) thêm câu cho `INTERACTION_NOT_FOUND` và `REASON_REQUIRED`. Test:
`AiInteractionRelayIntegrationTest` (7), `WidgetIntegrationTest` (+4), `AiPerformanceIntegrationTest` (+2).
