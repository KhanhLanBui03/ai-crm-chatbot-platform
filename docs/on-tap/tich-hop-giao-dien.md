# Ôn tập đợt tích hợp giao diện — 8 UC của Dev A qua bốn tầng

> Viết 14/11/2026, cuối GD4. Một bản cho cả đợt GD1–GD4 (luật 8 của kế hoạch). Kế hoạch:
> [`docs/plan/ke-hoach-tich-hop-giao-dien.md`](../plan/ke-hoach-tich-hop-giao-dien.md) · minh chứng:
> [`docs/report/tich-hop-giao-dien-2026-10.md`](../report/tich-hop-giao-dien-2026-10.md) · hợp đồng đã đổi:
> [`docs/contracts/giao-dien-gd.md`](../contracts/giao-dien-gd.md). Quyết định nền: ADR-0002 (AI không chạm bảng
> CRM), ADR-0023 (hạn mức), ADR-0031 (bản bóng khi nạp lại). Gói đổi giao ước của đợt sẽ gom vào **ADR-0037**
> (chưa viết).

## 1. Bức tranh — bốn tầng, hai chiều

```
 web-dashboard :5173 ─┐                                         (nhân viên, JWT)
 web-widget    :5174 ─┤  chỉ gọi /api/v1/**
                      ▼
               gateway :8080      xác thực JWT RS256, gắn X-Tenant-Id từ JWT, X-Trace-Id
                      │           /ai/v1/ai/privacy/** và /ai/v1/ai/summarize: denyAll
                      ▼
               java-core :8081    MẶT TIỀN: quyền (TENANT_ADMIN), hạn mức, kiểm toán, outbox
                      │  client/AiServiceClient (get/post/patch/delete chung)
                      │    → gương DTO theo nhóm: AiKnowledgeClient · AiInteractionClient
                      │                          AiSummaryClient · AiPrivacyClient
                      │    → AiServiceErrors (bảng dịch lỗi)
                      ▼
               ai-service :8000   /v1/** — RLS theo X-Tenant-Id, chỉ schema ai/knowledge
                      │
                      └──► chiều NGƯỢC: GET/PATCH/DELETE /internal/** của java-core
                           (X-Internal-Token + X-Tenant-Id; không JWT)
```

Ba câu nắm cả đợt:

1. **Dashboard không bao giờ gọi thẳng ai-service.** java-core có JWT đã xác thực, quyền, hạn mức gói, nhật ký kiểm
   toán. ai-service không có và không được có những thứ đó (ADR-0002).
2. **java-core không đọc schema `ai`/`knowledge`.** Muốn số liệu AI thì hỏi ai-service qua `client/`. Muốn ghi vào
   bảng CRM thì ai-service gọi ngược `/internal/**`, không bao giờ nối thẳng CSDL.
3. **`tenant_id` chỉ có một nguồn ở mỗi chiều.** Chiều xuôi lấy từ JWT (`SecurityUtils.getCurrentTenantId()`). Chiều
   ngược lấy từ `X-Tenant-Id` kèm token nội bộ. Không bao giờ lấy từ body, query hay path.

## 2. Lớp chuyển tiếp chung — vì sao một lớp chứ không tám

Mỗi UC tự viết `RestClient` riêng thì có tám cách gắn header, tám cách đọc JSON, tám cách dịch lỗi. Đợt này dựng
**một** lớp ở GD1 rồi dùng suốt bốn GD.

| Thành phần | File | Việc |
|---|---|---|
| Lời gọi chung | [`client/AiServiceClient.java`](../../java-core/src/main/java/com/thesis/crm/client/AiServiceClient.java) | `get/post/patch/delete` trên `RestClient`; mọi lời gọi gắn `X-Tenant-Id` (từ JWT) và `X-Trace-Id`; đọc bằng `ObjectMapper` `SNAKE_CASE` |
| Gương DTO | `AiKnowledgeClient` (GD1) · `AiInteractionClient` (GD2) · `AiSummaryClient` + `AiPrivacyClient` (GD3) | record Java khớp **hình ai-service**; mapper đổi sang record khớp **`dashboard-api.yaml`** |
| Dịch lỗi | [`client/AiServiceErrors.java`](../../java-core/src/main/java/com/thesis/crm/client/AiServiceErrors.java) | bảng dưới |

