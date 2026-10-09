# ADR-0032 — Tóm tắt hội thoại: nhiệt độ 0 ghim cứng, phiên bản model là ảnh chụp, PATCH rồi mới đánh dấu xong

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-09
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** đặc tả UC026 (luồng phụ 1.1, 1.2, 2.1, 3.1, 4.1) · kế hoạch Ngày 12 ·
  [ADR-0002](0002-ai-service-khong-truy-cap-db-truc-tiep.md) (ghi qua API) ·
  [ADR-0024](0024-nap-tai-lieu-commit-theo-chang-chong-trung-va-quet-job-ket.md) (chống trùng, DLQ) ·
  [ADR-0028](0028-llm-gemini-flash-lite-client-trung-lap.md) (client LLM, bậc miễn phí)

## Bối cảnh

UC026 sinh bản tóm tắt bốn phần (nhu cầu chính · thông tin khách đã cung cấp · vấn đề chưa giải quyết
· bước tiếp theo đề xuất) khi hội thoại đóng, chạy trong worker từ `crm.conversation.closed`.

Ba ràng buộc định hình thiết kế:

- **Bản tóm tắt nằm ở `engagement.conversations` của Track A** (V114: `summary_data`,
  `summary_trigger`, `summary_model_version`, ràng buộc `ck_conv_summary_complete`). `ai_app` không có
  quyền trên schema đó, nên phải ghi qua `PATCH /internal/conversations/{id}/summary` (ADR-0002). Đây
  là một lời gọi HTTP, không chung transaction được với `ai.processed_events`.
- **Kế hoạch Ngày 12 có hai ô 🖐:** `temperature = 0` để tái lập, và ghim phiên bản model dạng ẢNH CHỤP.
- **java-core chưa có `/internal/*`** (09/10) và chưa phát `crm.conversation.closed`.

## Quyết định

| Vấn đề | Chốt |
|---|---|
| Nhiệt độ | Hằng `tom_tat.NHIET_DO = 0.0`, ghim trong code. Bộ tóm tắt dựng client LLM **riêng** (`service.tao_bo_tom_tat`), không đọc `LLM_TEMPERATURE` |
| Phiên bản model | `model` **do nhà cung cấp trả về trong phản hồi** của chính lượt sinh, bỏ tiền tố `models/`, ghép `@` + phiên bản lời nhắc (`gemini-3.5-flash-lite@tt2`), cắt phần model cho vừa `varchar(50)` |
| Bốn phần thiếu | Kiểm bằng Pydantic (khoá rỗng hoặc vắng là hỏng), **một** vòng sửa kèm lý do cụ thể, vẫn sai thì `SUMMARY_SCHEMA_INVALID`: ghi lượt `FAILED`, **không PATCH**, giữ bản cũ |
| Thứ tự | (1) kiểm sớm `da_xu_ly` → (2) đọc lịch sử qua java-core → (3) luật bỏ qua → (4) LLM → (5) **PATCH** (luỹ đẳng) → (6) **một transaction**: dòng `ai_interactions` nhánh `SUMMARY` + dòng chống trùng |
| Hội thoại ngắn | Dưới 2 tin nhắn của khách thì bỏ qua **bằng luật**, 0 lời gọi LLM (luồng phụ 1.1) |
| Hội thoại dài | Quá 12.000 ký tự thì tóm tắt từng khối (không cắt giữa tin nhắn) rồi gộp (luồng phụ 2.1) |
| PII | `mask_pii` trước khi gửi LLM, cùng chính sách với lượt chat. Tin đã che theo UC041 (`is_redacted`) bị bỏ hẳn |
| Lịch sử | `ai_interactions.response_text` = JSON bốn phần. Không có bảng tóm tắt riêng (đặc tả UC026, luồng phụ 4.1) |
| KPI | Lượt `SUMMARY` **không vào** tín hiệu UC027, kể cả KPI ≥ 55% lượt không gọi LLM — đó là lượt nền, không phải lượt chat |
| java-core | Client `integrations/java_core/` theo nháp hợp đồng; mặc định `JAVA_CORE_MODE=mock` tới khi Track A có endpoint |

Đường đồng bộ `POST /v1/ai/summarize` (đã có trong hợp đồng) dùng cùng bộ tóm tắt cho trigger
`MANUAL`. java-core gửi kèm lịch sử và tự ghi kết quả.

## Lập luận

- **Vì sao PATCH trước, đánh dấu sau.** Chết giữa (5) và (6) thì Kafka giao lại, lượt mới tóm tắt và
  PATCH lần nữa: vô hại vì PATCH ghi đè bản mới nhất, chỉ tốn thêm một lượt LLM. Đảo thứ tự thì chết
  giữa chừng là sự kiện bị đánh dấu xong mà hội thoại không có tóm tắt — **mất việc**, và không có gì
  nhặt lại. UC019 gom được vào một transaction vì tác động của nó nằm trong CSDL của mình; UC026 thì
  không. Test `test_java_core_sap_khi_patch_thi_chua_danh_dau_xong` khoá điều này, và đột biến đảo thứ
  tự làm nó đỏ.
