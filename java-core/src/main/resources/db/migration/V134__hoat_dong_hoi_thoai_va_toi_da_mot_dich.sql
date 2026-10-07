-- UC035 — Hoạt động chăm sóc khách và nhắc việc.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Gắn TỐI ĐA một lead hoặc deal
--
-- Hợp đồng cũ ghi "đúng một" nhưng V108 chưa từng có ràng buộc nào. Đã chốt với người dùng: hoạt
-- động có thể chỉ thuộc HỒ SƠ KHÁCH (vd. khách vãng lai chưa thành lead được chuyển từ AI sang nhân
-- viên) — nên là "tối đa một": cấm gắn cùng lúc cả lead lẫn deal, cho phép không gắn cái nào.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE sales.activities
    ADD CONSTRAINT ck_act_toi_da_mot_dich CHECK (num_nonnulls(lead_id, deal_id) <= 1);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Hội thoại gốc của hoạt động
--
-- Hoạt động AUTO ("Tiếp nhận hội thoại từ AI") cần đường dẫn mở thẳng hội thoại. Hội thoại bị xoá
-- theo yêu cầu xoá dữ liệu cá nhân (UC041) thì chỉ mất liên kết — SET NULL ĐÍCH DANH cột, không đụng
-- tenant_id (bài học V132).
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE sales.activities
    ADD COLUMN conversation_id uuid,
    ADD CONSTRAINT fk_act_conversation FOREIGN KEY (conversation_id, tenant_id)
        REFERENCES engagement.conversations (id, tenant_id) ON DELETE SET NULL (conversation_id);

-- Tab "Hoạt động" của trang Lead (deal và khách đã có chỉ mục từ V108)
CREATE INDEX ix_act_lead ON sales.activities (tenant_id, lead_id, created_at DESC);

COMMENT ON COLUMN sales.activities.conversation_id IS
    'Hội thoại gốc — có ở hoạt động AUTO sinh khi nhân viên nhận hội thoại từ AI (UC035).';
