# Ôn tập Ngày 12 — Tóm tắt hội thoại (UC026) và xoá dữ liệu cá nhân (UC041)

> Viết 09/10/2026 (lịch gốc 02/10). Quyết định:
> [ADR-0032](../adr/0032-tom-tat-hoi-thoai-nhiet-do-0-anh-chup-model.md) ·
> [ADR-0033](../adr/0033-xoa-du-lieu-ca-nhan-phia-ai.md). Số liệu:
> [`docs/report/uc026-uc041-ngay12-2026-10-09.md`](../report/uc026-uc041-ngay12-2026-10-09.md). Hợp
> đồng nháp: [`uc026-uc041-tom-tat-va-xoa-du-lieu.md`](../contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md).

## 1. Hôm nay hệ thống có thêm gì, nằm đâu

```
UC026 — bất đồng bộ
java-core đóng hội thoại ─(outbox, CHƯA phát)─► crm.conversation.closed
                                                    │  group summarizer-cg (kênh thứ 2 của worker)
worker/consumers/tom_tat.py ─► service.summarize ───┤
   1. da_xu_ly(event_id)?            ── trùng ⇒ TRUNG, 0 LLM
   2. GET /internal/…/messages       ── java-core (GIẢ: JAVA_CORE_MODE=mock)
   3. < 2 tin của khách?             ── LUẬT ⇒ BO_QUA_NGAN, 0 LLM
   4. BoTomTat: che PII ─► LLM t=0 ─► 4 phần? ─ không ─► 1 vòng sửa ─ vẫn không ⇒ SAI_DINH_DANG
   5. PATCH /internal/…/summary      ── ghi đè, luỹ đẳng
   6. ai_interactions(SUMMARY) + processed_events   ← MỘT transaction, SAU khi PATCH xong
UC026 — đồng bộ: POST /v1/ai/summarize (MANUAL) ── cùng BoTomTat, java-core tự ghi kết quả

UC041
java-core (sau khi XÁC MINH danh tính) ─► DELETE /v1/ai/privacy/contacts/{id}?conversationId=…
                                            │  X-Internal-Token phải khớp, không thì 403
service.forget_contact:
   1. MỘT transaction: tài liệu có contact_id (+ dòng dõi cùng tệp) ─► đoạn ─► lượt + đánh giá  COMMIT
   2. xoá tệp gốc trên S3
   3. DELETE /internal/contacts/{id}/lead-scores (java-core, GIẢ)
   ─► 7 mục MucXoa, COMPLETED | PARTIALLY_FAILED, luỹ đẳng
```

## 2. Đi theo dữ liệu qua các file

| Bước | File | Ghi nhớ |
|---|---|---|
| Giải mã sự kiện | [`events/su_kien_hoi_thoai_dong.py`](../../ai-service/src/ai/events/su_kien_hoi_thoai_dong.py) | chỉ cần `conversation_id`; `closed_by` không bắt buộc |
| Commit hay DLQ | [`worker/consumers/tom_tat.py`](../../ai-service/src/worker/consumers/tom_tat.py) | mọi kết cục của service đều COMMIT; ngoại lệ thì thử lại 3 lần rồi DLQ |
| Worker hai kênh | [`worker/main.py`](../../ai-service/src/worker/main.py) `Kenh` | mỗi topic một consumer, một group, một vòng lặp |
| Bộ tóm tắt | [`rag/generate/tom_tat.py`](../../ai-service/src/ai/rag/generate/tom_tat.py) | `NHIET_DO`, `chup_phien_ban`, `doc_dau_ra`, `chia_khoi`, `BoTomTat` |
| Thứ tự UC026 | [`service.py`](../../ai-service/src/ai/service.py) `summarize` | PATCH rồi mới đánh dấu xong |
| Gọi java-core | [`integrations/java_core/client.py`](../../ai-service/src/ai/integrations/java_core/client.py) | Http thật + giả; header tenant/trace; không lặp lại thân lỗi |
| Lược đồ | [`V214`](../../ai-service/migration/V214__contact_id_tai_lieu_cho_xoa_du_lieu_ca_nhan.sql) | `contact_id` + chỉ mục bộ phận |
| Xoá | [`document_repository.xoa_tai_lieu_theo_khach`](../../ai-service/src/ai/db/repositories/document_repository.py) · [`interaction_repository.xoa_theo_hoi_thoai`](../../ai-service/src/ai/db/repositories/interaction_repository.py) | dòng dõi theo `file_path`; đếm trước rồi mới xoá |
| Endpoint xoá | [`api/v1/endpoints/rieng_tu.py`](../../ai-service/src/api/v1/endpoints/rieng_tu.py) | `hmac.compare_digest`; không dùng `SessionDep` |

