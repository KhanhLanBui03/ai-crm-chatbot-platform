# Hợp đồng UC025 + UC027 — từ chối có lý do, đánh giá lượt trả lời, khoảng trống tri thức (nháp 08/10/2026)

⚠️ Nháp phía Track B. Nguồn sự thật vẫn là `docs/openapi/ai-service-to-java-core.yaml` và
`docs/openapi/dashboard-api.yaml` — **chưa sửa**, chờ Dev B xác nhận (mục 6). Mọi thay đổi dưới đây
là **THÊM**: không trường nào đổi tên, đổi kiểu hay bị bỏ. Code ai-service đã chạy theo nháp này.

Căn cứ: đặc tả UC025, UC027 (`docs/Dac-ta-UseCase-Module-AI.docx`), ADR-0029, ADR-0030, nháp
[UC023](uc023-chat-tra-loi.md) (hai trường `degraded`, `latency_breakdown`).

## 1. `ChatResponse` — thêm hai trường

| Trường | Kiểu | Nghĩa |
|---|---|---|
| `interaction_id` | uuid | Khoá dòng `ai.ai_interactions` của lượt này. java-core **giữ lại** (ví dụ trong `metadata` của tin nhắn BOT) để gửi kèm khi khách/nhân viên đánh giá. Có thể trỏ vào dòng không tồn tại nếu ai-service ghi lượt hỏng — khi đó đánh giá nhận 404, không ảnh hưởng gì khác |
| `refusal_reason` | enum \| null | Một trong `NOT_COVERED` · `OUT_OF_SCOPE_DATA` · `LOW_CONFIDENCE` · `SAFETY_PROBE` khi `refused = true`; `null` khi trả lời được |

```yaml
        interaction_id: { type: string, format: uuid }
        refusal_reason:
          type: [string, 'null']
          enum: [NOT_COVERED, OUT_OF_SCOPE_DATA, LOW_CONFIDENCE, SAFETY_PROBE, null]
```

### Ngữ nghĩa đã đổi: `handoff` ở nhánh `route = RAG`

Trước 08/10, `handoff = true` chỉ ở nhánh `HANDOFF`/`TOOL_CALL`. Từ Ngày 10, nhánh `RAG` cũng trả
`handoff = true` **kèm** `refused = true` trong hai trường hợp (đặc tả UC025 bước 5):

1. `refusal_reason = OUT_OF_SCOPE_DATA` — câu hỏi về một đơn hàng / phiếu bảo hành / tài khoản /
   lịch hẹn cụ thể; tài liệu không trả lời được, cần người tra hệ thống.
2. Lượt từ chối thứ 2 liên tiếp trong cùng hội thoại (`NOT_COVERED`/`LOW_CONFIDENCE`) — luồng phụ 3.3.

`WidgetService` hiện đã xử lý đúng tổ hợp này (`r.refused() ? "NO_GROUNDING" : "CUSTOMER_REQUEST"`)
⇒ **java-core không phải sửa gì** để chạy; chỉ cần biết để giải thích được lý do chuyển giao.

`SAFETY_PROBE` không bao giờ đi kèm `handoff = true`, và `answer` khi đó cố ý không nói lý do.

## 2. `FeedbackRequest` — thêm ba trường

Hợp đồng hiện có `interaction_id`, `rating` (1 / −1), `comment`, `corrected_answer`. Bảng
`ai.ai_feedback` (V204) bắt buộc thêm ba thứ mà hợp đồng chưa có:

| Trường | Kiểu | Bắt buộc | Nghĩa |
|---|---|---|---|
| `reason_code` | enum | khi `rating = -1` | `WRONG_INFO` · `IRRELEVANT` · `INCOMPLETE` · `BAD_TONE`. Khen mà gửi lý do ⇒ 422 |
| `rater_type` | enum | không, mặc định `CUSTOMER` | `CUSTOMER` (widget) · `AGENT` (hộp thư). `AUTO_EVAL` **không** nhận từ API — chỉ bộ chấm trong ai-service ghi |
| `rater_user_id` | uuid | khi `rater_type = AGENT` | java-core lấy từ JWT nhân viên. Khách thì **không** gửi |

