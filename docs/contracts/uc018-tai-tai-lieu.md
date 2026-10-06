# Hợp đồng UC018 — Tải lên tài liệu tri thức

**Trạng thái:** Nháp — chờ hai bên thống nhất rồi mới vá `docs/openapi/` và `docs/events/`
(mục 9) · **Ngày:** 27/09/2026 · **Căn cứ:** đặc tả UC018 · ADR-0002 · ADR-0003 · ADR-0020 · ADR-0022 · ADR-0023

**Nguồn sự thật là code, không phải tài liệu này.** Mọi chi tiết dưới đây chép từ:

| Phía | File |
|---|---|
| ai-service | `ai-service/src/ai/schemas.py` (DTO) · `src/api/errors.py` + `src/ai/exceptions.py` (mã lỗi) · `src/ai/rag/ingest/luu_tru.py` (kiểm URI) · `src/ai/rag/ingest/mime.py` (đuôi, MIME) · `src/ai/service.py::index_document` (thứ tự bước) |
| java-core | `platform/controller/KnowledgeDocumentController.java` · `platform/service/impl/KnowledgeDocumentServiceImpl.java` · `platform/service/impl/KbObjectKey.java` (dựng key) · `platform/service/impl/UsageQuotaServiceImpl.java` (hạn mức) · `client/AiServiceClient.java` |
| Test | `ai-service/tests/integration/test_upload_documents.py` · `java-core/src/test/.../KnowledgeDocumentUploadIntegrationTest.java` |

Tài liệu và code lệch nhau thì **code đúng** — sửa tài liệu.

---

## 0. Tóm tắt

Người dùng tải tệp lên **java-core**. java-core kiểm dung lượng, siêu dữ liệu, đuôi tệp và
hạn mức gói, ghi tệp lên kho S3 dưới thư mục của tenant, rồi báo **ai-service** URI của tệp.
ai-service kiểm URI thuộc tenant, kiểm nội dung thật của tệp, ghi bản ghi `PENDING` và trả 202.
Nhận 202 thì java-core cộng hạn mức và ghi sự kiện outbox trong **cùng một transaction**.

Ranh giới đặt ở **URI tệp**: java-core không đọc nội dung tệp, ai-service không ghi vào schema
của Track A (ADR-0002, ADR-0020 quyết định 2).

```
dashboard ──multipart──▶ java-core ──PutObject──▶ kho S3 (RustFS/AWS)
                            │                         ▲
                            │ JSON {file_uri,…}       │ HEAD + GET
                            └──────────────────▶ ai-service ──INSERT PENDING──▶ knowledge.knowledge_documents
                            ◀── 202 {document_id,…} ──┘
                            │
                            └─ cùng transaction: usage_records (DOCUMENT +1, STORAGE_MB +byte) · outbox_events
```

---

## 1. Chặng 1 — dashboard → java-core: `POST /api/v1/documents`

### 1.1. Yêu cầu

`Content-Type: multipart/form-data`. Qua gateway (`/api/v1/**` → `lb://java-core`).

| Header | Bắt buộc | Ghi chú |
|---|---|---|
| `Authorization: Bearer <JWT>` | ✓ | RS256. Claim bắt buộc: `sub` (userId), `tenantId` (UUID), `roleCode`. Chỉ `roleCode = TENANT_ADMIN` được tải lên |
| `X-Trace-Id` | — | Gateway gắn; thiếu thì java-core tự sinh và trả lại ở header phản hồi |

| Trường | Bắt buộc | Luật (áp theo thứ tự: chuẩn hoá **NFC** → `strip` → đếm **code point**) |
|---|---|---|
| `file` | ✓ | ≤ **20 MiB** (= 20 × 1024 × 1024 byte = `20971520`). Đuôi ∈ `.pdf` `.docx` `.txt` `.md` `.markdown` `.html` `.htm`, không phân biệt hoa thường |
| `title` | ✓ | 3–**255** code point sau NFC + strip (không phải 3–300 như đặc tả — ADR-0020 quyết định 3) |
| `description` | — | ≤ 500 code point. Rỗng hoặc toàn khoảng trắng coi như không có (`null`) |
| `language` | — | `vi` \| `en`. Thiếu hoặc rỗng ⇒ `vi` |

**Không có trường `tenantId`.** Tenant lấy DUY NHẤT từ claim `tenantId` của JWT. Gửi thêm
trường `tenantId`/`tenant_id` trong form thì bị **bỏ qua** (form field thừa không được bind) —
key trên S3 vẫn theo tenant của JWT; test `boQuaTenantTrongForm` khoá hành vi này.