## 3. Quyết định hôm nay và vì sao

1. **PATCH trước, đánh dấu xong sau** (ADR-0032). PATCH là HTTP, không chung transaction với
   `processed_events` được. Chết giữa chừng thì: PATCH-rồi-đánh-dấu ⇒ làm lại một lần (vô hại); đánh
   dấu-rồi-PATCH ⇒ **mất tóm tắt vĩnh viễn**. Chọn "làm thừa" thay vì "làm thiếu".
2. **Nhiệt độ ghim trong code**, client LLM riêng cho tóm tắt (mạch riêng, hạn chót 20 s).
3. **Ảnh chụp = tên model nhà cung cấp TRẢ VỀ + phiên bản lời nhắc**, không đọc từ cấu hình.
4. **Luật trước LLM:** hội thoại < 2 tin của khách thì bỏ qua — 0 đồng, 0 ms.
5. **`contact_id` trên tài liệu (V214), không trên đoạn**; xoá theo cả "dòng dõi" cùng `file_path`.
6. **Danh sách hội thoại do java-core gửi**, không thêm `contact_id` vào `ai_interactions`.
7. **Commit CSDL trước khi chạm S3 và java-core** — truy hồi ngừng thấy dữ liệu ngay tại commit.
8. **Token nội bộ**: chỉ java-core gọi được endpoint xoá, tức là chỉ sau bước xác minh danh tính.
9. **Lượt `SUMMARY` không vào KPI "lượt không gọi LLM"** — đó là lượt nền, không phải lượt chat.
10. **Sửa lời nhắc `tt1` → `tt2`** sau khi đo thấy mô hình bịa "số điện thoại (đã che)".

## 4. "Phải giải thích được" — ba câu của kế hoạch Ngày 12

**Vì sao `temperature = 0`? Nó có làm tóm tắt kém đi không?**

- Tóm tắt là **nén thông tin**, không phải sáng tác. Nhiệt độ cao chỉ thêm biến thể câu chữ, và mỗi
  biến thể là một cơ hội để thêm một chi tiết không có trong hội thoại.
- **Không kém đi về nội dung:** đo trên 20 hội thoại, 40/40 bản đủ 4/4 phần, 0 vòng sửa, 0 PII lọt.
  Mô hình vẫn diễn đạt tự nhiên vì nhiệt độ chỉ ảnh hưởng **cách chọn từ**, không ảnh hưởng **hiểu**.
- **Nhưng 0 KHÔNG có nghĩa là tất định với Gemini** — điều này phải nói thẳng, đừng để hội đồng tự
  phát hiện. Ba request giống hệt nhau cho ba bản khác câu chữ, 0/20 bản giống hệt giữa hai lượt chạy
  (tương đồng ký tự 0,746). Gemini cũng không nhận `seed` qua lớp tương thích OpenAI. Lý do nằm ở phía
  nhà cung cấp: phép tính dấu phẩy động song song trên GPU, gom lô giữa nhiều request.
- Vì vậy "tái lập" của UC026 dựa vào **ảnh chụp**: sinh **một lần**, lưu kèm phiên bản model + lời nhắc,
  không bao giờ sinh lại để so. Nhiệt độ 0 thu hẹp độ dao động; ảnh chụp mới là thứ làm cho bản tóm
  tắt kiểm chứng được.
