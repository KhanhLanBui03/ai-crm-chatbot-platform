# ADR-0023 — Hạn mức tài liệu tính theo lượng ĐANG CÓ (số lượng và dung lượng), không theo lượt tải

- **Trạng thái:** Đề xuất — hướng chính do nhóm chốt 27/09/2026; các điểm (b)–(f) ở mục Quyết định chờ xác nhận
- **Ngày:** 2026-09-27
- **Làn sở hữu:** Track A (java-core giữ hạn mức) — ảnh hưởng hợp đồng UC020 với Track B

## Bối cảnh

Bản đầu của UC018 (commit `6fecd6e`) làm theo câu chữ đặc tả: *"Mức tiêu thụ tài liệu được cộng
vào `platform.usage_records` của chu kỳ hiện tại"* — tức là đếm **lượt tải được nhận trong chu kỳ**.
Hợp đồng UC018 mục 10 câu 1 đã nêu chỗ vênh: `subscription_plans.max_documents` nghe như một trần
tồn kho, không phải một hạn mức tiêu thụ. Hệ quả của cách đếm theo lượt:

- Gói TRIAL (20 tài liệu) sang chu kỳ mới được tải thêm 20 dù kho đang có sẵn 20 — kho phình không
  giới hạn qua các chu kỳ.
- Gỡ tài liệu (UC020) không trả lại chỗ, dù tài liệu đã biến mất khỏi kho.
- Không có gì chặn **dung lượng** — thứ thực sự tốn tiền (object S3, đoạn và vector trong
  `knowledge_chunks`). `subscription_plans.storage_mb` và giá trị `STORAGE_MB` trong `CHECK` của
  `usage_records.metric` đã có từ V102 mà chưa đường nào dùng; `ai-service-to-java-core.yaml:89`
  cũng đã ghi java-core kiểm `STORAGE_MB`.

Ràng buộc: java-core không đọc được schema `knowledge` (ADR-0002), nên không tự đếm được tài liệu
đang có. `usage_records` có một dòng cho mỗi `(subscription_id, metric)` — sang chu kỳ mới là dòng
mới.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Đếm lượt tải trong chu kỳ (bản `6fecd6e`) | Đơn giản, khớp câu chữ đặc tả | Ba hệ quả ở trên; không chặn dung lượng |
| B. Bộ đếm tồn kho trong `usage_records`: cộng khi tải, trừ khi gỡ, chép sang chu kỳ mới | Đọc rẻ (UC006 đọc thẳng bảng); kiểm hạn mức vẫn nằm trong một transaction có khoá dòng; không thêm lời gọi đồng bộ | Bộ đếm có thể lệch với thực tế khi có sự cố giữa hai dịch vụ |
| C. Hỏi ai-service số tài liệu và tổng dung lượng mỗi lần tải | Luôn đúng với thực tế | Thêm một lời gọi đồng bộ mỗi lượt tải và mỗi lần mở màn UC006; vẫn phải khoá phía java-core để chặn hai lượt đồng thời |

## Quyết định

**B — hạn mức tài liệu là lượng đang có, giữ bằng bộ đếm tồn kho trong `usage_records`, cho hai chỉ
số `DOCUMENT` và `STORAGE_MB`.** Cụ thể:

- **(a) Chặn khi tải:** `đang có + phần thêm > trần` thì 409 — `DOCUMENT_QUOTA_EXCEEDED` (thêm 1
  tài liệu) hoặc `STORAGE_MB_QUOTA_EXCEEDED` (thêm đúng số byte của tệp). Kiểm `DOCUMENT` trước,
  `STORAGE_MB` sau, và mọi lượt tải khoá hai dòng theo đúng thứ tự đó — không có deadlock.
- **(b) Cái gì được đếm:** mọi bản ghi tài liệu đang tồn tại — mỗi `version` là một tài liệu, kể cả
  bản `FAILED` (vẫn chiếm một dòng và một object tới khi bị gỡ). Lượt bị ai-service từ chối không
  được đếm (object đã bị xoá).
- **(c) `STORAGE_MB` lưu theo BYTE** ở cả `used_value` lẫn `quota_value`; `quota_value` =
  `storage_mb × 1 048 576` lúc chép từ gói. Tên chỉ số giữ theo `CHECK` của V102.