| ai-service trả | java-core trả cho dashboard | Lý do |
|---|---|---|
| 404 | 404, giữ `code` (`DOCUMENT_NOT_FOUND`, `INTERACTION_NOT_FOUND`) | RLS làm dòng của tenant khác vô hình → 404 cho cả "không có" lẫn "của người khác", không dò được id |
| 409 · 422 | giữ mã và `code` (`DOCUMENT_BUSY`, `INVALID_METADATA`, `REASON_REQUIRED`…) | lỗi nghiệp vụ người dùng sửa được |
| 401 · 403 | **500** | ai-service từ chối java-core = lỗi cấu hình phía mình (token, header), không phải lỗi người dùng |
| 5xx · hết giờ · không nối được | **502 `AI_SERVICE_UNAVAILABLE`** | đặc tả UC020; dashboard hiện "Dịch vụ AI tạm thời không phản hồi…" |

Phân trang: ai-service trả `items, page, size, total` → java-core trả `PageResponse` với `totalItems ← total`,
`totalPages = ceil(total / size)`.

## 3. Luồng từng UC qua bốn tầng

| UC | Giao diện (route · tệp) | java-core `/api/v1/**` | ai-service `/v1/**` | Ghi nhớ |
|---|---|---|---|---|
| **018** Tải lên | `/tri-thuc` · `UploadDocumentDialog` | `POST /documents` → khoá hạn mức → ghi tệp vào RustFS → gọi ai-service → cộng hạn mức + outbox `crm.kb.document.uploaded` **cùng transaction** | `POST /documents` tạo dòng `PENDING` | java-core không đọc nội dung tệp; ai-service không ghi schema Track A. Ranh giới đặt ở **URI tệp**. ai-service từ chối thì xoá tệp vừa ghi |
| **019** Nạp | `/tri-thuc/tai-lieu/{id}/tien-do` · `IngestionProgressPage`; `/tri-thuc/tien-do` | `GET /ingestion-jobs[/{id}]` (REST, không tiêu thụ sự kiện) | worker `ingestion-cg`: trích → chia đoạn → nhúng (ai-embed) → lập chỉ mục; `GET /ingestion-jobs` | màn tự ngừng hỏi lại khi `DONE`/`FAILED`; nạp lại hiện `trigger = REINDEX` |
| **020** Quản lý kho | `/tri-thuc` · `DocumentsPage` · `DocumentChunksPage` · `EditDocumentDialog` · `ArchiveDocumentDialog` | `GET/PATCH/DELETE /documents/{id}`, `POST …/reindex`, `GET …/chunks`; ghi `DOCUMENT_UPDATED/REINDEXED/ARCHIVED`; gỡ thì trả hạn mức | `kho.py` — sửa, nạp lại **bản bóng** (id mới), gỡ `ARCHIVED` + xoá đoạn, báo `quotaReleased` | nạp lại sang id mới; bản cũ phục vụ tới khi bản bóng `READY` (ADR-0031) |
| **023** Trả lời có trích dẫn | widget `main.ts`/`ui.ts`; hộp thư `MessageThread` | widget: `POST /widget/messages` → `WidgetService` → `AiChatClient`; lưu tin BOT kèm `ai_interaction_id`, `metadata.refusalReason`, `degraded` | `POST /ai/chat`: router (ai-classify) → truy hồi lai (vector + từ khoá, RRF) → Gemini → trích dẫn | đoạn trích ẩn tới khi bấm nguồn; "Xin chào" đi đường nhanh, không gọi LLM |
| **025** Từ chối + khoảng trống | widget; `/tri-thuc/khoang-trong` · `KnowledgeGapsPage` | `GET /knowledge-gaps` (sắp theo số khách) | lượt từ chối ghi `refusal_reason`; khoảng trống là **truy vấn gộp** trên lượt từ chối 30 ngày | hỏi lại lần hai cùng hội thoại → chuyển nhân viên; mã đơn hàng → luật, chuyển ngay |
| **027** Đánh giá | widget 👍/👎; hộp thư `DanhGiaDialog`; `/tac-tu-ai/luot-xu-ly`; `/phan-tich/hieu-qua-ai` | khách: `POST /widget/messages/{id}/feedback` (`rater_type = CUSTOMER` do máy chủ đặt); nhân viên: `POST /ai-interactions/{id}/feedback` (`AGENT` + người từ JWT; thiếu lý do → 422 ngay tại java-core); `GET /ai-interactions` | `feedback.py` — mỗi phía một dòng cho mỗi lượt, đánh giá lại thì cập nhật; `/ai/quality` cho ô tích cực | tỉ lệ tích cực = tổng 👍 ÷ tổng lượt **có** đánh giá, cộng tử với tử |
| **026** Tóm tắt | hộp thư `ContextPanel` · `KhoiTomTat` | `changeStatus` → outbox `crm.conversation.closed`; `context()` trả `summary`; `POST /conversations/{id}/summary` (MANUAL) | worker `summarizer-cg` → `GET /internal/…/messages` → Gemini t=0 → `PATCH /internal/…/summary`; `POST /ai/summarize` cho MANUAL | `CLOSING` + `MANUAL` (Q1); ghi **không lùi**; hội thoại < 2 tin khách thì bỏ qua, không gọi LLM |
| **041** Xoá dữ liệu cá nhân | `/kiem-toan/yeu-cau-xoa` · `CreateErasureDialog` · `ErasureProgressPage` · `ErasurePreviewPage` · `ExecuteErasureDialog` | `platform/erasure/` — tạo · xác minh · xem trước · thực thi **đồng bộ** ba chặng; ghi `ERASURE_*`; trả hạn mức | `DELETE /ai/privacy/contacts/{id}` (cần `X-Internal-Token`) → gọi ngược `DELETE /internal/contacts/{id}/lead-scores` | `ck_erasure_gate` chặn thực thi khi chưa xác minh, cả ở ứng dụng lẫn CSDL; chạy lại chỉ phần dở |

