# ADR-0033 — Xoá dữ liệu cá nhân phía AI: `contact_id` trên tài liệu, hội thoại do java-core gửi, chốt token nội bộ

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-09
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** đặc tả UC041 · kế hoạch Ngày 12 · Nghị định 13/2023/NĐ-CP · V214 ·
  [ADR-0002](0002-ai-service-khong-truy-cap-db-truc-tiep.md) ·
  [ADR-0016](0016-ten-role-runtime-va-cho-dat-nhan-ket-qua-lead.md) (không có `ai.lead_features`) ·
  [ADR-0022](0022-kho-tep-tai-lieu-object-storage-s3.md) (quyền S3 mở đúng lúc UC041) ·
  [ADR-0031](0031-nap-lai-bang-ban-bong.md) (bản bóng)

## Bối cảnh

Đặc tả UC041 chia việc như sau:

- **CRM** lo toàn bộ quy trình: tiếp nhận, **xác minh danh tính**, xem trước, thực thi trên schema
  Track A, lập biên bản.
- **AI** cung cấp `DELETE /v1/ai/privacy/contacts/{id}`: xoá mọi đoạn tri thức và bản ghi gắn với một
  khách.

Kế hoạch Ngày 12 thêm: xoá đặc trưng lead **qua API**; xoá hội thoại nguồn **không** kéo theo xoá cơ
hội tiềm năng; câu trả lời sinh **sau** khi xoá không còn trích dữ liệu đã xoá.

Khảo sát ngày 09/10 cho thấy:

- **Không bảng nào của schema `knowledge` liên kết tới khách.** Kho chỉ nhận tệp nhân viên tải lên.
  Master Plan §4.2 từng đặt `contact_id` trên `ai.chunks`, nhưng ADR-0015 đã đổi sang
  `knowledge.knowledge_*` và cột đó không đi theo.
- **`ai.ai_interactions` chỉ có `conversation_id`** — khoá liên làn, không có `contact_id`.
- **Gateway định tuyến `/ai/v1/**` cho MỌI JWT của tenant.** Không có chốt riêng thì một nhân viên bất
  kỳ gọi được endpoint xoá mà bỏ qua bước xác minh danh tính.
- **`sales.leads.source_conversation_id` đã là `ON DELETE SET NULL (source_conversation_id)`** (V132 của
  Dev B, kèm test `LeadIntegrationTest`). Ô "không xoá cơ hội" đã đúng ở tầng CSDL Track A.

## Quyết định

| Vấn đề | Chốt |
|---|---|
| Liên kết tài liệu ↔ khách | V214: `knowledge_documents.contact_id uuid NULL` + chỉ mục bộ phận `(tenant_id, contact_id) WHERE contact_id IS NOT NULL`. **Không** nhân bản xuống `knowledge_chunks` — đoạn đi theo tài liệu (`ON DELETE CASCADE`) |
| Gắn liên kết | `PATCH /v1/documents/{id}` (UC020) nhận thêm `contact_id` (`null` để gỡ). Bản bóng nạp lại chép theo |
| Xoá tài liệu | Xoá CỨNG (không `ARCHIVED`) mọi dòng mang `contact_id` **và mọi dòng cùng `file_path`** (bản cũ đã lưu trữ, bản bóng). Sau đó xoá tệp gốc trên S3 |
| Xoá lượt | Java-core gửi danh sách hội thoại của khách qua `?conversationId=…` (lặp lại được). Xoá `ai_interactions` của các hội thoại đó, kể cả lượt `SUMMARY`. `ai_feedback` và `ai_tool_calls` đi theo `CASCADE` |
| Đặc trưng lead | `DELETE /internal/contacts/{id}/lead-scores` của java-core qua `integrations/java_core/` — GIẢ tới khi Track A làm (ADR-0016: không có `ai.lead_features`) |
| Thứ tự | (1) một transaction CSDL rồi **commit** → (2) xoá tệp S3 → (3) java-core. Mỗi chặng là một mục `MucXoa` (`targetSchema`, `targetTable`, `action`, `status`, `affectedRows`) |
| Kết cục | `COMPLETED` khi mọi mục `DONE`; ngược lại `PARTIALLY_FAILED` với mã lỗi theo mục. Endpoint **luỹ đẳng**: gọi lại thì làm nốt phần hỏng |
| Ai được gọi | Header `X-Internal-Token` phải khớp `INTERNAL_API_TOKEN` (so thời gian hằng). Token rỗng thì endpoint **đóng hẳn** (403 `INTERNAL_ONLY`) |
| Giới hạn | Phản hồi kèm `note` nói rõ không vươn tới hệ thống ngoài nhận qua MCP, cũng không tới nhà cung cấp LLM (đặc tả UC041 bước 6) |

## Lập luận

- **`contact_id` trên tài liệu, không trên đoạn:** mọi đoạn của một tài liệu cùng thuộc một khách.
  Nhân bản xuống đoạn là ghi cùng một giá trị lên hàng nghìn dòng và phải giữ chúng khớp nhau.
- **Tính cả "dòng dõi" theo `file_path`:** sau nạp lại (ADR-0031), bản cũ `ARCHIVED` vẫn giữ tiêu đề,
  mô tả và trỏ cùng tệp. `contact_id` có thể chỉ được gắn lên bản mới sau khi bản cũ đã lưu trữ — lọc
  thuần theo `contact_id` sẽ bỏ sót. Test `test_xoa_ca_dong_doi_cung_tep` + 2 đột biến khoá điều này.
