-- V118 — Hàm SECURITY DEFINER cho toàn bộ luồng đăng ký tenant mới.
--
-- VẤN ĐỀ: Hibernate dùng connection pool (HikariCP), và khi flush nó có thể:
--   1. Mất biến phiên app.tenant_id giữa các câu INSERT.
--   2. Thực hiện SELECT sau INSERT (để lấy generated ID) → kích hoạt RLS SELECT policy.
-- Cả hai đều gây lỗi "violates row-level security policy" mà không thể sửa bằng
-- cách chỉnh policy INSERT, vì vấn đề nằm ở tầng ORM + connection pool.
--
-- GIẢI PHÁP: Giống find_login_identity và email_is_taken, ta tạo một hàm SECURITY DEFINER
-- chạy bằng quyền crm_owner. Hàm này thực hiện TẤT CẢ INSERT cần thiết trong một lời gọi
-- duy nhất, hoàn toàn bỏ qua RLS. Java chỉ gọi hàm, không dùng JPA repository.

-- Xoá V117 policies — ta giữ nguyên tenant_isolation gốc từ V112, chỉ bypass qua hàm này.
-- (Nếu V117 đã chạy, các policy cũ đã bị DROP, ta cần tạo lại tenant_isolation.)
DO $$
DECLARE
    tbl text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'platform.users', 'platform.user_roles',
        'platform.tenant_subscriptions', 'platform.usage_records'
    ] LOOP
        -- Drop V117 policies nếu tồn tại
        EXECUTE format('DROP POLICY IF EXISTS %I_select ON %s', split_part(tbl, '.', 2), tbl);
        EXECUTE format('DROP POLICY IF EXISTS %I_update ON %s', split_part(tbl, '.', 2), tbl);
        EXECUTE format('DROP POLICY IF EXISTS %I_delete ON %s', split_part(tbl, '.', 2), tbl);
        EXECUTE format('DROP POLICY IF EXISTS %I_insert ON %s', split_part(tbl, '.', 2), tbl);

        -- Tạo lại tenant_isolation nếu chưa có (V112 đã tạo, V117 đã xoá)
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %s', tbl);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %s
                USING      (tenant_id = platform.current_tenant())
                WITH CHECK (tenant_id = platform.current_tenant())
        $f$, tbl);
    END LOOP;
END $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- Hàm đăng ký tenant mới — SECURITY DEFINER, bypass RLS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION platform.register_tenant(
    p_tenant_id      uuid,
    p_company_name   varchar(200),
    p_slug           varchar(64),
    p_email          varchar(255),
    p_password_hash  varchar(255),
    p_full_name      varchar(200),
    p_industry       varchar(100),
    p_timezone       varchar(64)
)
RETURNS TABLE (
    tenant_id   uuid,
    tenant_slug varchar(64),
    user_id     uuid,
    user_email  varchar(255)
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = platform, pg_temp
AS $$
#variable_conflict use_column
DECLARE
    v_user_id   uuid;
    v_role_id   uuid;
    v_plan_id   uuid;
    v_sub_id    uuid;
    v_now       timestamptz := now();
    v_period_end timestamptz := now() + interval '14 days';
    v_plan      record;
BEGIN
    -- 1. Tạo tenant
    INSERT INTO platform.tenants (id, name, slug, contact_email, industry, timezone, status, created_at, updated_at)
    VALUES (p_tenant_id, p_company_name, p_slug, p_email, p_industry,
            COALESCE(NULLIF(p_timezone, ''), 'Asia/Ho_Chi_Minh'), 'TRIAL', v_now, v_now);

    -- 2. Tạo user admin
    v_user_id := gen_random_uuid();
    INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, scope, status, created_at, updated_at)
    VALUES (v_user_id, p_tenant_id, p_email, p_password_hash, p_full_name, 'TENANT', 'PENDING', v_now, v_now);

    -- 3. Gán vai trò TENANT_ADMIN
    SELECT roles.id INTO v_role_id FROM platform.roles WHERE roles.code = 'TENANT_ADMIN' AND roles.tenant_id IS NULL;
    IF v_role_id IS NULL THEN
        RAISE EXCEPTION 'Lỗi cấu hình hệ thống: Không tìm thấy vai trò TENANT_ADMIN';
    END IF;

    INSERT INTO platform.user_roles (user_id, role_id, tenant_id, granted_by, granted_at, created_at, updated_at)
    VALUES (v_user_id, v_role_id, p_tenant_id, v_user_id, v_now, v_now, v_now);

    -- 4. Tạo subscription TRIAL
    SELECT * INTO v_plan FROM platform.subscription_plans WHERE subscription_plans.code = 'TRIAL';
    IF v_plan.id IS NULL THEN
        RAISE EXCEPTION 'Lỗi cấu hình hệ thống: Không tìm thấy gói TRIAL';
    END IF;

    v_sub_id := gen_random_uuid();
    INSERT INTO platform.tenant_subscriptions (id, tenant_id, plan_id, status, period_start, period_end, auto_renew, changed_by, created_at, updated_at)
    VALUES (v_sub_id, p_tenant_id, v_plan.id, 'TRIALING', v_now, v_period_end, true, v_user_id, v_now, v_now);

    -- 5. Tạo usage records
    INSERT INTO platform.usage_records (id, tenant_id, subscription_id, metric, used_value, quota_value, created_at, updated_at)
    VALUES
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'CONVERSATION',  0, v_plan.conversation_quota, v_now, v_now),
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'AI_TOKEN',      0, v_plan.ai_token_quota,     v_now, v_now),
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'DOCUMENT',      0, v_plan.max_documents,      v_now, v_now),
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'STORAGE_MB',    0, v_plan.storage_mb,         v_now, v_now),
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'USER',          0, v_plan.max_users,           v_now, v_now);

    RETURN QUERY SELECT p_tenant_id, p_slug, v_user_id, p_email;
END $$;

REVOKE ALL ON FUNCTION platform.register_tenant(uuid, varchar, varchar, varchar, varchar, varchar, varchar, varchar) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.register_tenant(uuid, varchar, varchar, varchar, varchar, varchar, varchar, varchar) TO crm_app;

COMMENT ON FUNCTION platform.register_tenant IS
    'SECURITY DEFINER: chạy bằng quyền crm_owner, bỏ qua RLS. '
    'Dùng khi tạo tenant mới — lúc này chưa có app.tenant_id trên phiên. '
    'Tất cả INSERT (tenants, users, user_roles, tenant_subscriptions, usage_records) '
    'chạy trong một lời gọi hàm duy nhất. Sau khi hàm trả về, mọi truy vấn tiếp '
    'theo đi qua RLS bình thường.';