- Nếu hội đồng hỏi "vậy sao không bỏ nhiệt độ 0?": vì nó vẫn thu hẹp không gian đầu ra. Câu kiểm "4/4
  phần" ổn định hơn, và lượt chạy lại khi Kafka giao trùng cho bản gần như giống bản cũ.

**Vì sao ghim phiên bản model dạng "ảnh chụp" chứ không tham chiếu?**

- Tham chiếu = bản tóm tắt chỉ trỏ tới một bản ghi khác (ví dụ `ai_interactions.model_version`, hay
  cấu hình hiện tại). Đổi model một lần là **mọi bản tóm tắt cũ đồng loạt khai sai** rằng chúng được
  sinh bởi model mới.
- Ảnh chụp = chép giá trị **vào chính bản tóm tắt** lúc sinh (`summary_model_version` của V114). Giá trị
  không bao giờ đổi theo cái gì khác. Cùng lập luận với hạn mức sao chép của UC006 — đặc tả gọi đó là
  "phi chuẩn hoá có chủ ý".
- Thêm hai chi tiết đã làm:
  - lấy tên model **từ phản hồi** của nhà cung cấp, không từ cấu hình, vì bí danh có thể trỏ sang bản
    mới mà cấu hình không đổi;
  - ghép phiên bản lời nhắc (`@tt2`), vì cùng model mà lời nhắc khác nhau thì là hai "máy sinh" khác
    nhau. Hôm nay đã đổi `tt1` → `tt2`, và bản tóm tắt cũ vẫn khai đúng `@tt1`.
- Test bằng chứng: `test_phien_ban_la_anh_chup_tu_phan_hoi_khong_tu_cau_hinh`. Lần đầu đột biến "đọc từ
  cấu hình" **không** làm test đỏ, vì LLM giả trả về đúng tên đã cấu hình — đã sửa. Đây là ví dụ đẹp
  cho câu "kiểm ngược để làm gì".

**Vì sao xoá hội thoại KHÔNG xoá cơ hội tiềm năng? Lập luận pháp lý là gì?**

- Nghị định 13/2023/NĐ-CP trao cho chủ thể quyền yêu cầu xoá **dữ liệu cá nhân** — thông tin gắn với
  một con người xác định được. Cơ hội tiềm năng (lead) sau khi bỏ liên kết tới hội thoại và khách đã ẩn
  danh là một **dấu vết kinh doanh**: có một cơ hội, ở giai đoạn nào, giá trị bao nhiêu. Nó không còn
  xác định được ai.
- Doanh nghiệp còn nghĩa vụ khác buộc phải giữ dấu vết đó — kế toán, kiểm toán, báo cáo phễu bán hàng.
  Xoá luôn lead là phá số liệu doanh thu của các kỳ đã chốt, và đặc tả UC041 nói rõ "số liệu đã tổng
  hợp được giữ nguyên ở dạng không định danh".
- Cơ chế: java-core V132 `ON DELETE SET NULL (source_conversation_id)` — liên kết về `null`, bản ghi
  còn. Phải ghi **đích danh cột**: `SET NULL` trơn sẽ đặt null cả `tenant_id` của khoá kép và nổ lỗi
  (bug V108 mà V132 sửa).
- Phía AI: chỉ xoá **đặc trưng** trong `sales.lead_scores` (vector đặc trưng chứa dữ liệu cá nhân) qua
  API, không đụng `sales.leads`.

## 5. Câu phản biện kiểu hội đồng

- **"Tóm tắt gửi nội dung khách cho Google — có vi phạm Nghị định 13 không?"**
  - Che SĐT/email/CCCD/CMND trước khi gửi, cùng chính sách với lượt chat (đo được 0 PII gốc lọt).
  - Tên và địa chỉ vẫn đi qua, và bậc miễn phí dùng nội dung để huấn luyện ⇒ Ngày 18 có dữ liệu thật
    thì **phải bật thanh toán** (ADR-0028).
  - `note` của UC041 nói thẳng: không xoá được ở phía nhà cung cấp.
