-- V116 — Hàm SECURITY DEFINER kiểm tra email duy nhất toàn hệ thống khi chưa có tenant_id (đăng ký).
CREATE OR REPLACE FUNCTION platform.email_is_taken(p_email text)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = platform, pg_temp
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
          FROM platform.users
         WHERE lower(email) = lower(p_email)
           AND deleted_at IS NULL
    );
$$;

REVOKE ALL ON FUNCTION platform.email_is_taken(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.email_is_taken(text) TO crm_app;

-- Cho phép tạo tenant mới (INSERT) khi đăng ký:
DROP POLICY IF EXISTS tenant_self ON platform.tenants;

CREATE POLICY tenant_select ON platform.tenants FOR SELECT
    USING (id = platform.current_tenant());

CREATE POLICY tenant_update ON platform.tenants FOR UPDATE
    USING (id = platform.current_tenant())
    WITH CHECK (id = platform.current_tenant());

CREATE POLICY tenant_delete ON platform.tenants FOR DELETE
    USING (id = platform.current_tenant());

CREATE POLICY tenant_insert ON platform.tenants FOR INSERT
    WITH CHECK (true);


