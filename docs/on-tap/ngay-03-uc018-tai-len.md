# Ôn tập Ngày 3 — UC018 Tải lên tài liệu tri thức

> Viết bù 06/10/2026. Hợp đồng: [`docs/contracts/uc018-tai-tai-lieu.md`](../contracts/uc018-tai-tai-lieu.md).
> Quyết định: ADR-0020 (ranh giới UC018), ADR-0022 (kho tệp RustFS), ADR-0023 (hạn mức theo byte).

## Hệ thống chạy thế nào

1. java-core nhận multipart và kiểm 401 / 413 / 422 / 415 / 409.
2. java-core khoá dòng hạn mức, rồi ghi tệp lên S3 tại `kb-tai-lieu/{tenant_id}/{upload_id}/{tên đã làm sạch}`.
3. java-core gọi ai-service, truyền **URI của tệp** (không truyền nội dung).
4. ai-service ghi tài liệu `PENDING`.
5. java-core ghi outbox để phát `crm.kb.document.uploaded`. Worker UC019 nhận sự kiện này và nạp
   tài liệu.

## "Phải giải thích được"

**Vì sao đường dẫn lưu trữ phải chứa `tenant_id` khi truy vấn đã lọc `tenant_id` rồi?**
- Kho tệp S3 **không có RLS**: một bucket chung cho mọi tenant. Lọc ở CSDL không bảo vệ được tầng
  lưu trữ.
- `tenant_id` nằm trong key thì ai-service tự kiểm được: URI gửi tới phải nằm đúng vùng của tenant
  trong header. Nếu sai thì trả `FORBIDDEN_FILE_URI`. Đây là lớp chặn khi URI bị giả, hoặc java-core
  dựng key sai.
- So **đúng cả phân đoạn**, không so tiền tố chuỗi. Lý do: tiền tố `abc` cũng khớp `abcd…`.
- Lợi ích phụ: dọn hoặc xuất dữ liệu theo tenant chỉ cần liệt kê một tiền tố (UC041, Nghị định 13).

**`409` và `422` khác nhau thế nào? Vì sao không gộp?**
- **422 `INVALID_METADATA`:** yêu cầu **tự nó sai** (thiếu tệp, `title` ngoài 3–255, `language` lạ…).
  Sửa đầu vào là gửi lại được. Giao diện giữ hộp thoại và đánh dấu đúng trường sai.
- **409 (`DOCUMENT_QUOTA_EXCEEDED`, `STORAGE_MB_QUOTA_EXCEEDED`, `SUBSCRIPTION_NOT_ACTIVE`):** yêu cầu
  **hợp lệ** nhưng xung đột với **trạng thái hiện tại** của tài nguyên. Gửi lại y hệt vẫn hỏng cho tới
  khi trạng thái đổi. Giao diện dẫn sang việc khác: gỡ bớt tài liệu, nâng gói.
- Gộp làm một thì client không biết phải làm gì, và thống kê lỗi trộn "người dùng nhập sai" với
  "doanh nghiệp hết hạn mức".
