# Kế hoạch tích hợp giao diện — GD1–GD4 · 8 UC của Dev A

> **Mục tiêu đợt:** mỗi UC chạy trọn luồng **web-dashboard / web-widget → gateway → java-core →
> ai-service** trên dữ liệu thật, đúng **đặc tả** (`docs/Dac-ta-UseCase-Module-AI.docx`), không chỉ
> "gọi được API".
>
> **Lập 22/10/2026** từ khảo sát code ở `e5cb8ff` (develop, đã gồm PR #40 N17).
> **Thứ tự ưu tiên khi lệch:** đặc tả UC > `docs/openapi/dashboard-api.yaml` > nháp `docs/contracts/` >
> code hiện có. Chỗ nào hợp đồng lệch đặc tả thì theo đặc tả và báo Dev B (mục 1).

| GD | UC | Kết quả bấm được cuối ngày |
|---|---|---|
| **GD1** | UC018 · UC019 · UC020 | tải lên → tiến độ tới `DONE` → danh sách → xem đoạn → sửa → nạp lại → gỡ |
| **GD2** | UC023 · UC025 · UC027 | hỏi ở widget → có trích dẫn · hỏi ngoài kho → từ chối, chuyển nhân viên · 👍/👎 → hiện ở dashboard · khoảng trống tri thức |
| **GD3** | UC026 · UC041 | đóng hội thoại → tóm tắt 4 phần ở cột phải · tạo → xác minh → xem trước → thực thi xoá → câu trả lời sau không còn dữ liệu khách |
| **GD4** | cả 8 | diễn tập một lèo, sửa chỗ vỡ, minh chứng cuối, ôn tập, cập nhật artifact bản đồ luồng |

---

## 0. Luật của đợt

1. **Một UC chỉ được tick khi đủ 4 điều:**
   - (a) mọi bước **luồng chính** của đặc tả bấm được trên giao diện thật (`VITE_USE_MOCK=false`);
   - (b) các luồng phụ và mã lỗi ghi trong mục "DoD" đã thử trên giao diện, thấy đúng thông báo;
   - (c) `mvn compile` + `npm run typecheck` (+ `ruff`, `compileall`, `pytest` nếu đụng ai-service) sạch;
   - (d) có dòng minh chứng trong `docs/report/tich-hop-giao-dien-2026-10.md`.
2. **Chắc từng UC, không dàn mỏng.** Hết phiên mà UC còn ô mở thì phiên sau làm tiếp UC đó trước, **không mở
   GD mới khi GD cũ còn nợ**. Trễ lịch được chấp nhận (hạn thật 31/12); báo rõ ô nào đang chặn.
3. **Phân chỗ làm:** java-core, gateway, web-dashboard, web-widget làm ở **phiên chính** (agent bị chặn cứng
   ở đó). ai-service là Track B.
4. **Hướng tích hợp đã chốt:** dashboard chỉ gọi `/api/v1/**`. java-core là mặt tiền, chuyển tiếp sang
   ai-service bằng `AiServiceClient`. java-core **không** đọc schema `ai`/`knowledge` (ADR-0002).
   `X-Tenant-Id` luôn lấy từ JWT (`SecurityUtils.getCurrentTenantId()`), không bao giờ từ body/query/path.
5. **File dùng chung với Dev B phải nhắn trước khi sửa:** `SecurityConfig` hai phía, `application*.yml`,
   `docs/openapi/*.yaml` + `api-schema.d.ts` (một người sinh lại), `docker-compose.yml`, `WidgetDtos.java`.
6. **Git:** AI soạn lệnh, người dùng tự chạy (kể cả `git push`). Mỗi GD một nhánh tách từ `develop`
   (`feat/giao-dien-gd1-kho`, `…-gd2-chat`, `…-gd3-tom-tat-xoa`, `…-gd4-dien-tap`). Trước PR:
   `git pull origin develop`, gỡ conflict, kiểm lại; PR tạo trên web GitHub.
7. **Cuối mỗi phiên:** tắt mọi server, worker, container và lệnh nền đã bật (không xoá volume).
8. **Minh chứng gọn:** một tệp `docs/report/tich-hop-giao-dien-2026-10.md`, mỗi GD thêm một mục, dạng bảng
   "thao tác → kết quả thấy được". Ôn tập viết **một bản** ở GD4.

---

## 1. Trước GD1 — một tin nhắn gộp gửi Dev B

Gửi một lần cho cả đợt, để không bị chặn giữa ngày. Nháp hợp đồng mới đặt ở `docs/contracts/giao-dien-gd.md`.

| # | Đổi gì | Ở đâu | Dùng ở |
|---|---|---|---|
| 1 | Thêm `PATCH /api/v1/documents/{id}` `{title, description}` — đặc tả UC020 bước 5 có "sửa siêu dữ liệu", hợp đồng thiếu | `dashboard-api.yaml` | GD1 |
| 2 | `POST /api/v1/documents/{id}/reindex` trả `CongViecNap` của **bản bóng** (id mới, ADR-0031) | `dashboard-api.yaml` (mô tả) | GD1 |
| 3 | `GET /api/v1/knowledge-gaps` sắp theo `distinctContactCount` (đặc tả UC025 8.1), không theo `occurrenceCount` | `dashboard-api.yaml` | GD2 |
| 4 | Thân `POST /api/v1/ai-interactions/{id}/feedback` thêm `correctedAnswer` (đặc tả UC027 bước 4) | `dashboard-api.yaml` | GD2 |
| 5 | Widget: `MessageDto` thêm `rateable`; endpoint mới `POST /api/v1/widget/messages/{messageId}/feedback` | `WidgetDtos.java` | GD2 |
| 6 | Thêm `POST /api/v1/erasure-requests` (tạo, `legalBasis` bắt buộc) và `POST /api/v1/erasure-requests/{id}/verify-identity` — đặc tả UC041 bước 1–4; thiếu thì ràng buộc `ck_erasure_gate` chặn mọi lần thực thi | `dashboard-api.yaml` | GD3 |
| 7 | `execute` nhận cả `PARTIALLY_FAILED` (chạy lại phần dở, đặc tả UC041 8.1) | `dashboard-api.yaml` | GD3 |
| 8 | Chuỗi bảo mật `/internal/**` bằng `X-Internal-Token` + quyền `TENANT_ADMIN` cho thao tác ghi tài liệu và xoá dữ liệu | `SecurityConfig` | GD1, GD3 |
| 9 | ai-service ↔ java-core: 4 nháp cũ (UC020, UC023, UC025/027, UC026/041) + 2 endpoint liệt kê mới (mục GD1, GD2) | `ai-service-to-java-core.yaml` | cả đợt |
| 10 | Phát `crm.conversation.closed` từ `InboxService.changeStatus` | `docs/events/` (lược đồ đã có) | GD3 |
| 11 | Ai sinh lại `api-schema.d.ts` sau khi vá `dashboard-api.yaml` | — | GD1 |

Nợ cũ gửi kèm (không chặn đợt): log bí mật trong `AuthService` (N17 §3), `CLASSIFY_URL` trong compose.

---

## 2. Lệch giữa code và đặc tả — tìm thấy khi khảo sát 22/10

Đây là lý do kế hoạch dày hơn bản liệt kê cũ. Mỗi dòng có ô việc tương ứng ở GD của nó.

| UC | Chỗ lệch | Tầng |
|---|---|---|
| 019 | ai-service chỉ có `GET /v1/ai/kb/ingestion-jobs/{id}`, **không có danh sách** — màn SCR033 cần danh sách | ai-service |
| 019 | `IngestionJobProgress.trigger` luôn là `UPLOAD`, kể cả bản bóng nạp lại | ai-service |
| 020 | FE có bộ lọc trạng thái nhưng **không gửi `status`** lên máy chủ (`api/knowledge.ts` → `danhSachTaiLieu`) | dashboard |
| 020 | Không có giao diện sửa siêu dữ liệu; hợp đồng dashboard cũng thiếu `PATCH` | dashboard + hợp đồng |
| 020 | Nạp lại xong điều hướng theo **id cũ**, nhưng ai-service tạo bản bóng **id mới** | dashboard |
| 023/027 | `AiChatClient` bỏ qua `interaction_id`, nên tin BOT không có `ai_interaction_id` (cột đã có) và không đánh giá được | java-core |
| 027 | Nút "Chưa ổn" ở `AiInteractionsPage` **gán cứng `WRONG_INFO`**; đặc tả bắt chọn 1/4 lý do + nhận xét + câu sửa | dashboard |
| 027 | Widget chưa có 👍/👎; hộp thư (`MessageThread`) chưa có nút đánh giá cho nhân viên | widget + dashboard |
| 027 | ai-service **không có endpoint liệt kê lượt** — SCR036 và cột ngữ cảnh cần | ai-service |
| 026 | `InboxService.context()` trả `summary = null`, `lastAiInteraction = null`; `ContextPanel` **không có khối tóm tắt** | java-core + dashboard |
| 026 | ai-service gọi `/internal/*` chỉ kèm `X-Tenant-Id`, chưa có `X-Internal-Token` | ai-service |
| 041 | FE và hợp đồng **không có bước tạo yêu cầu và xác minh danh tính** — DB chặn thực thi khi chưa xác minh | cả bốn tầng |

Đã đúng sẵn, chỉ cần kiểm trên giao diện: hộp thoại tải lên (đuôi, 20 MB, gợi ý tiêu đề, ngôn ngữ), java-core
UC018 (413/415/422/409, hạn mức, outbox), widget hiện "Nguồn: …", `MessageThread` hiện nguồn, gateway gắn
`X-Tenant-Id` từ JWT, V135 đã sửa khoá ngoại `contact_notes`.

---

## 3. Lớp chuyển tiếp chung trong java-core (dựng ở GD1, dùng cả đợt)

Mấu chốt để vừa 4 ngày: mọi đường AI đi qua **một** lớp, không viết riêng từng UC.

- [x] `AiServiceClient` thêm `get/post/patch/delete` chung trên `RestClient` hiện có. Mọi lời gọi gắn
      `X-Tenant-Id` (từ JWT) và `X-Trace-Id`.
- [x] Đọc phản hồi bằng `ObjectMapper` kiểu `SNAKE_CASE`. Mỗi kiểu một **record Java đặt tên đúng theo
      `dashboard-api.yaml`**, trả trong `ApiResponse` (camelCase).
- [x] Ánh xạ lỗi, giữ nguyên `code` của ai-service:

  | ai-service | java-core trả |
  |---|---|
  | 404 | 404 (`DOCUMENT_NOT_FOUND`, `INTERACTION_NOT_FOUND`) |
  | 409 · 422 | giữ mã và `code` (`DOCUMENT_BUSY`, `INVALID_METADATA`, `REASON_REQUIRED` …) |
  | 401 · 403 | 500 — đây là lỗi cấu hình phía mình, không phải lỗi người dùng |
  | 5xx · hết giờ · không nối được | **502 `AI_SERVICE_UNAVAILABLE`** (đặc tả UC020). Đường UC018 cũ đang trả 503 — ghi lại, không sửa |

- [x] `Page`: `items, page, size`; `totalItems ← total`; `totalPages = ceil(total / size)`.
- [x] 1 test `MockRestServiceServer`: snake → camel, và 404/409/5xx → đúng mã.
- [x] Trường nào hai bên không khớp thì ghi vào minh chứng, **không** tự sửa hợp đồng.

---

## GD1 — Dựng stack + kho tri thức: UC018 · UC019 · UC020

**Điều kiện vào:** đã gửi tin mục 1. Nhánh `feat/giao-dien-gd1-kho` tách từ `develop`.

> **✅ Đóng 24/10/2026** — minh chứng: [`docs/report/tich-hop-giao-dien-2026-10.md`](../report/tich-hop-giao-dien-2026-10.md) mục GD1.
> Làm thêm ngoài danh sách: trả hạn mức khi gỡ (ADR-0023 (f)), trạng thái lỗi tải cho `ListPage`, vá
> `dashboard-api.yaml` + sinh lại kiểu. UC020 bước 8 chỉ kiểm được phần **ghi** kiểm toán (bằng CSDL) — màn
> xem thuộc UC040 của Dev B, chưa có backend. Ảnh chụp: người dùng tự chụp.

### Dựng stack (đầu phiên)

- [x] `docker compose up -d postgres redis kafka rustfs-init` → cả 4 healthy; `bash scripts/create-topics.sh` đủ 14 topic
- [x] `docker compose -f inference/compose.inference.yml up -d ai-embed ai-rerank ai-classify`
- [x] `eureka-server` (:8761) → `java-core` profile `local`, **có** Eureka (:8081) → `gateway` profile `local` (:8080)
- [x] ai-service `RUN_MODE=api` (:8000) + worker `RUN_MODE=worker`; GD1 dùng `LLM_MODE=mock` là đủ
- [x] `web-dashboard`: `npm run dev` (:5173), `.env` có `VITE_USE_MOCK=false`, `VITE_GATEWAY_URL=http://localhost:8080`
- [x] Đăng nhập `quantri@nha-khoa-b17.test` / `NhaKhoaB17@2026` (tenant B). Ghi mọi chỗ vỡ: CORS, JWT/JWKS, WS `/ws`, hình dạng `ApiResponse`

### UC018 — Tải lên tài liệu tri thức

Đường đã có sẵn ở cả bốn tầng; GD1 chỉ **kiểm trên giao diện**.

| Bước đặc tả | Thao tác | Phải thấy |
|---|---|---|
| 1–5 | Kho tri thức → "Tải lên tài liệu", kéo tệp PDF | tiêu đề tự gợi ý từ tên tệp, chọn được ngôn ngữ |
| 6–10 | Bấm "Tải lên" | 202, chuyển sang màn tiến độ của tài liệu đó |
| 7.1 | Tải lại cùng tiêu đề | `version` tăng thành v2, bản cũ còn |
| 4.1 | Chọn `.xlsx` | báo danh sách định dạng nhận, hộp thoại giữ nguyên |
| 4.2 | Chọn tệp > 20 MB | báo vượt 20 MB ngay ở trình duyệt |
| 8.1 | PDF ảnh quét (không có chữ) | tài liệu `FAILED` kèm `errorMessage` đọc được |
| 6.1 | (nếu tạo được) tenant chạm `max_documents` | 409 `DOCUMENT_QUOTA_EXCEEDED`, thông báo gỡ bớt hoặc nâng gói |

- [x] Kiểm 403 khi tài khoản không phải `TENANT_ADMIN` tải lên

### UC019 — Nạp và lập chỉ mục

| Việc | Tầng |
|---|---|
| [x] `GET /v1/ai/kb/ingestion-jobs?state&page&size` — danh sách, mới nhất trước, RLS theo `X-Tenant-Id` | ai-service |
| [x] `trigger = REINDEX` khi dòng có `replaces_document_id` | ai-service |
| [x] pytest cho hai việc trên + `ruff` + `compileall`; ghi vào nháp `docs/contracts/giao-dien-gd.md` | ai-service |
| [x] `GET /api/v1/ingestion-jobs` → danh sách trên, trả `Page<CongViecNap>` | java-core |
| [x] `GET /api/v1/documents/{id}` điền `latestJob` ← `GET /v1/ai/kb/ingestion-jobs/{reindex_document_id ?? id}` | java-core |

Ánh xạ `CongViecNap ← IngestionJobProgress`: `id ← job_id` · `documentId` · `documentTitle` · `trigger` ·
`state` · `attempt` · `chunksCreated ← chunks_created` · `errorCode` · `errorMessage` · `durationMs` ·
`startedAt` · `finishedAt` · `createdAt`. `tokensUsed`/`costVnd` chưa có nguồn nên bỏ trống (không bắt buộc).

| Bước đặc tả | Thao tác | Phải thấy |
|---|---|---|
| 1–11 | Ở lại màn tiến độ sau khi tải | chặng chạy `QUEUED → … → DONE`, tự ngừng hỏi lại khi xong |
| 12 | Đọc dòng hoàn tất | "đã có N đoạn trong chỉ mục", N khớp `chunkCount` ở danh sách |
| — | Mở `/tri-thuc/tien-do` | hàng đợi chung hiện việc đang chạy |
| 4.1 | Tệp ảnh quét ở UC018 | màn tiến độ `FAILED` + câu lỗi |

### UC020 — Quản lý kho tri thức

| Việc | Tầng |
|---|---|
| [x] `GET /api/v1/documents` → `/v1/documents` (`q → keyword`, `status`, `sourceType`, `size = 10` tường minh) | java-core |
| [x] `GET /api/v1/documents/{id}` → `TaiLieuChiTiet` | java-core |
| [x] `GET /api/v1/documents/{id}/chunks` → `Page<DoanTaiLieu>` | java-core |
| [x] `PATCH /api/v1/documents/{id}` → `PATCH /v1/documents/{id}` + ghi `platform.audit_logs` (`DOCUMENT_UPDATED`) | java-core |
| [x] `POST /api/v1/documents/{id}/reindex` → 202 + `CongViecNap` của bản bóng + audit (`DOCUMENT_REINDEXED`) | java-core |
| [x] `DELETE /api/v1/documents/{id}` → 200; 409 `DOCUMENT_BUSY`; 502 thì không ghi gì + audit (`DOCUMENT_ARCHIVED`) | java-core |
| [x] `uploadedByName`: tra `platform.users` theo `uploaded_by` (bảng của Track A, java-core đọc được) | java-core |
| [x] Quyền: `GET` mọi nhân viên của tenant; `PATCH`/`reindex`/`DELETE` chỉ `TENANT_ADMIN` → 403 | java-core (`SecurityConfig`) |
| [x] `danhSachTaiLieu` gửi thêm `status: bo.trangThai` | dashboard |
| [x] Hộp thoại sửa tiêu đề + mô tả (3–255 / ≤ 500 ký tự) ở màn chi tiết; mutation `suaTaiLieu` | dashboard |
| [x] Nạp lại xong điều hướng theo `kq.documentId` (bản bóng), không theo id cũ | dashboard |

Ánh xạ `TaiLieu ← DocumentDetail`: `sourceType ← source_type` · `fileName ← file_name` · `mimeType` ·
`sizeBytes ← file_size_bytes` · `chunkCount` · `version` · `errorMessage` · `indexedAt` · `createdAt`.
`TaiLieuChiTiet` thêm `replacesDocumentId`, `latestJob`, `checksum = null`.
`DoanTaiLieu ← ChunkItem`: `id ← chunk_id` · `ordinal ← chunk_index` · `sectionPath ← heading` · `tokenCount` ·
`embeddingModel` · `embeddingVersion`.

| Bước đặc tả | Thao tác | Phải thấy |
|---|---|---|
| 2 | Mở Kho tri thức, gõ `bao gia`, lọc trạng thái, lọc định dạng | khớp `báo giá`; lọc thật sự đổi kết quả; 10 dòng/trang, mới nhất trước |
| 2.1 | Tenant chưa có tài liệu | màn trống mời tải tài liệu đầu tiên |
| 4 | Bấm một tài liệu | chi tiết + bảng đoạn có mục, số token, mô hình nhúng **từng đoạn** |
| 5 (sửa) | Đổi tiêu đề | danh sách hiện tiêu đề mới; `chunkCount` không đổi |
| — | Đổi tiêu đề trùng tài liệu khác cùng version | 422 `INVALID_METADATA` |
| 6 | Nạp lại | sang màn tiến độ của bản bóng; trong lúc nạp, bản cũ vẫn `READY` |
| 5.1 | Nạp lại / xoá khi đang `PROCESSING` | 409 "đang xử lý" |
| 7 | Xoá khỏi kho | biến khỏi danh sách (ẩn `ARCHIVED`), lọc `ARCHIVED` thì thấy lại |
| 7.2 | Tắt ai-service rồi xoá | 502, tài liệu **vẫn** ở trạng thái cũ |
| 8 | Mở Nhật ký kiểm toán | đủ 3 dòng sửa · nạp lại · gỡ, có người làm và thời điểm |
| 403 | Đăng nhập nhân viên thường, bấm xoá | 403 |

### Cổng ra GD1

- [x] UC018, UC019, UC020 đủ 4 điều ở mục 0
- [x] `mvn -f java-core/pom.xml compile` + test lớp chuyển tiếp · `npm run typecheck` · ai-service `ruff` + `compileall` + `pytest` phần mới
- [x] Mục GD1 trong `docs/report/tich-hop-giao-dien-2026-10.md`
- [x] Tắt hết tiến trình; soạn lệnh commit/push cho người dùng

**Phải giải thích được:** vì sao dashboard không gọi thẳng ai-service · vì sao tài liệu của tenant khác trả 404
chứ không phải 403 · vì sao nạp lại đổi `id` mà kho không trống giây nào.

---

## GD2 — Chat trọn luồng + từ chối + đánh giá: UC023 · UC025 · UC027

**Điều kiện vào:** GD1 đóng. ai-service `LLM_MODE=remote` (Gemini, làm mới hạn mức 14:00). Cần nhanh thì
`RERANK_ENABLED=false`.

**Chốt bộ câu hỏi TRƯỚC khi chạy:** router hỏi lại phần lớn câu nha khoa, chỉ kiểu "… bao nhiêu tiền / chi
phí / bảng giá" qua được. Ghi sẵn vào báo cáo 6 câu: 2 câu có đáp án trong kho · 1 câu có "chi phí" nhưng
ngoài kho (`NOT_COVERED`) · 1 câu về đơn hàng/lịch hẹn cụ thể (`OUT_OF_SCOPE_DATA`) · 1 câu chào (đường nhanh)
· 1 câu ngoài kho hỏi lặp 2 lần (luồng phụ 3.3).

### Widget (đầu phiên)

- [ ] Tạo kênh widget + khoá widget cho tenant B ở trang cài đặt (SCR018), thêm `localhost:5174` vào tên miền được phép
- [ ] `cd web-widget && npm run dev` (:5174, trang `demo/`). Tránh cổng 3000 (Grafana)

### UC023 — Trả lời dựa trên tri thức doanh nghiệp

| Việc | Tầng |
|---|---|
| [ ] `AiChatClient` đọc thêm `interaction_id`, `refusal_reason`, `degraded` | java-core |
| [ ] `WidgetService` ghi `interaction_id` vào **cột** `messages.ai_interaction_id` (đã có), `refusalReason`/`degraded` vào `metadata` | java-core |
| [ ] Widget: khối nguồn hiện tiêu đề **và** đoạn trích (`snippet`) khi bấm; tin `degraded` có nhãn "trả lời tạm" | widget |

| Bước đặc tả | Thao tác | Phải thấy |
|---|---|---|
| 1–12 | Hỏi câu có đáp án ở widget | câu trả lời có `[1]`… và "Nguồn: <tiêu đề>"; bấm thấy đoạn trích |
| CRM | Mở hội thoại đó ở Hộp thư | tin BOT có nguồn giống widget |
| 10 | Mở Giám sát lượt xử lý | lượt `RAG`: điểm bám nguồn, trích dẫn, độ trễ từng chặng, token |
| KPI | Câu chào | lượt `SMALL_TALK`, chi phí 0, không gọi LLM |
| 8.2 | Tắt mạng LLM hoặc dùng khoá sai | widget vẫn có câu trả lời (trích nguyên văn đoạn), nhãn "trả lời tạm" |

### UC025 — Từ chối khi không đủ căn cứ

| Việc | Tầng |
|---|---|
| [ ] `GET /api/v1/knowledge-gaps` → `/v1/knowledge-gaps` (`gapType → gap_type`) | java-core |
| [ ] `KhoangTrongTriThuc`: `questionText ← query_text` · `occurrenceCount ← unanswered_count` · `distinctContactCount ← distinct_conversation_count` · `priority` = bậc do java-core tính · `firstSeenAt` · `lastSeenAt` | java-core |
| [ ] `KnowledgeGapsPage` ghi chú "số khách xấp xỉ theo số hội thoại"; bỏ tham số `q` (máy chủ không hỗ trợ) | dashboard |

| Bước đặc tả | Thao tác | Phải thấy |
|---|---|---|
| 1–6 | Hỏi câu "chi phí" ngoài kho | câu từ chối rõ ràng, **không** bịa, không có nguồn |
| 5 / 3.1 | Hỏi về đơn hàng/lịch hẹn cụ thể | từ chối + chuyển nhân viên; hội thoại hiện ở Hộp thư trạng thái chờ nhân viên |
| 3.3 | Hỏi ngoài kho lần 2 trong cùng hội thoại | đề xuất chuyển nhân viên |
| 4 | Giám sát lượt xử lý, lọc "đã từ chối" | thấy lý do từ chối và điểm truy hồi cao nhất |
| 8 · 8.1 | Mở Khoảng trống tri thức | câu vừa hỏi có mặt, xếp theo số khách khác nhau |
| — | Tải tài liệu bổ sung rồi hỏi lại | trả lời được; khoảng trống tụt dần (cửa sổ 30 ngày) |

`LOW_CONFIDENCE` khó gây ra có chủ đích: ghi "chưa tái hiện trên giao diện" nếu không gặp, không ép.

### UC027 — Đánh giá chất lượng câu trả lời

| Việc | Tầng |
|---|---|
| [ ] `GET /v1/ai-interactions?route&refused&conversation_id&from&to&page&size` — **mới**, hình dạng như `LuotXuLyAi` ở snake_case; `citations` nối `retrieved_chunk_ids` với `knowledge_chunks`/`knowledge_documents`; `discarded_answer` theo định nghĩa trong `dashboard-api.yaml`; kèm đánh giá mới nhất | ai-service |
| [ ] Kiểm `response_text` lưu gì khi từ chối, để `discardedAnswer` không hiện nhầm câu mẫu từ chối | ai-service |
| [ ] pytest (lọc, phân trang, RLS) + ghi vào nháp hợp đồng | ai-service |
| [ ] `GET /api/v1/ai-interactions` → `Page<LuotXuLyAi>` | java-core |
| [ ] `POST /api/v1/ai-interactions/{id}/feedback` → ai-service: `rating` POSITIVE/NEGATIVE → 1/−1, `rater_type = AGENT`, `rater_user_id` từ JWT, `corrected_answer`; trả 201 `DanhGiaAi` | java-core |
| [ ] `POST /api/v1/widget/messages/{messageId}/feedback` (token widget): kiểm tin thuộc hội thoại của khách đó, là tin BOT, có `ai_interaction_id` → ai-service với `rater_type = CUSTOMER`; `MessageDto.rateable` | java-core |
| [ ] Widget: 👍/👎 dưới tin BOT có `rateable`; 👎 mở 4 lý do + ô nhận xét; gửi xong "Cảm ơn bạn" | widget |
| [ ] Một `DanhGiaDialog` dùng chung: 👎 bắt chọn 1/4 lý do; nhận xét; **câu trả lời đúng** (chỉ nhân viên) | dashboard |
| [ ] Gắn dialog vào `AiInteractionsPage` (bỏ `WRONG_INFO` gán cứng) và `MessageThread` (tin BOT có `aiInteractionId`) | dashboard |
| [ ] Tỉ lệ tích cực hiện trên giao diện — xem **Điểm chốt Q2** | java-core + dashboard |

| Bước đặc tả | Thao tác | Phải thấy |
|---|---|---|
| 1–5 (khách) | 👍 ở widget | Giám sát lượt xử lý: lượt đó có đánh giá tích cực của khách |
| 3 · 3.1 | 👎 ở widget | bắt chọn lý do; 👍 thì không hỏi lý do |
| 4 (nhân viên) | Ở Hộp thư, 👎 + lý do + câu sửa | lưu được, hiện kèm tên nhân viên |
| 2.1 | Đánh giá lại cùng lượt, cùng phía | cập nhật dòng cũ, không sinh dòng thứ hai |
| 422 | Gửi 👎 thiếu lý do (gọi thẳng API) | 422 `REASON_REQUIRED` |
| 7 | Mở màn hiệu quả (theo Q2) | tỉ lệ tích cực = số 👍 / số lượt **có** đánh giá |
| 8 | Lọc lượt bị chê | thấy lý do và câu sửa |

### Cổng ra GD2

- [ ] UC023, UC025, UC027 đủ 4 điều ở mục 0; 6 câu chốt sẵn đều có dòng minh chứng
- [ ] `mvn compile` · `npm run typecheck` (dashboard + widget) · ai-service `ruff` + `compileall` + `pytest`
- [ ] Ghi số lượt Gemini đã dùng; tắt hết tiến trình

**Phải giải thích được:** `groundedness` khác `retrieval_top_score` ở đâu · vì sao khoảng trống tri thức không có
nút "đã xử lý" · vì sao tỉ lệ tích cực chia cho số lượt **có** đánh giá.

---

## GD3 — Tóm tắt + xoá dữ liệu cá nhân: UC026 · UC041

**Điều kiện vào:** GD2 đóng. Đặt `INTERNAL_API_TOKEN` giống nhau ở ai-service và java-core. ai-service + worker
chạy `JAVA_CORE_MODE=remote`, `LLM_MODE=remote`.

### Bề mặt `/internal/**` (dùng chung cho cả hai UC)

- [ ] java-core: chuỗi bảo mật riêng cho `/internal/**`: không cần JWT, **bắt buộc** `X-Internal-Token` khớp; đặt
      phạm vi tenant từ `X-Tenant-Id` bằng `TenantTransactionScope` (đường này chỉ ai-service gọi, gateway không định tuyến tới)
- [ ] ai-service: `HttpJavaCoreClient` gửi thêm `X-Internal-Token` — xem **Điểm chốt Q3**

### UC026 — Tóm tắt nội dung hội thoại

| Việc | Tầng |
|---|---|
| [ ] `changeStatus` → `CLOSED`/`RESOLVED`: ghi outbox `crm.conversation.closed` **cùng transaction**; payload `conversation_id, closed_by, close_reason, closed_at, message_count`, khoá `tenant_id` | java-core |
| [ ] `GET /internal/conversations/{id}/messages?page&size` — cũ trước, có `isRedacted`; không có/khác tenant → 404 | java-core |
| [ ] `PATCH /internal/conversations/{id}/summary` → `summary_data` (4 khoá), `summary_trigger`, `summary_model_version`, `summarized_at`, `summary`; luỹ đẳng | java-core |
| [ ] `context()` trả `summary` (đọc 5 cột trên, `isStale` = có tin mới sau `summarized_at`) và `lastAiInteraction` (lượt mới nhất qua `GET /v1/ai-interactions?conversation_id=…&size=1` của GD2) | java-core |
| [ ] `ContextPanel`: khối "Tóm tắt" 4 phần + `trigger` + `modelVersion` + thời điểm + chỉ báo `isStale` | dashboard |
| [ ] Nút "Tóm tắt lại" (`MANUAL`) — chỉ làm nếu chốt ở **Q1** | java-core + dashboard |

| Bước đặc tả | Thao tác | Phải thấy |
|---|---|---|
| 1–6 | Hộp thư → đóng một hội thoại có ≥ vài lượt | worker nhận sự kiện (log), vài giây sau mở lại hội thoại |
| 7 | Xem cột phải | 4 phần: nhu cầu chính · thông tin khách đã cung cấp · vấn đề chưa giải quyết · bước tiếp theo, kèm phiên bản model |
| 1.1 | Đóng hội thoại chỉ có câu chào | không sinh tóm tắt, không gọi LLM |
| 1.2 | (đã chứng minh N12) | — chỉ dẫn lại số đo |
| 4.1 | Mở lại → đóng lần nữa | bản mới đè bản cũ |

### UC041 — Xử lý yêu cầu xoá dữ liệu cá nhân

| Việc | Tầng |
|---|---|
| [ ] Gói `platform/erasure/`: `GET /api/v1/erasure-requests` (lọc `status`) · `GET /{id}` · `POST` (tạo `PENDING`, `legalBasis` bắt buộc, `requestedBy` CONTACT/STAFF, **chặn yêu cầu thứ hai** khi khách đã có yêu cầu đang mở — 2.1) | java-core |
| [ ] `POST /{id}/verify-identity` → `identity_verified_by` + `identity_verified_at` cùng lúc | java-core |
| [ ] `GET /preview?contactId=` → `MucXoa[]`: phía CRM đếm thật (`engagement.contacts` ANONYMIZE · `engagement.messages` che nội dung · `sales.lead_scores` DELETE); phía AI `affectedRows = null` ("biết sau khi thực thi") | java-core |
| [ ] `POST /{id}/execute` **đồng bộ**, nhận `PENDING` hoặc `PARTIALLY_FAILED`; chưa xác minh → 409 `IDENTITY_NOT_VERIFIED` | java-core |
| [ ] Thứ tự thực thi: `IN_PROGRESS` → lấy mọi `conversationId` của khách → `DELETE /v1/ai/privacy/contacts/{id}?conversationId=…` kèm `X-Internal-Token`, **ngoài** transaction (ai-service gọi ngược `DELETE /internal/contacts/{id}/lead-scores`) → ẩn danh danh bạ (`ANONYMIZED` + `anonymized_at`) → che tin nhắn (`is_redacted`) → gộp `items` → `COMPLETED`/`PARTIALLY_FAILED` → `externalSystemsNote` ← `note` của ai-service → audit `ERASURE_EXECUTED` | java-core |
| [ ] `DELETE /internal/contacts/{id}/lead-scores` → `{deleted: n}`, luỹ đẳng | java-core |
| [ ] Chặn `/ai/v1/ai/privacy/**` ở gateway | gateway |
| [ ] `ErasureRequestsPage`: nút "Tạo yêu cầu" (chọn khách, căn cứ pháp lý, nguồn) + nút "Xác minh danh tính" trên dòng `PENDING` | dashboard |
| [ ] Biên bản xác nhận — xem **Điểm chốt Q4** | java-core |

| Bước đặc tả | Thao tác | Phải thấy |
|---|---|---|
| chuẩn bị | Gắn một tài liệu riêng cho khách X (`PATCH /v1/documents/{id}` `contact_id`, gọi API trực tiếp) rồi hỏi ở widget | câu trả lời trích tài liệu đó |
| 1–2 | Tạo yêu cầu xoá cho X | dòng `PENDING`, cột xác minh "Chưa xác minh" |
| 3.1 | Thực thi ngay khi chưa xác minh | 409, thông báo chưa xác minh |
| 3–4 | Bấm "Xác minh danh tính" | hiện tên người xác minh |
| 5–6 | Xem trước phạm vi | bảng theo từng bảng + cảnh báo "phạm vi dừng ở hệ thống này (MCP)" |
| 7–10 | Thực thi, gõ `XOA VINH VIEN` | `COMPLETED`; màn tiến độ hiện số dòng từng bảng |
| sau | Hỏi lại câu cũ ở widget | **không** còn trích tài liệu của X; hồ sơ X đã ẩn danh |
| 2.1 | Tạo yêu cầu thứ hai cho X khi yêu cầu đầu còn mở | bị chặn |
| 8.1 · 9.1 | Tắt ai-service → thực thi khách Y → bật lại → "Chạy lại phần còn lại" | lần 1 `PARTIALLY_FAILED` (mục AI hỏng); lần 2 `COMPLETED`, mục CRM không chạy lại |
| gateway | `curl` `/ai/v1/ai/privacy/contacts/…` qua :8080 | bị chặn |

### Cổng ra GD3

- [ ] UC026, UC041 đủ 4 điều ở mục 0
- [ ] Test java-core: cổng xác minh (409), luỹ đẳng `lead-scores`, `/internal/**` thiếu token → 401/403
- [ ] `mvn compile` · `npm run typecheck` · ai-service `ruff` + `compileall` + `pytest` (đổi header client)
- [ ] Tắt hết tiến trình

**Phải giải thích được:** vì sao ai-service ghi tóm tắt qua API chứ không ghi thẳng · vì sao ẩn danh danh bạ
thay vì xoá vật lý · vì sao gọi ai-service **ngoài** transaction của java-core.

---

## GD4 — Diễn tập trọn luồng + hoàn thiện

- [ ] Bật stack từ đầu theo thứ tự GD1, đi lại **8 UC một lèo** theo đúng thứ tự: đăng nhập → tải → tiến độ →
      quản lý kho → chat (trích dẫn / từ chối / chuyển giao) → 👍/👎 → khoảng trống → đóng → tóm tắt → xoá
- [ ] Sửa chỗ vỡ. Mỗi chỗ vỡ một dòng: hiện tượng · nguyên nhân · cách sửa
- [ ] Bảng minh chứng cuối: 8 UC × "bước đặc tả → thao tác → kết quả", kèm ảnh chụp `docs/report/scr-gd-*.png`
- [ ] `docs/on-tap/tich-hop-giao-dien.md`: luồng từng UC qua bốn tầng, lớp chuyển tiếp, ánh xạ trường, gộp các câu "Phải giải thích được" của GD1–GD3
- [ ] Cập nhật artifact "Bản đồ luồng AI CRM" (https://claude.ai/artifact/9ne7Td2SmgB5owL6FhrdpB): sửa ô chuyển giao, thêm đường giao diện. **Không hoãn**
- [ ] Còn giờ: đo nhanh độ trễ thao tác trên giao diện, ghi số thật (không phải cổng)
- [ ] Chạy `/handoff`; soạn lệnh commit/push; PR trên web sau `git pull origin develop`

---

## 4. Điểm cần bạn chốt — hỏi ở đầu GD tương ứng, trước khi làm

| # | Câu hỏi | Đề xuất | GD |
|---|---|---|---|
| Q1 | UC026 làm những trigger nào? Đặc tả có 4: chuyển giao · kết thúc · ngưỡng số lượt · thủ công | `CLOSING` (bắt buộc) + `MANUAL` (ai-service đã có `POST /v1/ai/summarize`, java-core thêm 1 endpoint + 1 nút). `HANDOFF`, `TURN_THRESHOLD` ghi vào "giảm độ sâu" | GD3 |
| Q2 | Tỉ lệ tích cực UC027 bước 7 hiện ở đâu? `AiPerformancePage` là màn của UC039 (Dev B) | java-core điền `GET /api/v1/analytics/ai-performance` phần lấy được từ `/v1/ai/quality` (tỉ lệ từ chối, tỉ lệ tích cực, số đánh giá, bám nguồn trung bình); trường riêng của UC039 để rỗng; báo Dev B | GD2 |
| Q3 | Bảo vệ `/internal/**` bằng gì? | Dùng chung `INTERNAL_API_TOKEN` cả hai chiều, ai-service gửi thêm `X-Internal-Token` | GD3 |
| Q4 | Biên bản xác nhận UC041 làm tới đâu? | Bản gọn: biên bản = `items` + thời điểm + người xác minh, lưu trong yêu cầu và dòng kiểm toán; `certificateUri = null`, ghi vào "giảm độ sâu" | GD3 |
| Q5 | Màn "Tìm thử" (SCR031 `knowledge/search`) không thuộc luồng chính UC020 và ai-service chưa có endpoint | Để ngoài đợt, ghi rõ; không ẩn màn — **✅ chốt 24/10 theo đề xuất** | GD1 |
| Q6 | Dev B chưa trả lời mục 1 thì có làm trước không? | **✅ chốt 24/10:** 8 UC AI là việc của Dev A từ dashboard → java-core → ai-service — làm đúng, chạy chuẩn luôn, kể cả file dùng chung; chỉ **báo** Dev B (tin ở `docs/contracts/giao-dien-gd.md` mục 0) | GD1 |

---

## 5. Giảm độ sâu đã biết — ghi vào báo cáo, không giấu

- UC019: java-core đọc tiến độ bằng REST (đặc tả cho phép), **không** tiêu thụ `ai.kb.document.indexed` (sự kiện
  chưa có lược đồ). Không có trạng thái `PAUSED`. Không có `tokensUsed`/`costVnd` cho việc nạp.
- UC023: không có semantic cache (bỏ cùng N16). `ai.turn.completed` chưa phát.
- UC025: số "khách khác nhau" xấp xỉ bằng số hội thoại khác nhau (`ai_interactions` không có `contact_id`).
- UC026: theo Q1. `TOKEN_QUOTA_EXCEEDED` chưa có.
- UC041: thực thi đồng bộ; biên bản theo Q4; phạm vi xoá không vươn tới hệ thống ngoài (MCP đã hoãn).
- Lỗ hổng `contact_id` (tài liệu riêng của khách bị trích cho khách khác) **chưa vá** — làm sau đợt, ADR-0036.
- `mask_pii` không che họ tên (phát hiện N17).
