-- UC032 — Quản lý Lead: mỗi khách tối đa MỘT lead đang mở (Mới / Đã liên hệ / Đủ tiềm năng).
--
-- Vì sao chặn ở CSDL chứ không chỉ kiểm trong code: hai nhân viên bấm "Tạo lead" cho cùng một khách
-- trong cùng một giây thì cả hai lần kiểm "đã có lead mở chưa?" đều thấy CHƯA — chỉ ràng buộc duy
-- nhất mới chặn được lần thứ hai. Hai lead mở của một khách làm phễu (UC037) đếm đôi và hai người
-- cùng gọi một khách.
--
-- Lead đã loại (DISQUALIFIED) hoặc đã thành Deal (CONVERTED) nằm ngoài điều kiện, nên khách quay lại
-- sau này vẫn tạo được lead mới. Mở lại một lead đã loại cũng đi qua chỉ mục này.
CREATE UNIQUE INDEX uq_leads_mot_lead_mo_moi_khach
    ON sales.leads (tenant_id, contact_id)
    WHERE status IN ('NEW', 'CONTACTED', 'QUALIFIED');

-- ─────────────────────────────────────────────────────────────────────────────
-- Sửa lỗi V108: khoá ngoại KÉP (cột_id, tenant_id) kèm ON DELETE SET NULL
--
-- "SET NULL" không ghi cột nào thì Postgres đặt NULL cho CẢ HAI cột của khoá — kể cả tenant_id
-- (NOT NULL) → xoá hội thoại mà có lead trỏ tới là lỗi "null value in column tenant_id". Nghĩa là
-- yêu cầu xoá dữ liệu cá nhân (UC041) KHÔNG xoá được hội thoại nào đã sinh lead. Phát hiện khi viết
-- test UC032 luồng 6.1 ("hội thoại nguồn đã bị xoá").
--
-- Postgres 15+ cho ghi đích danh cột cần đặt NULL. Cùng lỗi ở hai khoá của sales.activities (xoá lead
-- hoặc deal có hoạt động gắn kèm) — sửa luôn một lần.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE sales.leads
    DROP CONSTRAINT fk_leads_conversation,
    ADD CONSTRAINT fk_leads_conversation FOREIGN KEY (source_conversation_id, tenant_id)
        REFERENCES engagement.conversations (id, tenant_id) ON DELETE SET NULL (source_conversation_id);

ALTER TABLE sales.activities
    DROP CONSTRAINT fk_act_lead,
    ADD CONSTRAINT fk_act_lead FOREIGN KEY (lead_id, tenant_id)
        REFERENCES sales.leads (id, tenant_id) ON DELETE SET NULL (lead_id),
    DROP CONSTRAINT fk_act_deal,
    ADD CONSTRAINT fk_act_deal FOREIGN KEY (deal_id, tenant_id)
        REFERENCES sales.deals (id, tenant_id) ON DELETE SET NULL (deal_id);