- **Hội thoại do java-core gửi, không thêm `contact_id` vào `ai_interactions`:** chỉ java-core biết khách
  nào có hội thoại nào (`engagement.conversations.contact_id`). Thêm cột thì phải sửa `ChatRequest`,
  `AiChatClient` của java-core, và vẫn không phủ được các lượt cũ đã ghi.
- **Commit CSDL trước khi chạm hệ thống ngoài:** truy hồi ngừng thấy dữ liệu ngay tại commit, nên câu
  trả lời sinh sau đó không thể trích nó, dù S3 hay java-core đang sập. Tệp S3 còn sót thì không dòng
  nào trỏ tới, không truy hồi được, và lần gọi lại sẽ xoá nốt.
- **Token nội bộ thay vì kiểm vai trò:** xoá là thao tác không đảo ngược, và đặc tả gọi bước xác minh
  danh tính là "chỗ dễ bỏ sót nhất". Kiểm `TENANT_ADMIN` ở ai-service vẫn để một quản trị viên xoá được
  mà không qua quy trình. Token nội bộ đảm bảo **chỉ java-core** gọi được, tức là chỉ sau khi quy trình
  bên CRM đã xác minh. Hợp đồng `java-core-to-ai-service.yaml` dự kiến JWT nội bộ RS256; token dùng
  chung là bước tạm cho tới lúc đó.
- **`ai_tool_calls` xoá theo `CASCADE` dù `ai_app` bị thu hồi DELETE:** hành động xoá lan của khoá ngoại
  chạy bằng quyền chủ bảng (đã đo, có test). Nhóm MCP đã hoãn nên bảng đang rỗng. Khi bật lại thì nên
  cân nhắc ẩn danh hoá `arguments` thay vì xoá bằng chứng kiểm toán.

## Số đo (09/10)

- **Test:** 8 ca tích hợp + 12 ca HTTP. Kiểm ngược 7/7 đột biến của UC041 làm test đỏ (bỏ lọc
  `contact_id`, bỏ dòng dõi, bản bóng không chép, bỏ lọc `conversation_id`, bỏ kiểm token…).
- **Minh chứng trên hạ tầng thật** (ai-embed bge-m3 INT8, RustFS, Postgres, Gemini), câu hỏi "máy
  lạnh được bảo trì mấy lần mỗi năm":
  - **trước khi xoá:** trích 2 đoạn, 1 đoạn của hợp đồng riêng của khách ("4 lần mỗi năm");
  - **sau khi xoá:** 1 đoạn, 0 đoạn của khách;
  - biên bản: 1 tài liệu, 1 đoạn, 3 lượt, 2 đánh giá, 1 tệp S3, 3 dòng lead (java-core giả);
  - không token thì 403.

## Đánh đổi và rủi ro còn mở

- **Tài liệu riêng của một khách nằm trong kho CHUNG thì bị trích cho khách khác.** Minh chứng cho thấy
  hợp đồng của khách X được trích để trả lời câu hỏi chung của bất kỳ ai. `contact_id` mới chỉ phục vụ
  việc xoá, chưa chặn truy hồi. Hướng sửa: truy hồi loại tài liệu có `contact_id` khác khách đang hỏi.
  Ghi vào bài kiểm thử bảo mật Ngày 17 (bề mặt T6).
- **Số tổng hợp giảm theo.** `GET /v1/ai/quality` tính trực tiếp từ `ai_interactions`, nên xoá lượt làm
  thay đổi tỉ lệ của các kỳ đã qua. Track B không có bảng tổng hợp nào để "giữ ở dạng tổng hợp".
- **`ai.processed_events` giữ `aggregate_id`** (id hội thoại) — chỉ là định danh, không phải nội dung.
  `ai_app` không có quyền DELETE trên bảng này.
- **Nhà cung cấp LLM đã nhận lời nhắc** (đã che SĐT/email/CCCD) — không xoá được ở phía họ. Điều này
  nằm trong `note` của phản hồi.

## Hệ quả

- **Lược đồ:** V214.
- **Mã:**
  - `document_repository.xoa_tai_lieu_theo_khach`;
  - `interaction_repository.xoa_theo_hoi_thoai`;
  - `object_storage.xoa`;
  - `service.forget_contact`;
  - `api/v1/endpoints/rieng_tu.py`.
- **Giao ước:** nháp [`uc026-uc041-tom-tat-va-xoa-du-lieu.md`](../contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md).
- **Track A còn nợ:**
  - endpoint xoá điểm lead theo contact;
  - gửi `X-Internal-Token` và danh sách hội thoại khi gọi ai-service;
  - gateway chặn `/ai/v1/ai/privacy/**` từ bên ngoài;
  - **khoá ngoại V125 `contact_notes.conversation_id` đang NO ACTION nên sẽ CHẶN xoá hội thoại có ghi
    chú** — cần `SET NULL` (cùng lỗi V108 mà V132 đã sửa cho `leads`).
- **Hạ tầng:** ai-service cần quyền `s3:DeleteObject` trên bucket (dev dùng tài khoản gốc — ADR-0022
  mục 5).
- **Báo cáo:** chương 3 (phạm vi xoá, token nội bộ); chương 5 (trích dẫn trước/sau).