## 4. Ánh xạ trường — chỗ hay hỏi

| ai-service (snake) | dashboard (camel) | Chỗ đổi |
|---|---|---|
| `total` | `totalItems` + `totalPages` | `PageResponse.of` |
| `intent` | `intentLabel` | `AiInteractionMapper.luot` |
| `latency_breakdown` {`embed_ms`, `retrieve_ms`, `guard_ms`, `postguard_ms`, …} | `latencyBreakdown` {`retrieve`, `rerank`, `generate`, `guard`, …} | `AiInteractionMapper.chang` — gộp chặng; chặng không chạy thì **không có khoá** |
| `feedback[].rater_type` · `rater_user_id` | `feedbacks[].ratedByType` · `ratedByUserId` · `ratedByName` | tên tra ở `platform.users`, **chỉ** khi có `raterUserId` (chỗ vỡ 2 của GD4) |
| `status != "SUCCESS"` | `errorCode` | thành công thì `null` |
| `distinct_conversation_count` | `distinctContactCount` + `priority` (1/2/3) | xấp xỉ: `ai_interactions` không có `contact_id` (giảm độ sâu UC025) |
| `citations[].document_title` (null) | `"Tài liệu không tên"` | tài liệu đã gỡ vẫn hiện được trích dẫn cũ |
| `ErasureResult.releasedDocuments/releasedStorageBytes` | hạn mức được trả | ai-service báo số, java-core **không tự suy** |

## 5. "Phải giải thích được" — gộp GD1–GD4

**Kiến trúc**

- **Vì sao dashboard không gọi thẳng ai-service.** java-core là chỗ có JWT đã xác thực, quyền `TENANT_ADMIN`, hạn
  mức gói và nhật ký kiểm toán. ai-service không có và không được có ba thứ đó (ADR-0002, ADR-0014). Đi thẳng thì
  tenant phải lấy từ trình duyệt.
- **Vì sao ai-service ghi tóm tắt qua API chứ không ghi thẳng.** `ai_app` không có quyền trên schema `engagement`
  (ADR-0002, V206). Đó là ranh giới quyền: mô hình bị tiêm chỉ thị cũng chỉ ghi được đúng năm cột tóm tắt của hội
  thoại thuộc tenant trong `X-Tenant-Id`, qua một endpoint có token. Nó không chạm được các bảng nghiệp vụ khác.
- **Vì sao tài liệu của tenant khác trả 404 chứ không 403.** RLS làm dòng đó vô hình. Trả 403 là xác nhận id có tồn
  tại ở đâu đó, tức là dò được. Trả 404 cho cả hai trường hợp đúng với đặc tả UC020.

