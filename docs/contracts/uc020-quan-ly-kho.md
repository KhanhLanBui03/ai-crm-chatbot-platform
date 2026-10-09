# Hợp đồng UC020 — quản lý kho tri thức (nháp 09/10/2026)

⚠️ Nháp phía Track B. Nguồn sự thật vẫn là `docs/openapi/ai-service-to-java-core.yaml` (mục B — bề mặt
đọc cho dashboard, ADR-0014) — **chưa sửa**, chờ Dev B xác nhận (mục 5). Căn cứ: đặc tả UC020,
[ADR-0031](../adr/0031-nap-lai-bang-ban-bong.md).

Mọi đường dẫn dưới đây đã có trong hợp đồng, TRỪ `PATCH /v1/documents/{documentId}`. Thay đổi so với
hợp đồng đều là **thêm trường**; tên tham số giữ nguyên (`keyword`, `status`, `sourceType`, `page`,
`size`). Tenant chỉ từ `X-Tenant-Id`; tài liệu của tenant khác ⇒ 404, không phân biệt với "không tồn tại".

## 1. Đọc — SCR030, SCR031, SCR032

| Đường dẫn | Ghi chú |
|---|---|
| `GET /v1/documents?page&size&keyword&status&sourceType` | `keyword` tìm trên tiêu đề + mô tả + tên tệp, **không phân biệt hoa thường và dấu** ("bao gia" khớp "báo giá"). Không lọc `status` thì **ẩn `ARCHIVED`**. Mới nhất trước. `size` mặc định 20 (đặc tả ghi 10 — java-core truyền tường minh) |
| `GET /v1/documents/{documentId}` | kể cả tài liệu `ARCHIVED` |
| `GET /v1/documents/{documentId}/chunks?page&size` | theo `chunk_index`; **không bao giờ trả `embedding`** |

`DocumentDetailResponse` — giữ `id, title, status, source_type, uploaded_by, chunk_count, created_at`,
**thêm**:

```yaml
        description: { type: [string, 'null'] }
        language: { type: string }
        file_name: { type: [string, 'null'] }
        mime_type: { type: [string, 'null'] }
        file_size_bytes: { type: [integer, 'null'] }
        version: { type: integer }
        error_message: { type: [string, 'null'] }
        indexed_at: { type: [string, 'null'], format: date-time }
        updated_at: { type: string, format: date-time }
        # Dòng này là bản bóng nạp lại của tài liệu nào (ADR-0031)
        replaces_document_id: { type: [string, 'null'], format: uuid }
        # Bản bóng ĐANG nạp lại tài liệu này — job_id để xem tiến độ ở /v1/ai/kb/ingestion-jobs/{id}
        reindex_document_id: { type: [string, 'null'], format: uuid }
```

Phần tử của `ChunkPageResponse.items` — giữ `chunk_id, content, chunk_index`, **thêm** `heading`,
`page_number`, `token_count`, `embedding_model`, `embedding_version`, `has_vector` (đặc tả UC020 bước 4:
hiện mô hình nhúng của TỪNG đoạn). `ChunkPageResponse` thêm `page`, `size`.

## 2. Sửa siêu dữ liệu — MỚI

```yaml
  /v1/documents/{documentId}:
    patch:
      operationId: updateDocumentMetadata
      requestBody:
        content:
          application/json:
            schema:
              type: object
              additionalProperties: false
              properties:
                title: { type: string, minLength: 3, maxLength: 255 }
                description: { type: [string, 'null'], maxLength: 500 }
      responses:
        '200': DocumentDetailResponse
        '404': DOCUMENT_NOT_FOUND
        '409': DOCUMENT_BUSY (đang nạp lại) · DOCUMENT_ARCHIVED
        '422': INVALID_METADATA (sai định dạng, hoặc tiêu đề mới trùng một tài liệu khác cùng version)
```

Chỉ `title` và `description`. **Không đụng chỉ mục vector**: `language` không sửa được vì nó quyết định
cách tách từ lúc nạp — đổi ngôn ngữ là nạp lại, không phải sửa siêu dữ liệu.

## 3. Nạp lại

| Đường dẫn | Phản hồi 200 (`ActionSuccessResponse` + trường thêm) |
|---|---|
| `POST /v1/documents/{documentId}/reindex` | `{success, message, document_id, job_id, version, status: "PENDING"}` — `job_id` là **bản bóng mới**, xem tiến độ ở `/v1/ai/kb/ingestion-jobs/{job_id}` |
| `POST /v1/ai/kb/reindex` (toàn kho, khi đổi mô hình nhúng) | `ReindexResponse {tenant_id, status: "ACCEPTED", total_documents}` |

Nạp lại tạo bản bóng (ADR-0031): bản cũ **vẫn `READY` và vẫn được truy hồi** tới khi bản mới nạp xong;
lúc đó bản cũ chuyển `ARCHIVED` trong cùng transaction. Bắt đầu nạp trong ≤ 60 s (chu kỳ bộ quét).
**`id` tài liệu đổi sau khi nạp lại** — giao diện theo `job_id` / `replaces_document_id`.

Lỗi: 404 · 409 `DOCUMENT_BUSY` (`PENDING`/`PROCESSING` hoặc đang có lượt nạp lại) · 409
`DOCUMENT_NOT_READY` (`FAILED`/`ARCHIVED` — tài liệu lỗi thì tải lên lại).

Hợp đồng ghi `200` cho cả hai; `dashboard-api.yaml` ghi `202` cho phía java-core — java-core tự đổi mã.

## 4. Gỡ khỏi chỉ mục

`DELETE /v1/documents/{documentId}` và `DELETE /v1/ai/kb/documents/{documentId}` — cùng một xử lý:
xoá đoạn TRƯỚC rồi `ARCHIVED`, cùng transaction. Phản hồi 200 `{success, message, chunks_deleted}`.
Gỡ lại tài liệu đã `ARCHIVED` ⇒ 200, `chunks_deleted: 0` (luỹ đẳng). 409 `DOCUMENT_BUSY` khi đang nạp
hoặc đang nạp lại. Lỗi hệ thống giữa chừng ⇒ 5xx và **trạng thái giữ nguyên** — java-core trả 502
`AI_SERVICE_UNAVAILABLE` (đặc tả) và không ghi gì về phía mình.

Tệp gốc trong kho S3 KHÔNG bị xoá (java-core sở hữu kho tệp, ADR-0022).

## 5. Cần Dev B xác nhận

1. Vá `ai-service-to-java-core.yaml` theo mục 1–4 (thêm `PATCH`, thêm trường)?
2. java-core: proxy SCR030–SCR032, sửa, nạp lại, gỡ — và ghi `platform.audit_logs` cho ba thao tác ghi
   (đặc tả UC020 bước 8). ai-service chỉ log có cấu trúc (`kiem_toan_kho`).
3. Gỡ tài liệu có trả lại hạn mức `DOCUMENT` / `STORAGE_MB` không? (ADR-0023: hạn mức theo lượng đang có.)
4. `ai.kb.document.indexed`: có trong `docs/events/README.md` nhưng chưa có lược đồ — cần không, ai tiêu thụ?