`corrected_answer` chỉ nhân viên được gửi. Body có `tenant_id` ⇒ 422 (tenant chỉ từ `X-Tenant-Id`).

```yaml
    FeedbackRequest:
      type: object
      required: [rating]
      additionalProperties: false
      properties:
        interaction_id: { type: string, format: uuid }
        rating: { type: integer, enum: [1, -1] }
        reason_code: { type: string, enum: [WRONG_INFO, IRRELEVANT, INCOMPLETE, BAD_TONE] }
        rater_type: { type: string, enum: [CUSTOMER, AGENT], default: CUSTOMER }
        rater_user_id: { type: string, format: uuid }
        comment: { type: string, maxLength: 2000 }
        corrected_answer: { type: string, maxLength: 4000 }
```

### Phản hồi 200 — thêm vào `ActionSuccessResponse`

```json
{ "success": true, "message": "Đã cập nhật đánh giá", "feedback_id": "…", "created": false }
```

`created = false`: phía này đã đánh giá lượt này, dòng cũ được **cập nhật** (UC027 luồng phụ 2.1).
Đặc tả liệt kê `409 DUPLICATE_FEEDBACK` nhưng ghi rõ "chuyển sang cập nhật thay vì báo lỗi" — ai-service
không bao giờ trả 409 ở đây.

### Mã lỗi — thân luôn `{code, message}`

| HTTP | `code` | Khi nào |
|---|---|---|
| 401 | `TENANT_CONTEXT_MISSING` | thiếu `X-Tenant-Id` |
| 404 | `INTERACTION_NOT_FOUND` | lượt không có **hoặc thuộc tenant khác** — cố ý không phân biệt |
| 422 | `REASON_REQUIRED` | `rating = -1` mà thiếu `reason_code` |
| 422 | `INVALID_RATER` | nhân viên thiếu `rater_user_id`; khách kèm `rater_user_id` hoặc `corrected_answer` |
| 422 | `INVALID_FEEDBACK` | thiếu `interaction_id`; đường dẫn và body mâu thuẫn; khen kèm lý do; trường lạ (`tenant_id`…) |

Đặc tả còn `403 FORBIDDEN` (không có quyền xem lượt) — thuộc java-core (quyền theo vai trò), ai-service
không biết vai trò người dùng.

Hai đường dẫn đều chạy: `POST /v1/ai/feedback` (id trong body) và
`POST /v1/ai-interactions/{interactionId}/feedback` (id trên đường dẫn).

## 3. `GET /v1/knowledge-gaps` — thêm tham số và trường

Hợp đồng hiện trả mảng `KnowledgeGapItem {query_text, unanswered_count, last_occurred_at}`. Đề xuất
trả **trang** và thêm đủ trường mà `KhoangTrongTriThuc` của `dashboard-api.yaml` cần — java-core chỉ
đổi tên snake_case → camelCase, không tính lại gì:

| Tham số query | Mặc định | |
|---|---|---|
| `gap_type` | — | `NOT_COVERED` · `OUT_OF_SCOPE_DATA` · `LOW_CONFIDENCE` |
| `page` / `size` | 0 / 20 | `size` ≤ 100 |
| `so_ngay` | 30 | cửa sổ nhìn lại — cách một khoảng trống "tự biến mất" khi tài liệu mới đã nạp |

```json
{ "items": [ {
    "id": "uuid5 tất định",
    "query_text": "SHOP CÓ BÁN MÁY RỬA BÁT KHÔNG",
    "gap_type": "NOT_COVERED",
    "unanswered_count": 3,
    "distinct_conversation_count": 2,
    "first_occurred_at": "…", "last_occurred_at": "…" } ],
  "total": 3, "page": 0, "size": 20 }
```

