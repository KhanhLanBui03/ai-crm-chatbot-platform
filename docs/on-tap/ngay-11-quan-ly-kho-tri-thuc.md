# Ôn tập Ngày 11 — Quản lý kho tri thức: duyệt, sửa, nạp lại, gỡ (UC020)

> Viết 09/10/2026 (lịch gốc 01/10). Quyết định: [ADR-0031](../adr/0031-nap-lai-bang-ban-bong.md).
> Số liệu: [`docs/report/uc020-ngay11-2026-10-09.md`](../report/uc020-ngay11-2026-10-09.md).
> Hợp đồng nháp: [`uc020-quan-ly-kho.md`](../contracts/uc020-quan-ly-kho.md).

## 1. Hôm nay hệ thống có thêm gì, nằm đâu

```
dashboard ─► java-core (chưa có proxy) ─► ai-service /v1/documents …   [api/v1/endpoints/kho.py]
                                              │
   GET  /v1/documents?keyword&status&sourceType ── danh_sach: f_unaccent + LIKE, ẩn ARCHIVED
   GET  /v1/documents/{id}            ──────────── lay_tai_lieu (RLS ⇒ tenant khác = 404)
   GET  /v1/documents/{id}/chunks     ──────────── danh_sach_doan — KHÔNG có cột embedding
   PATCH /v1/documents/{id}           ──────────── title/description, KHÔNG đụng knowledge_chunks
   DELETE /v1/documents/{id}          ──────────── khoá dòng ─► xoá đoạn ─► ARCHIVED (một transaction)
   POST /v1/documents/{id}/reindex    ──────────── khoá dòng ─► tạo BẢN BÓNG (dòng mới, version+1)
   POST /v1/ai/kb/reindex             ──────────── bản bóng cho mọi tài liệu READY
                                              │
worker: bộ quét 60 s ─► tim_job_ket (V213: nhặt bản bóng NGAY) ─► nap_tai_lieu (đường UC019 có sẵn)
                                              │
        hoan_tat(bản bóng): READY ─► xoá đoạn bản cũ ─► bản cũ ARCHIVED   ← CÙNG một transaction
```

## 2. Đi theo dữ liệu qua các file

| Bước | File | Ghi nhớ |
|---|---|---|
| Endpoint | [`api/v1/endpoints/kho.py`](../../ai-service/src/api/v1/endpoints/kho.py) | chỉ lấy tenant từ header, gọi facade |
| Facade | [`service.py`](../../ai-service/src/ai/service.py) mục UC020 | khoá dòng rồi mới kiểm trạng thái; log `kiem_toan_kho` |
| Truy vấn tài liệu | [`document_repository.py`](../../ai-service/src/ai/db/repositories/document_repository.py) `danh_sach`, `lay_tai_lieu`, `tao_ban_bong`, `xoa_khoi_chi_muc`, `hoan_tat` | biểu thức tìm trùng chỉ mục trigram |
| Xem đoạn | [`chunk_repository.py`](../../ai-service/src/ai/db/repositories/chunk_repository.py) `danh_sach_doan` | liệt kê cột tường minh, không `SELECT *` |
| Lược đồ | [`V213`](../../ai-service/migration/V213__nap_lai_ban_bong_va_tim_kiem_tai_lieu.sql) | cột bản bóng, chỉ mục duy nhất bộ phận, trigram, `tim_job_ket` |

## 3. Quyết định hôm nay và vì sao

1. **Nạp lại bằng BẢN BÓNG, không nạp tại chỗ** (ADR-0031). Đường nạp UC019 chuyển dòng sang `PROCESSING`
   và xoá đoạn cũ; truy hồi chỉ lấy `READY` ⇒ nạp tại chỗ là tài liệu biến mất suốt lúc nạp. Bản bóng là
   một dòng mới đi qua ĐÚNG đường nạp có sẵn; đổi bản trong một transaction.
2. **Loại phương án "lớp đoạn"** — phải sửa câu SQL truy hồi lõi (đã đo E3), đổi ràng buộc duy nhất của
   đoạn, tách trần thử lại khỏi thẻ sở hữu; tài liệu `FAILED` mà vẫn được truy hồi.
3. **Bộ quét nhặt bản bóng** thay vì phát sự kiện: topic upload là của java-core; bộ quét đã là lưới an
   toàn của mọi `PENDING`; ≤ 60 s chấp nhận được cho thao tác chạy nền.
4. **Hai lượt nạp lại chồng bị chặn ở CSDL** (`uq_doc_mot_luot_nap_lai` — chỉ mục duy nhất bộ phận), không
   khoá ở tầng ứng dụng.
5. **Danh sách ẩn `ARCHIVED`** trừ khi lọc — tài liệu đã gỡ không chi phối câu trả lời nào.
6. **`language` không sửa được qua PATCH** — nó quyết định cách tách từ; đổi là nạp lại.

## 4. "Phải giải thích được"

**Vì sao tài liệu của tenant khác trả 404 chứ không phải 403?**
- 403 nghĩa là "có, nhưng anh không được xem" — tức XÁC NHẬN id đó tồn tại ở một tenant khác. Kẻ dò chỉ
  cần đoán id rồi đếm 403 là biết mình đoán trúng.
- Ở đây còn không thể trả 403 nếu muốn: RLS che dòng của tenant khác TRƯỚC khi ứng dụng thấy nó — với
  phiên của tenant B, dòng của A đơn giản là không tồn tại. 404 là hành vi tự nhiên của RLS, không phải
  một nhánh `if` có thể viết sai.