- **(d) Sang chu kỳ mới:** chỉ số tồn kho (`DOCUMENT`, `STORAGE_MB`, `USER`) chép `used_value` từ dòng
  cùng chỉ số của chu kỳ gần nhất trước đó; chỉ số dòng chảy (`CONVERSATION`, `AI_TOKEN`) bắt đầu
  từ 0. `quota_value` vẫn chép từ gói hiện hành.
- **(e) Mốc `blocked_at`** = lần đầu trong chu kỳ dùng đủ 100% **hoặc** lần đầu một lượt tải bị từ
  chối vì hạn mức — với dung lượng, lượt bị chặn thường chưa chạm đúng 100%.
- **(f) Gỡ tài liệu (UC020) phải trả lại chỗ:** trừ 1 ở `DOCUMENT` và đúng số byte ở `STORAGE_MB`,
  trong cùng transaction với dòng outbox `DocumentDeleted`. ai-service phải trả `file_size_bytes`
  của tài liệu vừa gỡ.

## Lập luận

- B đúng nghĩa "đang có" mà không phá ADR-0002 và không thêm lời gọi đồng bộ. Lượt tải đã khoá
  dòng hạn mức sẵn (chống hai lượt đồng thời); chuyển từ đếm lượt sang đếm tồn kho chỉ đổi con số
  được cộng và thêm một dòng khoá — không đổi cấu trúc luồng.
- Lưu byte chứ không MB: làm tròn lên thì 20 tệp văn bản vài KB thành 20 MB; làm tròn xuống thì tệp
  nhỏ thành 0 MB. Trừ lại lúc gỡ cũng chỉ khớp khi cộng và trừ cùng một con số chính xác.
- Chép mức đang có sang chu kỳ mới là hệ quả trực tiếp của "đang có": tài liệu không biến mất khi
  sang tháng.

## Đánh đổi

1. **Bộ đếm có thể lệch thực tế.** Khe 1 của hợp đồng UC018 mục 4 (ai-service đã nhận nhưng
   java-core commit hỏng) làm đếm thiếu một tài liệu; UC020 gỡ hỏng giữa chừng có thể làm lệch
   ngược lại. Cần một job đối soát định kỳ với số liệu của ai-service — **chưa làm**, ghi nợ.
2. **Tên `STORAGE_MB` nói dối về đơn vị.** Ai đọc bảng mà không đọc ADR này sẽ hiểu sai; bù lại bằng
   `COMMENT ON COLUMN` ở V128 và chú thích ở ERD. Đổi tên chỉ số cần sửa `CHECK` — không đáng.
3. **Lệch câu chữ đặc tả UC018** ("cộng vào mức tiêu thụ của chu kỳ") và UC006 (chỉ nêu bốn hạn mức,
   không có dung lượng). Phải sửa đặc tả và thêm ô dung lượng vào màn hạn mức.
4. **Mỗi lượt tải khoá hai dòng thay vì một** — cùng tenant vẫn xếp hàng như trước, không tệ hơn.
5. **Mốc 80% / 100% không tự xoá khi gỡ bớt tài liệu** — cách xử lý mốc khi mức dùng tụt xuống chốt
   ở UC020, chưa ở đây.

## Hệ quả

- **Code java-core:** `UsageQuotaService` nhận lượng cần thêm; câu tạo dòng hạn mức chép mức tồn kho
  của chu kỳ trước; phản hồi 202 thêm `storageQuota` (byte); lỗi mới `STORAGE_MB_QUOTA_EXCEEDED`.
- **Lược đồ:** không thêm cột. V128 ghi chú đơn vị của `STORAGE_MB`.
- **Hợp đồng:** UC018 mục 5 viết lại; UC020 phải có `file_size_bytes` trong phản hồi gỡ của
  ai-service; `dashboard-api.yaml` — `HanMucSuDung` thêm ô dung lượng.
- **Đặc tả:** UC018 hậu điều kiện "cộng vào mức tiêu thụ của chu kỳ" → "cộng vào lượng tài liệu
  và dung lượng đang có"; UC006 bốn hạn mức → năm.
- **Báo cáo:** chương 3 — vì sao hạn mức kho là tồn kho còn hạn mức hội thoại/token là dòng chảy.
