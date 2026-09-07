-- V102 — Doanh nghiệp thuê bao, danh mục gói, thuê bao theo chu kỳ, mức sử dụng.
-- UC001 · UC004 · UC005 · UC006 · UC007

-- ─────────────────────────────────────────────────────────────────────────────
-- tenants — gốc của mọi dữ liệu nghiệp vụ.
-- Không có cột tenant_id: chính nó LÀ tenant. Policy RLS so id (V110).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE platform.tenants (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 varchar(200) NOT NULL,
    slug                 varchar(64)  NOT NULL UNIQUE,
    industry             varchar(100),
    contact_email        varchar(255) NOT NULL,
    phone                varchar(20),
    timezone             varchar(64)  NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
    locale               varchar(10)  NOT NULL DEFAULT 'vi-VN',
    business_hours       jsonb        NOT NULL DEFAULT '{}'::jsonb,
    ai_tone              varchar(30)  NOT NULL DEFAULT 'FRIENDLY'
                         CHECK (ai_tone IN ('PROFESSIONAL','FRIENDLY','CONCISE')),
    lead_score_threshold smallint     NOT NULL DEFAULT 70
                         CHECK (lead_score_threshold BETWEEN 0 AND 100),
    auto_lead_creation   boolean      NOT NULL DEFAULT true,
    status               varchar(30)  NOT NULL DEFAULT 'TRIAL'
                         CHECK (status IN ('TRIAL','ACTIVE','SUSPENDED','EXPIRED')),
    suspended_reason     text,
    suspended_at         timestamptz,
    created_at           timestamptz  NOT NULL DEFAULT now(),
    updated_at           timestamptz  NOT NULL DEFAULT now(),

    -- UC007 bước 8–9: khoá doanh nghiệp thì bắt buộc nhập lý do.
    CONSTRAINT ck_tenants_suspended
        CHECK (status <> 'SUSPENDED' OR suspended_reason IS NOT NULL)
);

COMMENT ON COLUMN platform.tenants.slug IS
    'Mã trên URL. Máy chủ sinh từ tên doanh nghiệp rồi bảo đảm duy nhất — không nhận từ phía gọi.';
COMMENT ON COLUMN platform.tenants.lead_score_threshold IS
    'UC030 bước 7: vượt ngưỡng thì UC031 tự tạo Lead.';

-- ─────────────────────────────────────────────────────────────────────────────
-- subscription_plans — danh mục cấp nền tảng.
-- NGOẠI LỆ: không có tenant_id, không bật RLS. Mọi tenant đọc chung, chỉ quản
-- trị nền tảng được ghi (V109 chỉ cấp SELECT cho crm_app).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE platform.subscription_plans (
    id                uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    code              varchar(30)   NOT NULL UNIQUE
                      CHECK (code IN ('TRIAL','STARTER','GROWTH','PRO')),
    name              varchar(100)  NOT NULL,
    monthly_price_vnd numeric(14,2) NOT NULL CHECK (monthly_price_vnd >= 0),
    conversation_quota int          NOT NULL CHECK (conversation_quota >= 0),
    ai_token_quota    bigint        NOT NULL CHECK (ai_token_quota >= 0),
    max_users         int           NOT NULL CHECK (max_users > 0),
    max_documents     int           NOT NULL CHECK (max_documents >= 0),
    max_channels      smallint      NOT NULL CHECK (max_channels > 0),
    storage_mb        int           NOT NULL CHECK (storage_mb >= 0),
    is_active         boolean       NOT NULL DEFAULT true,
    sort_order        smallint      NOT NULL,
    created_at        timestamptz   NOT NULL DEFAULT now(),
    updated_at        timestamptz   NOT NULL DEFAULT now()
);

COMMENT ON COLUMN platform.subscription_plans.is_active IS
    'Gói ngừng bán vẫn phải giữ: thuê bao cũ còn tham chiếu tới nó.';

INSERT INTO platform.subscription_plans
    (code, name, monthly_price_vnd, conversation_quota, ai_token_quota,
     max_users, max_documents, max_channels, storage_mb, sort_order)
VALUES
    ('TRIAL',   'Dùng thử 14 ngày',        0,       200,    500000,  3,  20,  1,   100, 1),
    ('STARTER', 'Khởi đầu',          490000,      2000,   5000000,  5,  100, 2,   500, 2),
    ('GROWTH',  'Tăng trưởng',      1490000,      8000,  20000000, 15,  500, 3,  2000, 3),
    ('PRO',     'Chuyên nghiệp',    3990000,     30000,  80000000, 50, 2000, 3, 10000, 4);

-- ─────────────────────────────────────────────────────────────────────────────
-- tenant_subscriptions — thuê bao theo chu kỳ.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE platform.tenant_subscriptions (
    id                     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              uuid        NOT NULL REFERENCES platform.tenants (id),
    plan_id                uuid        NOT NULL REFERENCES platform.subscription_plans (id),
    status                 varchar(30) NOT NULL DEFAULT 'TRIALING'
                           CHECK (status IN ('TRIALING','ACTIVE','PAST_DUE','EXPIRED','CANCELED')),
    period_start           timestamptz NOT NULL,
    period_end             timestamptz NOT NULL,
    auto_renew             boolean     NOT NULL DEFAULT true,
    scheduled_plan_id      uuid        REFERENCES platform.subscription_plans (id),
    scheduled_effective_at timestamptz,
    canceled_at            timestamptz,
    changed_by             uuid,   -- FK sang users thêm ở V103 (users tạo sau)
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_subscription_period UNIQUE (tenant_id, period_start),
    CONSTRAINT ck_subscription_period CHECK (period_end > period_start),
    -- cho phép usage_records khai khoá ngoại phức hợp
    CONSTRAINT uq_subscription_tenant UNIQUE (id, tenant_id)
);

CREATE INDEX ix_subscription_tenant_status
    ON platform.tenant_subscriptions (tenant_id, status);

COMMENT ON COLUMN platform.tenant_subscriptions.scheduled_plan_id IS
    'UC005: hạ gói chỉ hiệu lực từ chu kỳ kế tiếp — không cắt dữ liệu giữa chu kỳ đã trả tiền.';

-- ─────────────────────────────────────────────────────────────────────────────
-- usage_records — mức tiêu thụ so với hạn mức, theo chu kỳ và theo chỉ số.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE platform.usage_records (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          uuid        NOT NULL REFERENCES platform.tenants (id),
    subscription_id    uuid        NOT NULL,
    metric             varchar(30) NOT NULL
                       CHECK (metric IN ('CONVERSATION','AI_TOKEN','DOCUMENT','STORAGE_MB','USER')),
    used_value         bigint      NOT NULL DEFAULT 0 CHECK (used_value >= 0),
    quota_value        bigint      NOT NULL CHECK (quota_value >= 0),
    last_calculated_at timestamptz,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_usage_metric UNIQUE (subscription_id, metric),
    CONSTRAINT fk_usage_subscription FOREIGN KEY (subscription_id, tenant_id)
        REFERENCES platform.tenant_subscriptions (id, tenant_id)
);

CREATE INDEX ix_usage_tenant ON platform.usage_records (tenant_id, metric);

COMMENT ON COLUMN platform.usage_records.quota_value IS
    'Sao chép từ gói lúc mở chu kỳ, KHÔNG đọc qua plan_id. Đây là dữ kiện lịch sử của chu kỳ; '
    'đổi gói giữa chừng mà đọc qua khoá ngoại thì báo cáo chu kỳ cũ sai ngay.';