- **"Endpoint xoá — ai gọi được?"**
  - Chỉ bên có `X-Internal-Token`, tức java-core, và java-core chỉ gọi **sau** bước xác minh danh tính
    (ràng buộc `ck_erasure_gate` ở CSDL Track A).
  - Gateway đang mở `/ai/v1/**` cho mọi JWT ⇒ không có token này thì nhân viên bất kỳ xoá được.
  - Token rỗng ⇒ endpoint đóng hẳn (fail-closed).
- **"Kafka giao trùng hai lần thì khách bị tóm tắt hai lần, tốn hai lượt LLM?"** Không:
  - `da_xu_ly` kiểm sớm nên lần hai trả `TRUNG`, 0 LLM;
  - kịch bản 4 trên Kafka thật gửi trùng hai lần thì PATCH đúng một lần.
  - Chỉ khi chết giữa PATCH và đánh dấu thì mới làm lại — vô hại.
- **"Xoá hỏng giữa chừng thì sao?"**
  - CSDL commit trước, nên truy hồi đã sạch;
  - S3 hoặc java-core hỏng ⇒ mục đó `FAILED`, cả yêu cầu `PARTIALLY_FAILED`;
  - gọi lại thì làm nốt (luỹ đẳng — test `test_chay_lai_luy_dang`).
- **"Tài liệu riêng của khách nằm trong kho chung có rủi ro gì?"** Có, và hôm nay đã **đo thấy**: hợp
  đồng của khách X được trích cho câu hỏi chung. `contact_id` mới dùng để xoá, chưa chặn truy hồi — nợ
  bảo mật đưa vào Ngày 17.

## 6. Số đo và ý nghĩa

| Số | Ý nghĩa |
|---|---|
| 20/20 × 4/4 phần (hai lượt) | đạt cổng ra Ngày 12 trên Gemini thật, đếm trên thân PATCH |
| 0/20 bản giống hệt, tương đồng 0,746 | nhiệt độ 0 ≠ tất định — tái lập nhờ ảnh chụp |
| bịa "đã che" 1/40 → 0/40 | sửa lời nhắc `tt1` → `tt2` có tác dụng |
| trung vị 1.169 ms | lượt nền, không ai chờ; hạn chót 20 s |
| 429 ở lượt thứ 16 trong ~20 s | giới hạn số lượt mỗi phút của bậc miễn phí — worker cần giãn/thử lại |
| trích dẫn của khách: 1 → 0 | câu trả lời sau khi xoá không còn dữ liệu đã xoá |
| 681 test, 12/12 đột biến đỏ | test có răng, kể cả thứ tự PATCH và chốt token |

## 7. Phần AI làm — khai trung thực

- AI viết toàn bộ code, test, migration V214, ADR-0032/0033, nháp hợp đồng, báo cáo và ghi chú này.
- **20 hội thoại mẫu do AI soạn** (hư cấu, số điện thoại/email giả). Không phải dữ liệu thật của doanh
  nghiệp.
- java-core **giả** cho mọi lời gọi `/internal/*`; số "3 dòng lead đã xoá" là của bản giả.
- Lời nhắc tóm tắt do AI viết và AI sửa (`tt1` → `tt2`) dựa trên phép đo.

## 8. Ba câu tự kiểm

1. Nếu đảo bước 5 và 6 của `summarize`, kịch bản hỏng nào làm mất bản tóm tắt vĩnh viễn, và test nào
   bắt được?
2. Vì sao `xoa_tai_lieu_theo_khach` phải lọc cả `file_path`, chứ không chỉ `contact_id`? Nêu một chuỗi
   thao tác UC020 làm lọc thuần `contact_id` bỏ sót.
3. Vì sao endpoint xoá không dùng `SessionDep` như các endpoint UC020?
