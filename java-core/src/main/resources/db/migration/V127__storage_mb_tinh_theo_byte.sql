-- V127 — STORAGE_MB tính theo BYTE ở cả luồng đăng ký (ADR-0023 (c)). UC001 · UC018
--
-- VẤN ĐỀ: register_tenant (V118) ghi trần STORAGE_MB = subscription_plans.storage_mb nguyên văn,
-- tức số MB. UC018 hiểu cột này theo BYTE (V126, UsageRecordRepository.insertIfAbsent nhân
-- 1048576), và insertIfAbsent gặp dòng có sẵn thì ON CONFLICT DO NOTHING — nên doanh nghiệp đăng
-- ký qua luồng thật có trần 100 BYTE với gói TRIAL: tệp 1 KB đã bị 409 STORAGE_MB_QUOTA_EXCEEDED.
--
-- GIẢI PHÁP: thay thân hàm, đổi đúng một biểu thức (bước 5, dòng STORAGE_MB); mọi thứ khác giữ
-- nguyên V118. CREATE OR REPLACE giữ chủ sở hữu, quyền và COMMENT của hàm.

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

    -- 5. Tạo usage records. STORAGE_MB đổi MB của gói sang BYTE — V127, ADR-0023 (c).
    INSERT INTO platform.usage_records (id, tenant_id, subscription_id, metric, used_value, quota_value, created_at, updated_at)
    VALUES
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'CONVERSATION',  0, v_plan.conversation_quota,        v_now, v_now),
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'AI_TOKEN',      0, v_plan.ai_token_quota,            v_now, v_now),
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'DOCUMENT',      0, v_plan.max_documents,             v_now, v_now),
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'STORAGE_MB',    0, v_plan.storage_mb::bigint * 1048576, v_now, v_now),
        (gen_random_uuid(), p_tenant_id, v_sub_id, 'USER',          0, v_plan.max_users,                 v_now, v_now);

    RETURN QUERY SELECT p_tenant_id, p_slug, v_user_id, p_email;
END $$;

REVOKE ALL ON FUNCTION platform.register_tenant(uuid, varchar, varchar, varchar, varchar, varchar, varchar, varchar) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.register_tenant(uuid, varchar, varchar, varchar, varchar, varchar, varchar, varchar) TO crm_app;


-- Sửa các doanh nghiệp đã đăng ký trước V127: dòng STORAGE_MB còn mang đúng số MB của gói. Điều
-- kiện quota_value = storage_mb chỉ khớp dòng sai — dòng đúng (byte) lớn hơn hàng triệu lần.
-- Flyway chạy bằng crm_owner (rolbypassrls) nên thấy mọi tenant.
UPDATE platform.usage_records u
   SET quota_value = p.storage_mb::bigint * 1048576
  FROM platform.tenant_subscriptions s
  JOIN platform.subscription_plans p ON p.id = s.plan_id
 WHERE u.subscription_id = s.id
   AND u.metric = 'STORAGE_MB'
   AND p.storage_mb > 0
   AND u.quota_value = p.storage_mb;
