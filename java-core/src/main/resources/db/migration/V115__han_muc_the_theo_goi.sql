-- V115 — Giới hạn số thẻ phân loại theo gói dịch vụ.
-- UC017
--
-- UC017 9.1-9.2 (luồng thay thế): "Nếu số lượng thẻ của doanh nghiệp VƯỢT GIỚI HẠN CHO
-- PHÉP → từ chối tạo thẻ mới và đề nghị quản trị viên dọn dẹp các thẻ không còn sử dụng."
--
-- V102 có bốn hạn mức (max_users, max_documents, max_channels, storage_mb) nhưng không
-- có hạn mức thẻ, nên nhánh 9.1 không có gì để so. Hợp đồng đã khai GoiDichVu.maxTags
-- từ trước — đây là cột nó vẫn thiếu.
--
-- Vì sao là hạn mức THEO GÓI chứ không phải hằng số: nó nằm cùng chỗ với bốn hạn mức
-- kia, cùng được đọc ở SCR012+013 khi so sánh các gói, và cùng là trục thu phí. Đặt nó
-- thành hằng số ở tầng mã là tách một hạn mức ra khỏi bảng hạn mức.
--
-- Thẻ không tính vào usage_records: khác bốn hạn mức kia, số thẻ là một con số nhỏ đếm
-- được tức thời bằng COUNT trên engagement.tags, không cần cột cộng dồn theo chu kỳ.

ALTER TABLE platform.subscription_plans
    ADD COLUMN max_tags smallint NOT NULL DEFAULT 50 CHECK (max_tags > 0);

-- Giá trị theo gói, cùng bậc thang với max_users. DEFAULT ở trên chỉ để ALTER chạy
-- được trên bốn dòng đã seed ở V102; bốn giá trị thật là bốn dòng dưới đây.
UPDATE platform.subscription_plans SET max_tags =  20 WHERE code = 'TRIAL';
UPDATE platform.subscription_plans SET max_tags =  50 WHERE code = 'STARTER';
UPDATE platform.subscription_plans SET max_tags = 150 WHERE code = 'GROWTH';
UPDATE platform.subscription_plans SET max_tags = 500 WHERE code = 'PRO';

COMMENT ON COLUMN platform.subscription_plans.max_tags IS
    'UC017 9.1 — trần số thẻ phân loại của một doanh nghiệp. Kiểm bằng COUNT trên '
    'engagement.tags lúc tạo thẻ mới, không cộng dồn vào usage_records: đây là con số tức thời, '
    'không phải mức tiêu thụ theo chu kỳ.';

-- Không GRANT: crm_app chỉ có SELECT trên bảng này (V111 mục 1), và ADD COLUMN kế thừa.
-- Bảng không bật RLS — danh mục cấp nền tảng, mọi tenant đọc chung (ERD mục 13).
