-- V112 — Row-Level Security. ADR-0001, bề mặt T1.
--
-- HAI CÁI BẪY làm RLS mất tác dụng HOÀN TOÀN trong khi test vẫn xanh:
--   1. Chỉ ENABLE mà quên FORCE  -> chủ bảng vẫn đọc hết mọi tenant.
--   2. Chạy runtime bằng crm_owner -> chủ bảng bypass RLS.
-- Cả hai đều không có thông báo lỗi nào. Mục kiểm 2 ở erd-ai-crm.md là cách phát hiện.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Mười chín bảng theo khuôn chuẩn: tenant_id = platform.current_tenant()
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
    full_name text;
    tbl       text[] := ARRAY[
        'platform.users',            'platform.user_roles',
        'platform.tenant_subscriptions', 'platform.usage_records',
        'platform.audit_logs',       'platform.data_erasure_requests',
        'engagement.contacts',       'engagement.tags',
        'engagement.contact_tags',   'engagement.contact_notes',
        'engagement.channels',       'engagement.channel_identities',
        'engagement.conversations',  'engagement.messages',
        'sales.pipelines',           'sales.deal_stages',
        'sales.leads',               'sales.deals',
        'sales.activities'
    ];
BEGIN
    FOREACH full_name IN ARRAY tbl LOOP
        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', full_name);
        EXECUTE format('ALTER TABLE %s FORCE  ROW LEVEL SECURITY', full_name);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %s
                USING      (tenant_id = platform.current_tenant())
                WITH CHECK (tenant_id = platform.current_tenant())
        $f$, full_name);
    END LOOP;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. tenants — so id, vì chính nó LÀ tenant
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE platform.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform.tenants FORCE  ROW LEVEL SECURITY;

CREATE POLICY tenant_self ON platform.tenants
    USING      (id = platform.current_tenant())
    WITH CHECK (id = platform.current_tenant());

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. roles — vai trò hệ thống (tenant_id NULL) phải ĐỌC được từ mọi tenant
--
-- Dùng khuôn chuẩn ở đây là hỏng: TENANT_ADMIN và AGENT có tenant_id NULL, phép
-- so NULL = <uuid> trả về NULL, nên KHÔNG tenant nào thấy vai trò nào — đăng nhập
-- không phân quyền được. Đọc thì mở, ghi thì vẫn khoá theo tenant.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE platform.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform.roles FORCE  ROW LEVEL SECURITY;

CREATE POLICY role_read ON platform.roles FOR SELECT
    USING (tenant_id IS NULL OR tenant_id = platform.current_tenant());

