# Hợp đồng UC026 + UC041 — tóm tắt hội thoại và xoá dữ liệu cá nhân (nháp 09/10/2026)

⚠️ Nháp phía Track B. Nguồn sự thật vẫn là `docs/openapi/java-core-to-ai-service.yaml`,
`docs/openapi/ai-service-to-java-core.yaml` và `docs/events/crm.conversation.closed.v1.json` — **chưa
sửa**, chờ Dev B xác nhận (mục 6). Căn cứ: đặc tả UC026, UC041;
[ADR-0032](../adr/0032-tom-tat-hoi-thoai-nhiet-do-0-anh-chup-model.md),
[ADR-0033](../adr/0033-xoa-du-lieu-ca-nhan-phia-ai.md).

Ở mục 1–3, ai-service **gọi** java-core. Các endpoint đó chưa có ở java-core: ai-service đang chạy
với `JAVA_CORE_MODE=mock`. `HttpJavaCoreClient` đã viết đúng hình dạng dưới đây và đã test bằng HTTP
giả. Track A làm xong thì chỉ cần đổi `JAVA_CORE_MODE=remote`.

Mọi lời gọi nội bộ mang `X-Tenant-Id` (tenant đã xác thực của luồng) và `X-Trace-Id`. Phản hồi bọc
trong `ApiResponse` của java-core (`{success, data, message, code, traceId, timestamp}`).

## 1. UC026 bước 2 — `GET /internal/conversations/{conversationId}/messages?page&size`

Đã khai đường dẫn trong `java-core-to-ai-service.yaml`, thân còn `# TODO`. Đề xuất:

```yaml
# ApiResponse.data = PageResponse (java-core common/response/PageResponse)
items:
  - senderType: CUSTOMER | BOT | AGENT | SYSTEM   # engagement.messages.sender_type (V107)
    content: string
    sentAt: date-time
    isRedacted: boolean                           # tin đã che theo UC041 — ai-service BỎ QUA
page: integer
size: integer          # ai-service gửi 200
totalItems: integer
totalPages: integer
```

Thứ tự: cũ trước, mới sau. Hội thoại không có, hoặc thuộc tenant khác, thì trả **404** (ai-service coi
là rỗng và bỏ qua).

## 2. UC026 bước 4 — `PATCH /internal/conversations/{conversationId}/summary`

```json
{
  "trigger": "CLOSING",
  "mainNeed": "…", "providedInfo": "…", "unresolvedIssues": "…", "nextSteps": "…",
  "modelVersion": "gemini-3.5-flash-lite@tt2",
  "summaryText": "Nhu cầu chính: …\nThông tin khách đã cung cấp: …\n…",
  "generatedAt": "2026-10-09T14:20:00+00:00"
}
```

| Trường → cột (V114/V107) | Ghi chú |
|---|---|
| bốn phần → `summary_data` jsonb | khoá **đúng** `mainNeed · providedInfo · unresolvedIssues · nextSteps` (comment V114). Phần nào không có thì ai-service gửi `"Không có"`, không bao giờ rỗng |
| `trigger` → `summary_trigger` | enum V114: `HANDOFF · CLOSING · TURN_THRESHOLD · MANUAL` |
| `modelVersion` → `summary_model_version` varchar(50) | ẢNH CHỤP `model@lời nhắc`, luôn ≤ 50 ký tự (ADR-0032) |
| `generatedAt` → `summarized_at` | |
| `summaryText` → `summary` | bản phẳng cho danh sách hộp thư và tìm kiếm toàn văn |

**Luỹ đẳng:** ghi đè bản mới nhất. ai-service có thể gửi lại cùng thân khi sự kiện được giao lại.
Trả 200 hoặc 204. Hội thoại đã bị xoá thì trả 404 (ai-service ghi lỗi, không thử lại mãi).

## 3. UC041 — `DELETE /internal/contacts/{contactId}/lead-scores` — MỚI

Xoá mọi dòng `sales.lead_scores` của khách (cột `features` chứa vector đặc trưng; quyền DELETE của
`crm_app` giữ lại cho đúng việc này — V113, ADR-0016). Trả `ApiResponse.data = {"deleted": n}`.
**Luỹ đẳng**: lần hai trả `deleted: 0`; khách không có điểm thì 200 với 0 (hoặc 404 — ai-service coi
như 0).

## 4. ai-service cung cấp — `DELETE /v1/ai/privacy/contacts/{contactId}?conversationId=…`

Đường dẫn theo đặc tả UC041 và Master Plan §2.5. **Chưa có** trong `ai-service-to-java-core.yaml`.

- **Header bắt buộc:** `X-Tenant-Id`, `X-Internal-Token` (bí mật dùng chung, cấu hình
  `INTERNAL_API_TOKEN` ở ai-service). Thiếu hoặc sai thì `403 INTERNAL_ONLY`. ai-service chưa cấu hình
  token thì endpoint đóng hẳn.