**Tên tệp gốc** (`file.getOriginalFilename()`) được làm sạch trước khi dùng: lấy phần sau dấu
`/` hoặc `\` cuối cùng (trình duyệt Windows cũ gửi cả đường dẫn), NFC, bỏ ký tự điều khiển
(`Cc`) và ký tự định dạng vô hình (`Cf` — U+200B, U+202E đảo chiều chữ, BOM), strip. Kết quả
rỗng hoặc dài quá 255 code point ⇒ 422. Tên này gửi sang ai-service ở trường `file_name`.

### 1.2. Phản hồi 202

Vỏ `ApiResponse` (`common/response/ApiResponse.java`), `data` theo hình `TaiLieu` của
`dashboard-api.yaml` **cộng ba trường mới** `jobId`, `documentQuota` và `storageQuota`:

```json
{
  "success": true,
  "data": {
    "id": "5f0c…",
    "jobId": "5f0c…",
    "title": "Chính sách đổi trả",
    "description": null,
    "sourceType": "MD",
    "fileName": "chinh-sach-doi-tra-v2.md",
    "mimeType": "text/markdown",
    "sizeBytes": 3412,
    "language": "vi",
    "status": "PENDING",
    "chunkCount": 0,
    "version": 2,
    "errorMessage": null,
    "uploadedByName": null,
    "indexedAt": null,
    "createdAt": "2026-09-27T03:15:22.481Z",
    "documentQuota": {
      "used": 16,
      "quota": 20,
      "percent": 80.0,
      "warnedAt": "2026-09-27T03:15:22.470Z",
      "blockedAt": null
    },
    "storageQuota": {
      "used": 7340032,
      "quota": 104857600,
      "percent": 7.0,
      "warnedAt": null,
      "blockedAt": null
    }
  },
  "message": null,
  "code": null,
  "traceId": null,
  "timestamp": "2026-09-27T03:15:22.490Z"
}
```

- `id` = `jobId` = `document_id` của ai-service — một tài liệu có đúng một tiến trình nạp
  (V202: cột `status` thay cho bảng `ingestion_jobs`).
- `sourceType`, `mimeType`, `version` lấy từ phản hồi của ai-service (MIME **thật**, không phải
  MIME trình duyệt khai). `sizeBytes`, `fileName`, `language`, `description` do java-core biết.
- `uploadedByName` luôn `null` ở phản hồi này — người tải chính là người đang xem.
- `documentQuota` / `storageQuota` là **lượng đang có SAU lượt tải này** so với trần của gói
  (mục 5): số tài liệu, và dung lượng tính bằng **byte**. `warnedAt ≠ null` ⇒ giao diện hiện
  cảnh báo 80%. `blockedAt ≠ null` ⇒ đã chạm trần trong chu kỳ.

### 1.3. Mã lỗi — theo đúng thứ tự java-core kiểm

Thân lỗi: `ApiResponse` với `success = false`, **`code`** (trường mới — mục 9), `message`
tiếng Việt cho người dùng, `traceId`. Giao diện rẽ nhánh theo **`code`**, không theo `message`.

| # | HTTP | `code` | Khi nào | Giao diện nên làm gì |
|---|---|---|---|---|
| 1 | 401 | `UNAUTHORIZED` | Không có JWT, JWT sai chữ ký/hết hạn, hoặc thiếu claim `tenantId` hợp lệ | Về màn đăng nhập |
| 2 | 403 | `FORBIDDEN` | `roleCode ≠ TENANT_ADMIN` | Ẩn nút tải lên với vai trò này |
| 3 | 413 | `FILE_TOO_LARGE` | Tệp > 20 MiB — chặn ngay ở tầng servlet, trước khi đọc form | Luồng phụ 4.2: đề nghị tách nhỏ |
| 4 | 422 | `INVALID_METADATA` | Thiếu `file`/`title`; `title` ngoài 3–255; `description` > 500; `language` ∉ {vi, en}; tên tệp rỗng hoặc > 255 | Giữ hộp thoại, đánh dấu trường sai |
| 5 | 415 | `UNSUPPORTED_FORMAT` | Đuôi không nằm trong danh sách nhận | Luồng phụ 4.1: hiện danh sách đuôi nhận được |
| 6 | 409 | `SUBSCRIPTION_NOT_ACTIVE` | Không có thuê bao `TRIALING`/`ACTIVE` đang trong chu kỳ `[period_start, period_end)` · **[CẦN XÁC NHẬN]** — đặc tả chưa có mã này | Dẫn sang màn gói dịch vụ |
| 7 | 409 | `DOCUMENT_QUOTA_EXCEEDED` | Số tài liệu đang có + 1 > `max_documents` — `data` là trạng thái hạn mức | Luồng phụ 6.1: đề nghị gỡ bớt tài liệu hoặc nâng gói |
| 7b | 409 | `STORAGE_MB_QUOTA_EXCEEDED` | Dung lượng đang có + byte của tệp > `storage_mb` — `data` là trạng thái hạn mức (byte). ADR-0023 | Như trên, kèm số MB đang dùng / trần / tệp này |
| 8 | 503 | `STORAGE_UNAVAILABLE` | Không ghi được lên kho S3, **hoặc** ai-service không đọc được kho S3 | "Thử lại sau" — không phải lỗi của tệp |
| 9 | 415 / 413 / 422 | *(chuyển nguyên `code` của ai-service)* | ai-service từ chối nội dung tệp — ca thật: **nội dung không khớp đuôi** (PNG đổi đuôi `.pdf`, ZIP đổi đuôi `.docx`) | Như dòng 5 |
| 10 | 503 | `AI_SERVICE_UNAVAILABLE` | ai-service không trả lời, quá thời gian chờ, hoặc trả 5xx | "Thử lại sau" |
| 11 | 500 | `INTERNAL_ERROR` | ai-service trả 401/403/`FILE_NOT_FOUND` — lỗi lập trình giữa hai bên, không phải lỗi người dùng. Chi tiết chỉ vào log ERROR | Thông báo chung kèm `traceId` |

Dòng 3 đứng trước dòng 4 vì giới hạn multipart của servlet nổ trước khi Spring bind form. Từ
dòng 5 trở đi thứ tự do `KnowledgeDocumentServiceImpl` quyết định. **Tệp vừa quá lớn vừa sai
đuôi thì cả hai tầng cùng trả 413** — khớp ghi chú đầu `mime.py`.

Từ dòng 1 đến dòng 7: **chưa có gì được ghi** (không object S3, không gọi ai-service). Dòng 8
đến 11: object vừa ghi bị **xoá** trước khi trả lỗi (mục 4, bước 6).

---

## 2. Chặng 2 — java-core → ai-service: `POST /v1/ai/kb/documents`

Gọi qua `client/AiServiceClient` — bề mặt **duy nhất** của java-core nói chuyện với ai-service.
Tên dịch vụ `ai-service` phân giải qua Spring Cloud LoadBalancer (Eureka; dự phòng bằng
`spring.cloud.discovery.client.simple` khi ai-service chưa tự đăng ký Eureka). Chờ kết nối
**2 s**, chờ đọc **30 s** — ai-service phải tải cả tệp 20 MiB từ S3 về để kiểm DOCX.

### 2.1. Header

| Header | Giá trị |
|---|---|
| `X-Tenant-Id` | `tenantId` từ JWT, dạng `UUID.toString()` (chữ thường, có gạch nối) |
| `X-Trace-Id` | Trace ID của request gốc |
| `Content-Type` | `application/json` |

### 2.2. Thân — JSON phẳng, `snake_case`

```json
{
  "file_uri": "s3://kb-tai-lieu/11111111-1111-1111-1111-111111111111/7d4e2f0a-…/chinh-sach-doi-tra-v2.md",
  "file_name": "chinh-sach-doi-tra-v2.md",
  "title": "Chính sách đổi trả",
  "description": null,
  "language": "vi",
  "uploaded_by": "9b1c…"
}
```

| Trường | Kiểu | Luật (Pydantic `KbDocumentCreate`, `extra="forbid"`) |
|---|---|---|
| `file_uri` | string 1–2048 | Dạng DUY NHẤT: `s3://{bucket}/{tenant_id}/…/{tên}` — mục 3 |
| `file_name` | string 1–255 | NFC + strip. Chỉ dùng để lấy **đuôi** và để hiển thị; không dùng để đọc tệp |
| `title` | string 3–255 | NFC + strip, rồi mới đếm code point |
| `description` | string ≤ 500 \| null | Toàn khoảng trắng ⇒ `null` |
| `language` | `"vi"` \| `"en"` | Mặc định `"vi"` |
| `uploaded_by` | UUID \| null | `sub` của JWT nếu là UUID. Lưu uuid trần, không FK (ADR-0002) |