CREATE POLICY role_write ON platform.roles FOR ALL
    USING      (tenant_id = platform.current_tenant())
    WITH CHECK (tenant_id = platform.current_tenant());

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Ba bảng KHÔNG bật RLS — có chủ ý, không phải bỏ sót
--
--   subscription_plans  danh mục cấp nền tảng, không có tenant_id, mọi tenant đọc chung.
--   outbox_events       job phát sự kiện chạy nền, KHÔNG có ngữ cảnh tenant và phải
--                       quét được mọi dòng chưa phát. Bật RLS ở đây thì poller không
--                       thấy gì và sự kiện đọng lại vĩnh viễn mà không báo lỗi.
--   processed_events    cùng lý do — consumer kiểm trùng trước khi biết tenant.
--
-- Bù lại: hai bảng hạ tầng không bao giờ được truy vấn từ mã theo yêu cầu người
-- dùng. Chúng chỉ có ở tầng worker.
-- ─────────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Đường đăng nhập — chỗ RLS không thể áp
--
-- Lúc đăng nhập, hệ thống chưa biết tenant: người dùng mới chỉ gõ email. Với RLS
-- FORCE và app.tenant_id chưa đặt, câu SELECT ... WHERE email = ? trả về RỖNG, và
-- không ai đăng nhập được. Đây là hệ quả trực tiếp của việc siết cô lập ở tầng CSDL.
--
-- Lời giải: một hàm SECURITY DEFINER thuộc sở hữu crm_owner, trả về ĐÚNG những cột
-- cần cho việc xác thực. crm_app gọi hàm, không đọc thẳng bảng. Bề mặt lộ ra là một
-- hàm có chữ ký cố định thay vì quyền đọc toàn bảng.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE FUNCTION platform.find_login_identity(p_email text)
RETURNS TABLE (
    user_id           uuid,
    tenant_id         uuid,
    tenant_slug       varchar(64),
    tenant_status     varchar(30),
    password_hash     varchar(255),
    scope             varchar(20),
    status            varchar(30),
    email_verified_at timestamptz,
    failed_login_count smallint,
    locked_until      timestamptz
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = platform, pg_temp
STABLE
AS $$
    SELECT u.id, u.tenant_id, t.slug, t.status,
           u.password_hash, u.scope, u.status,
           u.email_verified_at, u.failed_login_count, u.locked_until
      FROM platform.users u
      LEFT JOIN platform.tenants t ON t.id = u.tenant_id
     WHERE lower(u.email) = lower(p_email)
       AND u.deleted_at IS NULL;
$$;

REVOKE ALL ON FUNCTION platform.find_login_identity(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.find_login_identity(text) TO crm_app;

COMMENT ON FUNCTION platform.find_login_identity(text) IS
    'SECURITY DEFINER: chạy bằng quyền crm_owner nên bỏ qua RLS. Chỉ dùng cho bước xác thực, '
    'khi chưa biết tenant. KHÔNG trả về bất kỳ dữ liệu nghiệp vụ nào ngoài thông tin đăng nhập. '
    'Sau khi xác thực xong, mọi truy vấn tiếp theo đi qua RLS như bình thường.';

-- Cùng lý do: đăng ký và nhúng widget cần tra doanh nghiệp khi chưa có JWT.
CREATE FUNCTION platform.slug_is_taken(p_slug text)
RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path = platform, pg_temp STABLE
AS $$ SELECT EXISTS (SELECT 1 FROM platform.tenants WHERE slug = lower(p_slug)); $$;

REVOKE ALL ON FUNCTION platform.slug_is_taken(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.slug_is_taken(text) TO crm_app;

CREATE FUNCTION engagement.resolve_widget_key(p_widget_key text)
RETURNS TABLE (channel_id uuid, tenant_id uuid, config jsonb, status varchar(30))
LANGUAGE sql SECURITY DEFINER SET search_path = engagement, pg_temp STABLE
AS $$
    SELECT c.id, c.tenant_id, c.config, c.status
      FROM engagement.channels c
     WHERE c.widget_key = p_widget_key AND c.type = 'WEB_WIDGET';
$$;

REVOKE ALL ON FUNCTION engagement.resolve_widget_key(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION engagement.resolve_widget_key(text) TO crm_app;

COMMENT ON FUNCTION engagement.resolve_widget_key(text) IS
    'Web Widget gọi từ trình duyệt khách, chưa có ngữ cảnh tenant. Trả về tenant_id để gateway '
    'gắn vào ngữ cảnh cho các lời gọi sau. Bề mặt T2 — không trả bất kỳ dữ liệu hội thoại nào.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. Gắn trigger chạm updated_at cho mọi bảng có cột đó
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE r record;
BEGIN
    FOR r IN
        SELECT c.table_schema, c.table_name
          FROM information_schema.columns c
          JOIN information_schema.tables t
            ON t.table_schema = c.table_schema AND t.table_name = c.table_name
         WHERE c.column_name = 'updated_at'
           AND t.table_type = 'BASE TABLE'
           AND c.table_schema IN ('platform','engagement','sales','analytics')
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_touch_updated_at BEFORE UPDATE ON %I.%I
               FOR EACH ROW EXECUTE FUNCTION platform.touch_updated_at()',
            r.table_schema, r.table_name);
    END LOOP;
END $$;
