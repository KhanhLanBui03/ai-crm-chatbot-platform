# Hợp đồng đợt tích hợp giao diện GD1–GD4 (nháp 24/10/2026)

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
> 5. Thấy khi chạy thật, **không thuộc GD1, chưa sửa**: gateway không có route `/ws` và java-core chưa có
>    endpoint STOMP → WebSocket 404, thanh trên luôn "Mất kết nối"; `GET /api/v1/audit-logs` và
>    `GET /api/v1/tool-calls` trả **500** (không có controller — route lạ đang rơi vào handler chung
>    thành 500 thay vì 404); ai-service chưa tự đăng ký Eureka (java-core dùng danh sách dự phòng).
>
> Còn mở cho GD2/GD3 (chưa đụng): mục 3–7, 10 của kế hoạch — `knowledge-gaps` sắp theo số khách,
> `correctedAnswer`, đánh giá từ widget, tạo/xác minh yêu cầu xoá, `/internal/**` bằng
> `X-Internal-Token`, phát `crm.conversation.closed`.

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