- **Vì sao ghim nhiệt độ trong code, không trong cấu hình.** `LLM_TEMPERATURE` thuộc về lượt chat. Ai
  đó chỉnh nó cho lượt chat thì tóm tắt đổi theo mà không ai biết. Test đọc **thân HTTP thật** gửi đi,
  với `LLM_TEMPERATURE=0.9`.
- **Vì sao ảnh chụp từ phản hồi, không từ cấu hình.** Cấu hình nói model **đang** dùng, phản hồi nói
  model **đã sinh ra** bản này. Hai thứ lệch nhau khi nhà cung cấp trỏ bí danh sang bản mới, hoặc khi
  đổi `LLM_MODEL` giữa lúc worker còn bản tin cũ. Đọc qua tham chiếu (`ai_interactions.model_version`)
  thì mọi bản tóm tắt cũ tự khai sai phiên bản ngay khi đổi model. Ghép phiên bản lời nhắc vì cùng một
  model mà lời nhắc khác nhau thì cho ra hai bản tóm tắt khác nhau.
- **Vì sao một vòng sửa.** Ở nhiệt độ 0, vòng thứ ba gần như lặp lại vòng thứ hai, chỉ đốt hạn mức. Đo
  thật: 0/40 lượt cần sửa.
- **Lệch có chủ đích so với chữ của đặc tả** (`LLM_ERROR` — "không xác nhận offset"): không xác nhận
  mãi thì một hội thoại có LLM sập sẽ chặn cả partition phía sau. Worker thử lại tại chỗ 3 lần (chờ
  10 s rồi 60 s), sau đó đẩy DLQ với nguyên byte bản tin, phát lại được (cùng cơ chế với ADR-0024).

## Số đo (Gemini 3.5 Flash-Lite, 20 hội thoại mẫu, 09/10)

| Chỉ số | tt1 | **tt2 (ship)** |
|---|---|---|
| Đủ 4/4 phần — lượt 1 / lượt 2 | 20/20 · 20/20 | **20/20 · 20/20** |
| Bịa "đã cung cấp số điện thoại (đã che)" khi đầu vào không có | 1/40 | **0/40** |
| PII gốc lọt vào bản tóm tắt | 0 | 0 |
| Vòng sửa | 0/20 | 0/20 |
| Trung vị độ trễ | 1.212 ms | 1.169 ms |
| Bản giống hệt giữa hai lượt chạy | 0/20 | 0/20 |
| Phần giống hệt · tương đồng ký tự trung bình | 7/80 · 0,722 | 21/80 · 0,746 |

Nhánh chia khối (1.000 ký tự/khối) chạy trên H19 và H20: 4/4 phần, 4 và 3 lượt gọi.

## Đánh đổi

- **Nhiệt độ 0 KHÔNG cho tất định với Gemini.** Ba request giống hệt nhau cho ba bản khác câu chữ.
  Gemini cũng không nhận `seed` qua lớp tương thích OpenAI (thử ngày 09/10, trả 400). Hai bản giống
  nhau về nội dung (cùng sự kiện, cùng bốn phần) nhưng khác cách diễn đạt. "Tái lập" của UC026 vì thế
  dựa vào **ảnh chụp**: sinh một lần, lưu kèm phiên bản, không sinh lại để đối chiếu. Nhiệt độ 0 chỉ
  thu hẹp độ dao động, không xoá được nó.
- **Giới hạn số lượt mỗi phút của bậc miễn phí.** Chạy dồn thì lượt thứ 16 trong khoảng 20 giây đã
  nhận 429. Worker xử lý từng bản tin một và có khoảng chờ thử lại; một đợt đóng hàng loạt hội thoại
  vẫn có thể rơi vào DLQ. Ngày 18 bật thanh toán sẽ nâng trần (ADR-0028).
- **`TOKEN_QUOTA_EXCEEDED` chưa làm.** Hạn mức token theo tenant (UC006) chưa có ở ai-service. Hiện
  vượt trần của nhà cung cấp được xử lý như `LLM_ERROR`.
- **Lời nhắc lộ cho nhà cung cấp** (đã che SĐT/email/CCCD, nhưng tên và địa chỉ thì còn) — cùng giới
  hạn của lượt chat, ghi ở ADR-0028.

## Hệ quả

- **Mã:** `rag/generate/tom_tat.py`, `events/su_kien_hoi_thoai_dong.py`, `worker/consumers/tom_tat.py`,
  worker hai kênh (group `summarizer-cg`), `integrations/java_core/`, `service.summarize` +
  `summarize_messages`, `POST /v1/ai/summarize`.
- **Giao ước:** nháp [`uc026-uc041-tom-tat-va-xoa-du-lieu.md`](../contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md)
  — trigger theo enum V114 (`CLOSING`, không phải `CONVERSATION_CLOSED`), thân PATCH, `closed_by` tuỳ
  chọn.
- **Track A còn nợ:** phát `crm.conversation.closed` trong `InboxService.changeStatus`, và hai endpoint
  `GET …/messages` + `PATCH …/summary` kèm chuỗi bảo mật nội bộ.
- **Báo cáo:** chương 3 (thứ tự PATCH/đánh dấu, ảnh chụp); chương 5 (bảng số đo trên, kể cả kết quả 0/20
  bản giống hệt).