**Kho tri thức**

- **Vì sao nạp lại đổi `id` mà kho không trống giây nào.** Bản bóng là dòng mới (version kế tiếp, cùng tệp). Bản cũ
  vẫn `READY` và vẫn được truy hồi. Lúc bản bóng `READY`, ai-service xoá đoạn cũ và chuyển bản cũ sang `ARCHIVED`
  **trong cùng transaction**, nên người đọc chỉ thấy trạng thái trước hoặc trạng thái sau (ADR-0031).
- **Vì sao tải lại cùng nội dung dưới tên khác vẫn được nhận** (GD4). Đặc tả UC018 7.1 chỉ coi trùng theo cặp
  `(tenant_id, title)`: trùng tên thì tăng version. Chặn trùng nội dung sẽ chặn luôn trường hợp hợp lệ, ví dụ cùng
  bảng giá cho hai chi nhánh với hai tiêu đề.

**Chat và đánh giá**

- **`groundedness` khác `retrieval_top_score` ở đâu.** Điểm truy hồi đo độ liên quan giữa đoạn và câu hỏi, đo
  **trước** khi sinh. Bám nguồn đo câu trả lời có nằm trong đoạn không, đo **sau** khi sinh. Truy hồi 0,76 mà bám
  nguồn 0,50 là chuyện thường: đoạn đúng, câu diễn đạt lại. Vì groundedness là phép đo từ vựng nên cổng huỷ đang tắt
  (ADR-0029), điểm này chỉ để theo dõi.
- **Vì sao khoảng trống tri thức không có nút "đã xử lý".** Nó là truy vấn gộp trên lượt từ chối, không phải bảng có
  trạng thái. Bổ sung tài liệu thì lượt từ chối thôi phát sinh và dòng tự rơi khỏi cửa sổ 30 ngày. Nút "đã xử lý"
  chỉ giấu dòng mà không sửa gì trong kho.
- **Vì sao tỉ lệ tích cực chia cho số lượt CÓ đánh giá.** Phần lớn lượt không ai bấm. Chia cho tổng lượt thì đo mức
  sẵn lòng bấm nút chứ không đo chất lượng. Cộng tử với tử, mẫu với mẫu của hai phía (không lấy trung bình hai tỉ
  lệ), và lấy từ `ai.ai_feedback` vì đánh giá đến **sau** sự kiện lượt.

**Tóm tắt và xoá**

- **Vì sao ẩn danh danh bạ thay vì xoá vật lý.** Xoá dòng `contacts` kéo sập các tham chiếu lịch sử (deal, lead, hội
  thoại) mà nghĩa vụ kế toán và kiểm toán vẫn cần. Ẩn danh bỏ mọi trường quy về cá nhân nhưng giữ quan hệ nghiệp vụ.
- **Vì sao gọi ai-service NGOÀI transaction của java-core.** Giữa lượt xoá, ai-service gọi ngược
  `DELETE /internal/contacts/{id}/lead-scores`. Giữ transaction (và khoá dòng) quanh lời gọi đó là tự khoá mình. Lượt
  bấm thứ hai bị chặn bằng trạng thái `IN_PROGRESS` đã commit trước. Hỏng giữa chừng thì tiến độ từng bảng cho biết
  phần nào cần chạy lại.

**Từ buổi diễn tập GD4**

- **Vì sao diễn tập trên tenant mới.** "Kho trống → đầy đủ" mới là kịch bản demo thật. Tenant mới còn kiểm thêm một
  đường chưa ai đi: tenant vừa đăng ký có hạn mức, thuê bao dùng thử và kênh widget từ con số 0.
- **Vì sao lỗi `ai-interactions` 500 không lộ ở GD2.** Lỗi chỉ xảy ra khi trang có đánh giá của khách mà **không có**
  đánh giá nào của nhân viên (`Map.of().get(null)` ném NPE). GD2 mở hội thoại sau khi nhân viên đã chê. Đi đúng thứ tự
  người dùng thật mới lộ ra — đó là giá trị của một lượt "một lèo".