- **`conversationId`** (lặp lại được, tối đa 500): mọi hội thoại của khách. `ai_interactions` không có
  `contact_id`, chỉ java-core biết khách có những hội thoại nào. **Gọi TRƯỚC khi xoá hội thoại** ở
  `engagement`, và **ngoài** transaction của java-core — ai-service sẽ gọi ngược lại endpoint ở mục 3.
- **Phản hồi 200** — `items` theo khuôn `MucXoa` của `dashboard-api.yaml`, chép thẳng vào
  `data_erasure_requests.progress` được:

```json
{
  "contactId": "…", "status": "COMPLETED",
  "items": [
    {"targetSchema": "knowledge", "targetTable": "knowledge_documents", "action": "DELETE", "status": "DONE", "affectedRows": 1, "errorCode": null},
    {"targetSchema": "knowledge", "targetTable": "knowledge_chunks",    "action": "DELETE", "status": "DONE", "affectedRows": 1, "errorCode": null},
    {"targetSchema": "ai",        "targetTable": "ai_interactions",     "action": "DELETE", "status": "DONE", "affectedRows": 3, "errorCode": null},
    {"targetSchema": "ai",        "targetTable": "ai_feedback",         "action": "DELETE", "status": "DONE", "affectedRows": 2, "errorCode": null},
    {"targetSchema": "ai",        "targetTable": "ai_tool_calls",       "action": "DELETE", "status": "DONE", "affectedRows": 0, "errorCode": null},
    {"targetSchema": "s3",        "targetTable": "kb-tai-lieu",         "action": "DELETE", "status": "DONE", "affectedRows": 1, "errorCode": null},
    {"targetSchema": "sales",     "targetTable": "lead_scores",         "action": "DELETE", "status": "DONE", "affectedRows": 3, "errorCode": null}
  ],
  "note": "Phạm vi xoá phía AI: … KHÔNG vươn tới hệ thống bên ngoài đã nhận dữ liệu qua MCP …"
}
```

`status` là `COMPLETED` khi mọi mục `DONE`, còn không thì `PARTIALLY_FAILED` (mục hỏng mang
`errorCode`, ví dụ `JAVA_CORE_UNAVAILABLE`, `STORAGE_UNAVAILABLE`). Endpoint **luỹ đẳng**: gặp
`PARTIALLY_FAILED` thì gọi lại, phần đã xoá trả 0 dòng (đặc tả UC041 luồng phụ 8.1). `note` hiển thị
nguyên văn cho người duyệt (bước 6).

## 5. `PATCH /v1/documents/{documentId}` — thêm `contact_id`

Bổ sung nháp UC020 (`uc020-quan-ly-kho.md` mục 2): thân nhận thêm `contact_id` (uuid, `null` để gỡ),
và `DocumentDetailResponse` thêm `contact_id`. Đây là cách gắn tài liệu chứa dữ liệu của một khách
(hợp đồng, báo giá riêng) để UC041 xoá được (V214).

## 6. Cần Dev B xác nhận

1. **Trigger UC026:** `SummarizeRequest.trigger` trong `ai-service-to-java-core.yaml` ví dụ
   `CONVERSATION_CLOSED`, còn V114 chỉ nhận `CLOSING`. ai-service theo **V114**. Sửa ví dụ thành enum
   bốn giá trị; `SummarizeResponse` thêm `generatedAt` và `interactionId`.
2. **Sự kiện `crm.conversation.closed`:** java-core **chưa phát**. Đề xuất `outboxService.append(…,
   "ConversationClosed", "crm.conversation.closed", {conversation_id, closed_by, close_reason,
   closed_at, message_count})` trong `InboxService.changeStatus`, cùng `@Transactional`. **`closed_by`
   nên tuỳ chọn** — hội thoại do hệ thống tự đóng thì không có người đóng; worker không đọc trường này.
3. **Khoá phân vùng:** đặc tả UC026 ghi "khoá là mã hội thoại, 12 phân vùng", còn
   `docs/events/README.md` và `.claude/rules/kafka-events.md` ghi `tenant_id`. ai-service chạy đúng với
   cả hai (một bản tin là một hội thoại). Đề xuất giữ `tenant_id` theo quy ước chung và sửa câu trong
   đặc tả.
4. **Ba endpoint `/internal/*`** (mục 1–3) cùng chuỗi bảo mật nội bộ trong `SecurityConfig` — hiện mọi
   đường dẫn đều đòi JWT người dùng.
5. **Khoá ngoại V125 `engagement.contact_notes.conversation_id` đang NO ACTION** ⇒ xoá một hội thoại có
   ghi chú sẽ bị **CHẶN**. Cần `ON DELETE SET NULL (conversation_id)` — cùng loại lỗi V108 mà V132 đã
   sửa cho `leads`.
6. **Gateway** nên chặn `/ai/v1/ai/privacy/**` từ phía ngoài. Token ở mục 4 là lớp chặn thứ hai, không
   phải lớp duy nhất.
7. **Thêm mục 4 vào `ai-service-to-java-core.yaml`** khi Dev B đồng ý.
