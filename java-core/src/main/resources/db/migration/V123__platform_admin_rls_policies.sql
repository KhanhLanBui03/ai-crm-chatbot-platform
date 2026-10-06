-- V123 — Cập nhật chính sách RLS cho phép Quản trị viên Nền tảng (Platform Admin) truy vấn đa tenant.
--
-- Khi chạy bằng vai trò PLATFORM_ADMIN (app.is_platform_admin = 'true'),
-- các bảng thuộc schema platform, analytics, engagement cho phép đọc/ghi dữ liệu toàn hệ thống.

-- 1. Cập nhật hàm platform.current_tenant() để không ném lỗi khi là PLATFORM_ADMIN
CREATE OR REPLACE FUNCTION platform.current_tenant() RETURNS uuid
LANGUAGE plpgsql STABLE AS $$
DECLARE v text := current_setting('app.tenant_id', true);
BEGIN
    IF current_setting('app.is_platform_admin', true) = 'true' THEN
        RETURN NULL;
    END IF;
    IF v IS NULL OR v = '' THEN
        RAISE EXCEPTION
            'Chưa đặt app.tenant_id. Mọi truy vấn nghiệp vụ phải chạy trong ngữ cảnh tenant '
            '(java-core: filter ở security/; ai-service: app/db/session.py).'
            USING ERRCODE = '42501';
    END IF;
    RETURN v::uuid;
END $$;

-- 2. Cập nhật Policy cho platform.tenants
DROP POLICY IF EXISTS tenant_self ON platform.tenants;
CREATE POLICY tenant_self ON platform.tenants
    USING (current_setting('app.is_platform_admin', true) = 'true' OR id = platform.current_tenant())
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true' OR id = platform.current_tenant());

-- 3. Cập nhật Policy cho platform.users
DROP POLICY IF EXISTS tenant_isolation ON platform.users;
CREATE POLICY tenant_isolation ON platform.users
    USING (current_setting('app.is_platform_admin', true) = 'true' OR scope = 'PLATFORM' OR tenant_id = platform.current_tenant())
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true' OR scope = 'PLATFORM' OR tenant_id = platform.current_tenant());

-- 4. Cập nhật Policy cho platform.tenant_subscriptions
DROP POLICY IF EXISTS tenant_isolation ON platform.tenant_subscriptions;
CREATE POLICY tenant_isolation ON platform.tenant_subscriptions
    USING (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = platform.current_tenant())
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = platform.current_tenant());

-- 5. Cập nhật Policy cho platform.usage_records
DROP POLICY IF EXISTS tenant_isolation ON platform.usage_records;
DROP POLICY IF EXISTS usage_records_isolation ON platform.usage_records;
CREATE POLICY usage_records_isolation ON platform.usage_records
    USING (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = platform.current_tenant())
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = platform.current_tenant());

-- 6. Cập nhật Policy cho engagement.conversations (để thống kê số hội thoại)
DROP POLICY IF EXISTS tenant_isolation ON engagement.conversations;
CREATE POLICY tenant_isolation ON engagement.conversations
    USING (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = platform.current_tenant())
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = platform.current_tenant());

-- 7. Cập nhật Policy cho platform.audit_logs
DROP POLICY IF EXISTS tenant_isolation ON platform.audit_logs;
CREATE POLICY tenant_isolation ON platform.audit_logs
    USING (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = platform.current_tenant())
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = platform.current_tenant());