- **Vì sao lỗi đua phiên widget ảnh hưởng UC041.** Quyền xoá đi theo danh bạ. Một người bị tách thành hai danh bạ
  thì một yêu cầu xoá chỉ phủ một nửa. Nối danh tính khách phải đúng **trước** mọi việc khác trong chuỗi chăm sóc.

## 6. Câu phản biện kiểu hội đồng

1. *"java-core chỉ chuyển tiếp, sao không cho dashboard gọi thẳng `/ai/v1/**` qua gateway cho nhanh?"* — Gateway chỉ
   xác thực JWT. Quyền theo vai trò, hạn mức và kiểm toán nằm ở java-core. Chặng chuyển tiếp chưa đo tách riêng,
   nhưng trọn vòng đã nhỏ (GD4: `PATCH` 86 ms, `DELETE` 134–251 ms qua cả bốn tầng), không đáng gì so với lỗ hổng
   phải vá nếu đi thẳng.
2. *"Token nội bộ dùng chung hai chiều — lộ một là lộ cả hai?"* — Đúng, và đã ghi là đánh đổi (Q3, sẽ vào ADR-0037).
   Bù lại: token chỉ mở `/internal/**` (không phải mọi API), tenant vẫn bị RLS chặn ở từng truy vấn, và gateway
   `denyAll` hai đường nội bộ của ai-service nên token không dùng được từ ngoài.
3. *"Thực thi xoá đồng bộ — 500 hội thoại thì treo trình duyệt?"* — Đo GD4: 14 bảng mất 0,31 s. Có trần 500 hội thoại
   mỗi lượt gửi ai-service; vượt thì `PARTIALLY_FAILED` và chạy lại phần dở. Bất đồng bộ là bước tiếp theo khi có số
   liệu khách thật.
4. *"Sao tin `SYSTEM` không bị che khi xoá?"* — Nó là câu mẫu của hệ thống ("Cuộc trò chuyện đã kết thúc…"), không
   chứa dữ liệu khách. Tin của bot và nhân viên thì **bị** che, vì câu trả lời hay nhắc lại tên, số điện thoại.

## 7. Số đo của buổi diễn tập GD4 (máy dev, một người dùng, rerank tắt — không phải cổng)

| Thao tác | Thời gian thấy được |
|---|---|
| Tải lên → toast "Đã nhận" | 0,4–1,4 s |
| Nạp tới `DONE` (Markdown 1–4 đoạn) | 2,3–4,9 s |
| Nạp lại → bản bóng `READY` | 30,9 s (bộ quét ≤ 60 s chiếm phần lớn) |
| Câu chào (đường nhanh) | 1,0 s |
| Câu có trích dẫn (Gemini) | 1,4–1,7 s; giám sát: truy hồi 397 ms |
| Từ chối (Gemini) · luật mã đơn | 1,2–1,3 s · 0,21 s |
| Tóm tắt `CLOSING` hiện ở cột phải | 6,0 s sau khi bấm "Đánh dấu xong" |
| "Tóm tắt lại" | 4,1 s |
| Thực thi xoá 14 bảng | 0,31 s |

## 8. Phần AI làm — khai trung thực

Cả đợt GD1–GD4 do Claude làm theo phân công của người dùng (24/10: "8 UC AI là việc của Dev A từ dashboard tới
ai-service"): viết code ba tầng, test, bật stack, đi cảnh bằng Playwright, ghi minh chứng. Người dùng chốt các điểm
Q1–Q6, cách kiểm (không chụp ảnh), tenant diễn tập, và tự chạy mọi lệnh git. Số liệu trong tài liệu này lấy từ lượt
chạy thật ngày 14/11, không ước lượng.

## 9. Ba câu tự kiểm

1. Khách bấm 👎 ở widget. Hãy kể đường đi của lượt đánh giá đó qua bốn tầng, và chỉ ra tầng nào đặt
   `rater_type = CUSTOMER`. Vì sao không để widget gửi trường này?
2. Bấm "Nạp lại tài liệu" lúc bản bóng trước còn `PENDING` thì nhận được gì, ở tầng nào chặn? Vì sao gỡ bản cũ lúc
   đó cũng bị chặn?
3. ai-service đã xoá xong phía AI nhưng java-core mất phản hồi trước chặng ba. Lượt "Chạy lại phần còn lại" sẽ làm
   gì với các mục `DONE`, và hạn mức có bị trả hai lần không?
