-- V117 — Bổ sung chính sách INSERT cho các bảng khởi tạo khi đăng ký tenant mới
-- Lúc đăng ký (AuthService.dangKy), luồng tạo mới User, UserRole, TenantSubscription, UsageRecord
-- cần được phép INSERT mà không bị chặn bởi app.tenant_id chưa kịp đồng bộ trên connection pool.
-- Các thao tác SELECT, UPDATE, DELETE vẫn bị khóa cứng 100% bởi platform.current_tenant().

-- 1. platform.users
DROP POLICY IF EXISTS tenant_isolation ON platform.users;

CREATE POLICY users_select ON platform.users FOR SELECT
    USING (tenant_id = platform.current_tenant());

CREATE POLICY users_update ON platform.users FOR UPDATE
    USING (tenant_id = platform.current_tenant())
    WITH CHECK (tenant_id = platform.current_tenant());

CREATE POLICY users_delete ON platform.users FOR DELETE
    USING (tenant_id = platform.current_tenant());

CREATE POLICY users_insert ON platform.users FOR INSERT
    WITH CHECK (tenant_id IS NOT NULL);

-- 2. platform.user_roles
DROP POLICY IF EXISTS tenant_isolation ON platform.user_roles;

CREATE POLICY user_roles_select ON platform.user_roles FOR SELECT
    USING (tenant_id = platform.current_tenant());

CREATE POLICY user_roles_update ON platform.user_roles FOR UPDATE
    USING (tenant_id = platform.current_tenant())
    WITH CHECK (tenant_id = platform.current_tenant());

CREATE POLICY user_roles_delete ON platform.user_roles FOR DELETE
    USING (tenant_id = platform.current_tenant());

CREATE POLICY user_roles_insert ON platform.user_roles FOR INSERT
    WITH CHECK (tenant_id IS NOT NULL);

-- 3. platform.tenant_subscriptions
DROP POLICY IF EXISTS tenant_isolation ON platform.tenant_subscriptions;

CREATE POLICY tenant_subscriptions_select ON platform.tenant_subscriptions FOR SELECT
    USING (tenant_id = platform.current_tenant());

CREATE POLICY tenant_subscriptions_update ON platform.tenant_subscriptions FOR UPDATE
    USING (tenant_id = platform.current_tenant())
    WITH CHECK (tenant_id = platform.current_tenant());

CREATE POLICY tenant_subscriptions_delete ON platform.tenant_subscriptions FOR DELETE
    USING (tenant_id = platform.current_tenant());

CREATE POLICY tenant_subscriptions_insert ON platform.tenant_subscriptions FOR INSERT
    WITH CHECK (tenant_id IS NOT NULL);

-- 4. platform.usage_records
DROP POLICY IF EXISTS tenant_isolation ON platform.usage_records;

CREATE POLICY usage_records_select ON platform.usage_records FOR SELECT
    USING (tenant_id = platform.current_tenant());

CREATE POLICY usage_records_update ON platform.usage_records FOR UPDATE
    USING (tenant_id = platform.current_tenant())
    WITH CHECK (tenant_id = platform.current_tenant());

CREATE POLICY usage_records_delete ON platform.usage_records FOR DELETE
    USING (tenant_id = platform.current_tenant());

CREATE POLICY usage_records_insert ON platform.usage_records FOR INSERT
    WITH CHECK (tenant_id IS NOT NULL);