**KHÔNG có `tenant_id`.** Gửi thêm bất kỳ trường nào ngoài sáu trường trên ⇒ 422
`INVALID_METADATA` — `extra="forbid"` biến việc lén gửi tenant thành lỗi ồn ào thay vì bị bỏ
qua trong im lặng.

### 2.3. Phản hồi 202 — `KbDocumentAccepted`

```json
{
  "document_id": "5f0c…",
  "job_id": "5f0c…",
  "title": "Chính sách đổi trả",
  "version": 2,
  "status": "PENDING",
  "source_type": "MD",
  "mime_type": "text/markdown"
}
```

`source_type` ∈ `PDF` `DOCX` `TXT` `MD` `HTML`. `mime_type` tra từ `source_type`
(`mime.py::MIME_THEO_DINH_DANG`). Trùng `(tenant, title)` ⇒ `version` tăng, bản cũ giữ nguyên
(cấp dưới `pg_advisory_xact_lock`).

### 2.4. Mã lỗi của ai-service và java-core xử lý thế nào

Thân lỗi ai-service: `{"code": "...", "message": "..."}`; riêng 422 validate có thêm
`"errors": [{"loc": [...], "msg": "..."}]` (không lặp lại giá trị đầu vào — Nghị định 13).

| ai-service trả | Ý nghĩa | java-core trả | Xoá object S3? |
|---|---|---|---|
| 202 | Đã nhận, `PENDING` | 202 — tiếp mục 4 bước 7 | Không |
| 401 `TENANT_CONTEXT_MISSING` | Thiếu `X-Tenant-Id` | 500 `INTERNAL_ERROR` (lỗi java-core) | Có |
| 403 `FORBIDDEN_FILE_URI` **[CẦN XÁC NHẬN]** | URI ngoài vùng tenant — dấu hiệu tấn công hoặc java-core dựng key sai | 500 `INTERNAL_ERROR`, log ERROR | Có |
| 413 `FILE_TOO_LARGE` | Lớp phòng thủ thứ hai (HEAD thấy > 20 MiB) | 413 `FILE_TOO_LARGE` | Có |
| 415 `UNSUPPORTED_FORMAT` | Nội dung thật không khớp đuôi | 415 `UNSUPPORTED_FORMAT` | Có |
| 422 `INVALID_METADATA` | Siêu dữ liệu sai — java-core lẽ ra đã chặn | 422 `INVALID_METADATA` | Có |
| 422 `FILE_NOT_FOUND` **[CẦN XÁC NHẬN]** | URI hợp lệ nhưng kho không có object | 500 `INTERNAL_ERROR`, log ERROR | Có (nếu còn) |
| 503 `STORAGE_UNAVAILABLE` **[CẦN XÁC NHẬN]** | ai-service không đọc được S3 | 503 `STORAGE_UNAVAILABLE` | Có |
| 5xx khác · hết thời gian chờ · không kết nối | — | 503 `AI_SERVICE_UNAVAILABLE` | Có |