- Test `test_404_tenant_khac_moi_duong` đi qua cả 6 đường và kiểm tài liệu của A không bị đụng tới.

**Vì sao xoá đoạn TRƯỚC rồi mới `ARCHIVED`, không làm ngược lại?**
- Thứ tự ngược mà bước thứ hai hỏng ⇒ tài liệu đã biến khỏi giao diện (`ARCHIVED`) nhưng vector vẫn trong
  chỉ mục và vẫn được truy hồi — câu trả lời trích một tài liệu mà quản trị viên tin là đã gỡ. Không ai
  thấy để sửa.
- Thứ tự đúng mà bước thứ hai hỏng ⇒ tệ nhất là tài liệu vẫn hiện, đoạn đã mất — thấy được, gỡ lại được.
- Ở đây hai câu nằm trong CÙNG transaction nên hỏng bước nào cũng rollback cả hai (test
  `test_go_hong_giua_chung_tra_5xx_va_giu_nguyen`). Thứ tự vẫn giữ: nó đúng cả khi ai đó tách thành hai
  transaction, và khi kho vector là hệ thống ngoài (không chung transaction với CSDL).

**Reindex làm sao để không có khoảnh khắc nào kho rỗng?**
- Không nạp lại trên dòng cũ. Tạo dòng mới (bản bóng) cùng tệp, nạp nó như tài liệu mới — bản cũ vẫn
  `READY`, vẫn phục vụ.
- Khi bản bóng xong, MỘT transaction làm ba việc: bản bóng `READY`, xoá đoạn bản cũ, bản cũ `ARCHIVED`.
- Truy hồi là một câu SQL trên một ảnh chụp (MVCC): nó thấy trạng thái trước commit (bản cũ) hoặc sau
  commit (bản mới) — không bao giờ thấy trạng thái giữa.
- Đo thật: 96 lần hỏi trong 3,2 s nạp lại, 0 lần trống, 0 lần thấy hai bản cùng lúc.

## 5. Câu phản biện kiểu hội đồng

1. *"Id tài liệu đổi sau mỗi lần nạp lại — giao diện xử lý sao?"* — Phản hồi nạp lại trả `job_id` = id
   bản mới; bản mới mang `replaces_document_id`, bản cũ mang `reindex_document_id` trong lúc nạp. Câu trả
   lời cũ vẫn trỏ đúng bản đã dùng — đúng luồng phụ 7.1 của đặc tả.
2. *"Đổi mô hình nhúng thì 'nạp lại toàn kho' có thật sự 0 giây trống?"* — Không tự động: truy hồi lọc đoạn
   theo mô hình của vector câu hỏi. Phải đổi `EMBED_URL` của worker trước, nạp lại toàn kho, rồi mới đổi của
   API. Ghi rõ ở ADR-0031 — một giới hạn vận hành, nói trước khi bị hỏi.
3. *"Vì sao không dùng một cờ 'đang chuyển đổi' cho đơn giản?"* — Cờ thì người đọc phải kiểm, quên một
   chỗ là lộ trạng thái giữa. Transaction + MVCC cho tính nguyên tử mà không cần ai nhớ kiểm gì.
4. *"Hai quản trị viên bấm nạp lại cùng lúc?"* — Khoá dòng `FOR UPDATE` xếp hàng hai request; người sau
   thấy bản bóng đã có ⇒ 409. Lỡ có đường nào lọt, chỉ mục duy nhất bộ phận vẫn chặn ở CSDL.
5. *"Tìm kiếm có chậm khi kho lớn?"* — Chỉ mục trigram trên đúng biểu thức tìm (`EXPLAIN` xác nhận dùng
   được). Ở quy mô vài chục tài liệu/tenant, planner chọn chỉ mục theo tenant — cũng đúng.

## 6. Số đo và ý nghĩa

| Đo gì | Kết quả |
|---|---|
| 4 mã lỗi | 404 (6 đường) · 409 (3 tình huống) · 422 (5 dạng body) · 5xx giữ nguyên trạng thái — đúng hết |
| 0 giây trống (thật) | 96 lần hỏi / 3,2 s nạp lại: 0 trống, 0 hai bản |
| Nạp lại hỏng | bản cũ vẫn `READY`, vẫn truy hồi được (gặp thật với kho đo nhân bản) |
| Tìm không dấu | `BẢO HÀNH` → 3 tài liệu · `bang gia` → "Bảng giá sản phẩm 2026" |
| PATCH | đoạn + vector + `updated_at` của đoạn giống hệt trước/sau |
| Test | 21 ca mới · tổng 595 passed · 8/8 đột biến làm đỏ |

## 7. Phần AI làm — khai trung thực

- Toàn bộ code, V213, ADR-0031, nháp hợp đồng, test và ghi chú này do Claude viết (theo chốt 05/10).
- Phương án bản bóng do Claude chọn sau khi so với phương án lớp đoạn — lý do ở ADR-0031.
- Phần java-core (proxy SCR030–SCR032, `audit_logs`) chưa làm — Track A.

## 8. Ba câu tự kiểm

1. Bản bóng đang `PROCESSING` thì tài liệu cũ hiện trạng thái gì, và truy hồi lấy đoạn của bản nào?
2. Nếu bản bóng `FAILED`, quản trị viên bấm nạp lại lần nữa thì chuyện gì xảy ra với dòng `FAILED` đó?
3. Vì sao `GET /v1/documents/{id}/chunks` của tenant khác trả 404 chứ không trả trang rỗng?
