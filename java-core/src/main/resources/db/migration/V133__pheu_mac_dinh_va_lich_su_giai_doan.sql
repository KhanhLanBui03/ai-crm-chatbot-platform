-- UC033 + UC034 — phễu mặc định cho mọi doanh nghiệp và lịch sử chuyển giai đoạn của Deal.
--
-- ⚠ Số V133 đặt TẠM: Dev A định dùng V133 cho 3 cột sales.lead_scores. Ai merge vào develop trước
-- lấy số trước — nhánh sau đổi sang số kế tiếp TRƯỚC khi merge (Flyway chặn trùng số và chặn số nhỏ
-- tới sau số lớn đã chạy).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Lịch sử chuyển giai đoạn (UC034 bước 6)
--
-- Mỗi lần kéo deal ghi MỘT dòng, kèm số giây deal đã nằm ở giai đoạn trước — tính sẵn lúc ghi để báo
-- cáo "trung bình mỗi giai đoạn mất bao lâu" (UC037) chỉ cần AVG, không phải chạy hàm cửa sổ.
-- Dòng đầu tiên (from_stage_id NULL) là lúc deal được tạo.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE sales.deal_stage_history (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid        NOT NULL REFERENCES platform.tenants (id),
    deal_id          uuid        NOT NULL,
    from_stage_id    uuid,
    to_stage_id      uuid        NOT NULL,
    duration_seconds bigint      CHECK (duration_seconds >= 0),
    changed_by       uuid,
    changed_at       timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_dsh_deal FOREIGN KEY (deal_id, tenant_id)
        REFERENCES sales.deals (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_dsh_from FOREIGN KEY (from_stage_id, tenant_id)
        REFERENCES sales.deal_stages (id, tenant_id),
    CONSTRAINT fk_dsh_to FOREIGN KEY (to_stage_id, tenant_id)
        REFERENCES sales.deal_stages (id, tenant_id),
    CONSTRAINT fk_dsh_user FOREIGN KEY (changed_by, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    CONSTRAINT ck_dsh_first CHECK ((from_stage_id IS NULL) = (duration_seconds IS NULL))
);

CREATE INDEX ix_dsh_deal ON sales.deal_stage_history (tenant_id, deal_id, changed_at);

GRANT SELECT, INSERT, UPDATE, DELETE ON sales.deal_stage_history TO crm_app;

ALTER TABLE sales.deal_stage_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales.deal_stage_history FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON sales.deal_stage_history
    USING      (tenant_id = platform.current_tenant())
    WITH CHECK (tenant_id = platform.current_tenant());

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Phễu mặc định 5 giai đoạn
--
-- Không có phễu thì bảng Deal không có cột nào và không chuyển được lead thành deal. Chưa có màn sửa
-- giai đoạn (giảm độ sâu) nên mọi doanh nghiệp dùng cùng một bộ:
--   Mới tiếp nhận → Đã báo giá (bắt buộc có giá trị) → Thương lượng → Thắng / Thua
--
-- RLS của sales.pipelines/deal_stages là FORCE, nên hàm tự đặt app.tenant_id = doanh nghiệp đang
-- tạo rồi TRẢ LẠI giá trị cũ — chạy được cả trong migration lẫn trong giao dịch đăng ký doanh nghiệp.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE FUNCTION sales.tao_pheu_mac_dinh(p_tenant uuid) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    cu  text := current_setting('app.tenant_id', true);
    pid uuid;
BEGIN
    PERFORM set_config('app.tenant_id', p_tenant::text, true);
    IF NOT EXISTS (SELECT 1 FROM sales.pipelines WHERE tenant_id = p_tenant AND is_default) THEN
        INSERT INTO sales.pipelines (tenant_id, name, is_default)
        VALUES (p_tenant, 'Phễu bán hàng', true)
        RETURNING id INTO pid;
        INSERT INTO sales.deal_stages (tenant_id, pipeline_id, name, position, is_won, is_lost, required_fields)
        VALUES (p_tenant, pid, 'Mới tiếp nhận', 0, false, false, '{}'),
               (p_tenant, pid, 'Đã báo giá',    1, false, false, '{amount}'),
               (p_tenant, pid, 'Thương lượng',  2, false, false, '{}'),
               (p_tenant, pid, 'Thắng',         3, true,  false, '{}'),
               (p_tenant, pid, 'Thua',          4, false, true,  '{}');
    END IF;
    PERFORM set_config('app.tenant_id', coalesce(cu, ''), true);
END $$;

CREATE FUNCTION sales.trg_tenant_tao_pheu() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM sales.tao_pheu_mac_dinh(NEW.id);
    RETURN NEW;
END $$;

CREATE TRIGGER trg_tenant_tao_pheu AFTER INSERT ON platform.tenants
    FOR EACH ROW EXECUTE FUNCTION sales.trg_tenant_tao_pheu();

-- Doanh nghiệp đã có trước migration này
DO $$
DECLARE t uuid;
BEGIN
    FOR t IN SELECT id FROM platform.tenants LOOP
        PERFORM sales.tao_pheu_mac_dinh(t);
    END LOOP;
END $$;

COMMENT ON FUNCTION sales.tao_pheu_mac_dinh(uuid) IS
    'UC034 — phễu 5 giai đoạn mặc định. Gọi lại an toàn: đã có phễu mặc định thì không làm gì.';