- `distinct_conversation_count` ↔ `distinctContactCount`: `ai_interactions` không có `contact_id`
  (liên làn), nên "khách khác nhau" xấp xỉ bằng **hội thoại** khác nhau. java-core có thể tính đúng
  theo liên hệ nếu cần — ghi rõ trên giao diện.
- Sắp theo `distinct_conversation_count` giảm dần, rồi `unanswered_count` — đặc tả UC025 luồng phụ 8.1.
  `dashboard-api.yaml` ghi "sắp theo `occurrenceCount`" — **lệch đặc tả**, đề xuất sửa theo đặc tả.
- `SAFETY_PROBE` không phải khoảng trống tri thức (thêm tài liệu không lấp được) — không bao giờ có ở đây.
- `priority` của dashboard là hình chiếu theo bậc của `distinctContactCount` — java-core tính.

## 4. `GET /v1/ai/quality` — MỚI

UC027 bước 7: bảy tín hiệu chất lượng trong cửa sổ `[tu, den)` (mặc định 7 ngày gần nhất), nguồn cho
báo cáo hiệu quả AI (UC039). **Mọi tỉ lệ trả kèm tử số và mẫu số** để không ai chia nhầm:

```json
{
  "tu": "…", "den": "…", "so_luot": 10, "so_luot_loi": 1,
  "ty_le_tu_choi":       { "tu_so": 3, "mau_so": 10, "gia_tri": 0.3 },
  "ty_le_suy_giam":      { "tu_so": 1, "mau_so": 10, "gia_tri": 0.1 },
  "ty_le_chuyen_giao":   { "tu_so": 1, "mau_so": 10, "gia_tri": 0.1 },
  "do_phu_trich_dan":    { "tu_so": 3, "mau_so": 4,  "gia_tri": 0.75 },
  "ty_le_khong_goi_llm": { "tu_so": 6, "mau_so": 10, "gia_tri": 0.6 },
  "groundedness_trung_binh": 0.91,
  "tu_choi_theo_ly_do": { "NOT_COVERED": 3 },
  "danh_gia": [
    { "rater_type": "CUSTOMER", "ty_le_tich_cuc": { "tu_so": 1, "mau_so": 2, "gia_tri": 0.5 },
      "che_theo_ly_do": { "WRONG_INFO": 1 } }
  ]
}
```

- `ty_le_tich_cuc.mau_so` = số lượt **có** đánh giá từ phía đó — không phải tổng số lượt (đặc tả UC027).
- `do_phu_trich_dan.mau_so` = lượt RAG trả lời bằng LLM, **không gồm** lượt suy giảm.
- Tên trường tiếng Việt không dấu theo quy ước định danh của repo; đổi sang tiếng Anh nếu Dev B muốn
  thống nhất với phần còn lại của hợp đồng — báo trước khi java-core sinh type.

## 5. Không đổi

`ai.turn.completed` (UC022 bước 10, UC039) vẫn chưa phát — việc của UC039. Tín hiệu đã nằm trong
`ai.ai_interactions` (V212 thêm `llm_called`, `is_degraded`, `is_handoff`), nên sự kiện khi có chỉ cần
chép cột, không phải tính lại.

## 6. Cần Dev B xác nhận

1. Vá `ai-service-to-java-core.yaml` theo mục 1–4?
2. `AiChatClient` có lưu `interaction_id` vào `metadata` của tin nhắn BOT không? Không lưu thì widget
   không gửi được đánh giá (UC027 bước 1–2).
3. Widget/hộp thư: hai nút đánh giá + hộp chọn 4 lý do + ô câu sửa (nhân viên) — phần CRM của UC027.
4. Thứ tự sắp của SCR034: theo đặc tả (số khách khác nhau) hay theo `dashboard-api.yaml` hiện tại?