---

## 3. Định dạng key trên kho S3

```
s3://{bucket}/{tenant_id}/{upload_id}/{ten_da_lam_sach}
     kb-tai-lieu  UUID JWT   UUID mới     ví dụ: Bảng-giá-2026.pdf
```

| Phân đoạn | Nguồn | Vì sao |
|---|---|---|
| `bucket` | `S3_BUCKET`, mặc định `kb-tai-lieu` | Một bucket chung cho mọi tenant (ADR-0022 đánh đổi 4) |
| `tenant_id` | Claim `tenantId` của JWT, `UUID.toString()` | Cô lập ngay ở tầng lưu trữ. ai-service so **bằng đúng cả phân đoạn**, không so tiền tố chuỗi |
| `upload_id` | `UUID.randomUUID()` mỗi lượt tải | Tải lại cùng tên tệp (bản mới của cùng tiêu đề) **không ghi đè** object mà version cũ đang trỏ tới — đúng luồng phụ 7.1 "giữ nguyên bản cũ" |
| `ten_da_lam_sach` | Tên tệp gốc qua `KbObjectKey.sanitize` | Người xem kho (giao diện RustFS, S3 console) nhận ra tệp; không chứa ký tự ai-service từ chối |

**Làm sạch tên** (`KbObjectKey.sanitize`) — áp lên tên đã qua bước ở mục 1.1:

1. Giữ chữ cái (`L*`), dấu kết hợp (`M*`), chữ số thập phân (`Nd`) và `.` `-` `_`; mọi ký tự khác (khoảng trắng,
   `/`, `\`, `#`, `?`, `%`…) thành `-`; gộp các `-` liền nhau.
2. Bỏ `.` và `-` ở hai đầu — không còn `.`, `..`, tệp ẩn.
3. Cắt phần tên còn tối đa **150** code point, giữ nguyên đuôi.
4. Rỗng sau khi làm sạch ⇒ `tep` + đuôi (hoặc `tep` nếu không có đuôi).

Kết quả không bao giờ chứa phân đoạn rỗng, `.`, `..`, `\`, ký tự `Cc`/`Cf` — tức là luôn qua
được `luu_tru.kiem_uri_thuoc_tenant`. Content-Type của object luôn là
`application/octet-stream`: MIME trình duyệt khai không đáng tin, ai-service tự nhận diện.

**Quyền trên kho:** java-core `PutObject` + `DeleteObject` (xoá object của lượt thất bại);
ai-service `GetObject` (+ HEAD). Ở dev hai bên dùng chung tài khoản gốc RustFS — ADR-0022 đánh
đổi 5.

---

## 4. Thứ tự bước phía java-core và ranh giới transaction

Toàn bộ bước 4–8 nằm trong **một** `@Transactional` của `KnowledgeDocumentServiceImpl.upload`.
`app.tenant_id` được đặt bằng `set_config(…, true)` ngay khi transaction mở
(`security/TenantAwareJpaTransactionManager`) — không có đường nào khác để đặt nó.

| Bước | Việc | Lỗi |
|---|---|---|
| 1 | Chuỗi filter của Spring Security: xác minh JWT, lấy `tenantId`, kiểm `roleCode` — chưa đọc thân request | 401 / 403 |
| 2 | Servlet đọc multipart, giới hạn tệp 20 MiB | 413 |
| 3 | Bind form + Bean Validation: `title` / `description` / `language` | 422 |
| 4 | Kiểm lại dung lượng (lớp 2) → tên tệp → **đuôi tệp** | 413 / 422 / 415 |
| 5 | Tìm thuê bao đang hiệu lực; `SELECT … FOR UPDATE` hai dòng `usage_records` theo thứ tự cố định `DOCUMENT` → `STORAGE_MB` (tạo nếu chưa có — mục 5); `đang có + phần thêm > trần` ⇒ ghi mốc rồi từ chối | 409 |
| 6 | `PutObject` lên key ở mục 3 | 503 |
| 7 | Gọi ai-service (mục 2). Khác 202 ⇒ `DeleteObject` rồi trả lỗi theo bảng 2.4 | theo 2.4 |
| 8 | `DOCUMENT + 1`, `STORAGE_MB + byte`, ghi `warned_at`/`blocked_at` nếu vừa vượt ngưỡng, **ghi `outbox_events`** — cùng transaction | — |
| 9 | Commit, trả 202 | — |

**Khoá dòng hạn mức giữ suốt bước 5–9**, kể cả lúc ghi S3 và chờ ai-service. Đây là chủ ý:
khoá ngắn hơn thì hai lượt tải đồng thời lúc `used = quota − 1` đều qua kiểm, đều được
ai-service nhận, và hạn mức bị vượt. Test `sauLuotDongThoiKhiConMotCho` khoá hành vi
này: 6 lượt đồng thời ⇒ đúng 1 lượt 202, 5 lượt 409. Cái giá: các lượt tải **của cùng một
tenant** xếp hàng nối tiếp nhau (tenant khác không bị chặn), và mỗi lượt giữ một kết nối CSDL
trong lúc chờ ai-service — chấp nhận được ở quy mô SME, ghi ở mục Đánh đổi của ADR-0020.

**Ba khe không nhất quán đã biết** — không có giao dịch phân tán giữa hai dịch vụ:

| Khe | Hậu quả | Giảm thiểu |
|---|---|---|
| ai-service đã commit `PENDING`, rồi java-core commit hỏng (bước 8–9) | Tài liệu `PENDING` không có sự kiện, không tính hạn mức | Hiếm (lỗi CSDL giữa chừng). UC019 cần quét `PENDING` quá hạn — ghi nợ cho Ngày 4 |
| ai-service xử lý xong nhưng java-core hết 30 s chờ | java-core xoá object và trả 503; ai-service còn một dòng `PENDING` trỏ vào object đã mất | Worker gặp `FILE_NOT_FOUND` ⇒ `FAILED`. Chấp nhận |
| `DeleteObject` ở bước 7 hỏng | Object mồ côi trên S3, không dòng nào trỏ tới | Log WARN kèm key. Dọn định kỳ theo tiền tố — sau đồ án |

---

## 5. Hạn mức — lượng ĐANG CÓ, cảnh báo 80%, chặn 100%

**Hạn mức tài liệu là lượng đang có, không phải lượt tải trong chu kỳ** — nhóm chốt 27/09/2026,
lập luận và đánh đổi ở ADR-0023. Hai chỉ số, cùng một cách kiểm:

| Chỉ số | Đếm gì | Trần | Đơn vị |
|---|---|---|---|
| `DOCUMENT` | Mọi bản ghi tài liệu đang tồn tại — mỗi `version` là một, kể cả bản `FAILED` | `max_documents` | tài liệu |
| `STORAGE_MB` | Tổng dung lượng tệp gốc đang lưu | `storage_mb × 1 048 576` | **byte** (tên chỉ số giữ theo V102) |

- **Chặn:** `đang có + phần thêm > trần` ⇒ 409. Tệp lấp đúng trần vẫn được nhận.
- **Sang chu kỳ mới:** dòng hạn mức mới **chép mức đang có** từ chu kỳ gần nhất trước đó; `quota_value`
  chép từ gói hiện hành. (Hội thoại và token là dòng chảy — chu kỳ mới về 0.)
- **Lượt bị ai-service từ chối** không được đếm — object đã bị xoá (mục 4 bước 7).
- **Gỡ tài liệu (UC020) phải trả lại chỗ:** `DOCUMENT − 1`, `STORAGE_MB − file_size_bytes`, cùng
  transaction với outbox `DocumentDeleted`. Vì vậy phản hồi gỡ của ai-service phải có
  `file_size_bytes` — ghi vào hợp đồng UC020.

Mốc cần **migration V128** (Track A): `warned_at`, `blocked_at` trên `platform.usage_records` —
đặc tả UC018 ghi thẳng tên hai cột này, `dashboard-api.yaml` (`HanMucSuDung.warnedAt`/`blockedAt`)
đã khai từ trước, nhưng V102 chưa có.

| Mốc | Điều kiện | Ghi |
|---|---|---|
| Cảnh báo | Sau khi cộng: `used × 100 ≥ quota × 80` và `warned_at` đang trống | `warned_at = now()` |
| Chạm trần | Sau khi cộng: `used ≥ quota` và `blocked_at` đang trống | `blocked_at = now()` |
| Từ chối | Trước khi cộng: `used + phần thêm > quota` | 409; ghi `blocked_at` (và `warned_at`) nếu còn trống — ghi này **được commit** dù trả lỗi. Với dung lượng, lượt bị chặn thường chưa lấp đủ 100% |

Mốc ghi **một lần** mỗi chu kỳ, không ghi đè — đó là "thời điểm chạm mốc" UC006 4.1–4.2 hiển thị.
Mốc có bị xoá khi gỡ bớt tài liệu làm mức dùng tụt xuống hay không: chốt ở UC020.
`percent = used × 100 / quota` (quota = 0 ⇒ 100). Gói TRIAL (20 tài liệu, 100 MB): tài liệu thứ
16 ghi `warned_at`, thứ 20 ghi `blocked_at`, thứ 21 nhận 409.

---

## 6. Sự kiện `DocumentUploaded`

Ghi vào `platform.outbox_events` ở bước 8 — **không** gọi `KafkaTemplate.send()` (ADR-0003).
Job phát `platform/messaging/OutboxPublisher` (500 ms, lô 100) đọc bảng này và phát lên Kafka với
**khoá bản tin = `tenant_id`**. Chỉ một job phát chạy tại một thời điểm (khoá advisory), và một sự
kiện phát hỏng chặn các sự kiện sau **của cùng tenant** (thử lại lùi dần 2 → 60 s) — thứ tự trong
tenant được giữ, tenant khác không bị kẹt. Chưa có hàng đợi chết.

| Cột `outbox_events` | Giá trị |
|---|---|
| `tenant_id` | tenant của JWT — cũng là khoá phân vùng Kafka |
| `aggregate_type` | `document` |
| `aggregate_id` | `document_id` từ ai-service |
| `event_type` | `DocumentUploaded` |
| `topic` | `crm.kb.document.uploaded` — theo đặc tả UC018 và Master Plan §2.6, chốt 27/09/2026 (ADR-0020 quyết định 4) |
| `headers` | `{"X-Trace-Id": "…"}` — Trace ID đi ở header Kafka, không ở payload |
| `payload` | bên dưới |

```json
{
  "document_id": "5f0c…",
  "version": 2,
  "source_type": "MD",
  "mime_type": "text/markdown",
  "size_bytes": 3412,
  "language": "vi",
  "uploaded_by": "9b1c…"
}
```

Không có `title`, `file_name`, `file_uri`: consumer `ingestion-cg` (ai-service) đọc chi tiết từ
`knowledge_documents` của chính nó theo `document_id`. Sự kiện càng ít dữ liệu người dùng
nhập thì càng ít thứ phải xoá khi có yêu cầu UC041.

Vỏ sự kiện job phát dựng (khuôn chung của `docs/events/`): `event_id` = `outbox_events.id`,
`event_version` = 1 (topic đặt tên theo sự kiện, không có hậu tố `.vN`), `event_type`, `tenant_id`, `aggregate_id`,
`occurred_at` = `created_at` của dòng outbox, `payload` như trên.

---

## 7. `PARSE_NO_TEXT_EXTRACTED` không phải mã HTTP

PDF chỉ có ảnh (`ban-scan-bao-hanh.pdf`) được nhận **202** ở UC018 — ai-service chỉ kiểm chữ ký
`%PDF-`, chưa phân tích cú pháp. Nó chỉ chuyển `FAILED` kèm
`error_message = PARSE_NO_TEXT_EXTRACTED…` khi parser của UC019 chạy (ràng buộc `ck_doc_failed`).
Giao diện thấy lỗi này ở màn tiến độ nạp (SCR033), không phải ở hộp thoại tải lên. Lượt tải đó
**vẫn tính** vào hạn mức.

---

## 8. Kiểm chứng

| Ca | Ở đâu | Kết quả |
|---|---|---|
| 25/25 tệp mẫu ra đúng mã phía ai-service | `test_upload_documents.py::test_manifest_25_tep_dung_ma_http` | xanh |
| 401 / 403 / 413 / 422 / 415 / 409 / 503 / 500 phía java-core, key đúng tenant, outbox, 80% / 100%, 6 lượt đồng thời, hết dung lượng theo byte, chu kỳ mới chép mức đang có | `KnowledgeDocumentUploadIntegrationTest` — 22 ca (Postgres + RustFS thật, JWT ký thật, ai-service giả lập bằng máy chủ HTTP trong test) | xanh |
| Làm sạch tên tệp, đuôi giống `PurePath.suffix` | `KbObjectKeyTest` — 21 ca | xanh |
| Job phát: khoá = `tenant_id`, cùng tenant cùng phân vùng đúng thứ tự, vỏ sự kiện, header, sự kiện hỏng chỉ chặn tenant của nó | `OutboxPublisherIntegrationTest` — 3 ca (Postgres + Kafka thật) | xanh |
| **Luồng thật: java-core → RustFS → ai-service → Kafka**, tenant gói STARTER | `scripts/e2e-uc018.sh up && … run` — hạ tầng dùng một lần; báo cáo [`docs/report/uc018-e2e-2026-09-27.md`](../report/uc018-e2e-2026-09-27.md) | **25/25** đúng mã theo `manifest.csv`; "Chính sách đổi trả" ra v1 (DOCX) + v2 (MD) ở hai key khác nhau; 21 dòng `PENDING`, 21 object, 21 sự kiện; hai tệp bị ai-service trả 415 đã bị xoá khỏi kho |
| **Dữ liệu lưu đầy đủ** — 44 tài liệu (gồm tên tiếng Việt, NFD, có mô tả, tiếng Anh): từng trường `knowledge_documents`, SHA-256 từng object, hạn mức, outbox, Kafka, sẵn sàng cho UC019 | `scripts/e2e-uc018.sh run` phần 3 | **22/22**; kiểm ngược (phá dữ liệu rồi `soi`) đỏ đúng 3 mục |
| **Ca 409 đầu-cuối**, tenant gói TRIAL (20) | Như trên, 21 lượt tải | lần 16: 202, `warnedAt` có (80%) · lần 20: 202, `blockedAt` có (100%) · lần 21: **409 `DOCUMENT_QUOTA_EXCEEDED`**, không object, không gọi ai-service |

**Kiểm ngược đã chạy:** bỏ `@Lock(PESSIMISTIC_WRITE)` ⇒ 6 lượt đồng thời lúc 19/20 ra 6 × 202
(test đỏ). Bỏ `noRollbackFor` ở `UsageQuotaServiceImpl` ⇒ lượt hết hạn mức ra 500
`UnexpectedRollbackException` thay vì 409 (test đỏ). Bỏ chặn-theo-tenant của job phát ⇒ sự kiện
sau của tenant có sự kiện hỏng bị phát vượt lên (test đỏ). Tắt chép mức tồn kho sang chu kỳ mới ⇒
lượt đầu chu kỳ ra tài liệu thứ 1 thay vì thứ 8 (test đỏ).

**Kafka ở lượt chạy thật:** 41/41 sự kiện đã phát; 21 bản tin của tenant A cùng ở phân vùng 0, 20 bản
tin của B cùng ở phân vùng 2; header `X-Trace-Id`, không có header `__TypeId__`.

---

## 9. Chỗ lệch phải vá khi chốt

| File:dòng | Đang ghi | Phải thành |
|---|---|---|
| `docs/openapi/dashboard-api.yaml:1399` | "Vượt `plans.max_documents` hoặc vượt giới hạn dung lượng mỗi tệp thì 409" | 409 chỉ cho hạn mức; 413 cho dung lượng |
| `docs/openapi/dashboard-api.yaml:1409` | `title: { maxLength: 300 }` | `minLength: 3, maxLength: 255`; thêm `description.maxLength: 500`, `language.enum: [vi, en]` |
| `docs/openapi/dashboard-api.yaml:1421-1430` | Chỉ có 202 / 409 / 415 | Thêm 413, 422, 503; tách hai `code` của 409 |
| `docs/openapi/dashboard-api.yaml:1413-1420` | 202 trả `TaiLieu` | `TaiLieu` + `jobId` + `documentQuota` + `storageQuota` (`MotHanMuc` + `warnedAt` + `blockedAt`) |
| `docs/openapi/dashboard-api.yaml` — `HanMucSuDung` | Bốn hạn mức, không có dung lượng | Thêm `storage` (byte) — ADR-0023 |
| `docs/openapi/dashboard-api.yaml:2974` (`ApiResponse`) | Không có `code` | Thêm `code: string \| null` — đổi **vỏ chung** của mọi endpoint, giao diện rẽ nhánh theo nó |
| `docs/openapi/ai-service-to-java-core.yaml:74-92` | `POST /v1/documents`, "multipart" | `POST /v1/ai/kb/documents`, JSON mục 2. Giữ ý "java-core kiểm `max_documents` và `STORAGE_MB`" — đúng với ADR-0023 |
| `docs/events/` | Chỉ có `crm.document.v1.json` (payload TODO) | Thêm `crm.kb.document.uploaded.json` với payload mục 6; bảng topic ở `README.md` thêm dòng này (producer java-core, consumer `ingestion-cg`) |
| `docs/openapi/ai-service-to-java-core.yaml:54` | "…qua topic `crm.document.v1`" | `crm.kb.document.uploaded` |
| `docs/Dac-ta-UseCase-Module-AI.docx` — UC018 "Tham số và ngưỡng" | "Tiêu đề: 3–300 ký tự" | 3–255 (ADR-0020) |
| `docs/Dac-ta-UseCase-Module-AI.docx` — UC018 hậu điều kiện | "Mức tiêu thụ tài liệu được cộng vào `usage_records` của chu kỳ hiện tại" | "…cộng vào số tài liệu và dung lượng đang có" (ADR-0023); UC006 bốn hạn mức → năm |

---

## 10. Còn treo — [CẦN XÁC NHẬN]

1. ~~Hạn mức tài liệu là "lượt tải trong chu kỳ" hay "số tài liệu đang có"?~~ **Đã chốt 27/09:
   lượng đang có, cả số lượng lẫn dung lượng** — ADR-0023, mục 5. Còn treo trong ADR đó: xoá mốc
   khi mức dùng tụt xuống (UC020) và job đối soát bộ đếm với ai-service.
2. **Hai mã lỗi mới của java-core:** `SUBSCRIPTION_NOT_ACTIVE` (409) và `AI_SERVICE_UNAVAILABLE`
   (503 — mượn tên từ đặc tả UC041). Cùng ba mã phía ai-service đã đánh dấu ở mục 2.4.
3. **Sự kiện cảnh báo 80%.** UC006 4.1 nói "kèm ngày **đã gửi** cảnh báo" — tức là có gửi thông
   báo. Hiện chỉ ghi `warned_at`; chưa có sự kiện nào báo ra ngoài. `crm.usage.v1` mới khai
   `ConversationConsumed`/`TokensConsumed`.
