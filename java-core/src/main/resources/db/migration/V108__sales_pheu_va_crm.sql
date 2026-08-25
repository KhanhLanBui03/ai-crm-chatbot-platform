-- V108 — Phễu bán hàng, Lead, Deal, hoạt động chăm sóc.
-- UC029 · UC030 · UC031 · UC032 · UC033 · UC034 · UC035 · UC037

-- ─────────────────────────────────────────────────────────────────────────────
-- pipelines + deal_stages
--
-- Hợp đồng dashboard-api.yaml khai Deal.pipelineId và Deal.stageId là uuid BẮT
-- BUỘC, và GiaiDoanPheu là thực thể đầy đủ (position, probability, isWon, isLost,
-- requiredFields). Không phục vụ được bằng một cột enum cố định.
--
-- KHÔNG seed ở đây: hai bảng có tenant_id, mà lúc migration chạy chưa có tenant
-- nào. Phễu mặc định sinh trong luồng đăng ký doanh nghiệp (UC001).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE sales.pipelines (
    id         uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  uuid         NOT NULL REFERENCES platform.tenants (id),
    name       varchar(150) NOT NULL,
    is_default boolean      NOT NULL DEFAULT false,
    is_active  boolean      NOT NULL DEFAULT true,
    created_at timestamptz  NOT NULL DEFAULT now(),
    updated_at timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_pipelines_tenant UNIQUE (id, tenant_id),
    CONSTRAINT uq_pipelines_name   UNIQUE (tenant_id, name)
);

-- Mỗi doanh nghiệp có đúng một phễu mặc định.
CREATE UNIQUE INDEX uq_pipeline_default
    ON sales.pipelines (tenant_id) WHERE is_default;

CREATE TABLE sales.deal_stages (
    id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid         NOT NULL REFERENCES platform.tenants (id),
    pipeline_id     uuid         NOT NULL,
    name            varchar(100) NOT NULL,
    position        smallint     NOT NULL CHECK (position >= 0),
    probability     smallint     CHECK (probability BETWEEN 0 AND 100),
    is_won          boolean      NOT NULL DEFAULT false,
    is_lost         boolean      NOT NULL DEFAULT false,
    required_fields text[]       NOT NULL DEFAULT '{}',
    created_at      timestamptz  NOT NULL DEFAULT now(),
    updated_at      timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_stage_position UNIQUE (pipeline_id, position),
    CONSTRAINT uq_stage_tenant   UNIQUE (id, tenant_id),
    -- cho phép deals khai khoá ngoại (pipeline_id, stage_id) — xem bên dưới
    CONSTRAINT uq_stage_pipeline UNIQUE (pipeline_id, id),
    CONSTRAINT fk_stage_pipeline FOREIGN KEY (pipeline_id, tenant_id)
        REFERENCES sales.pipelines (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_stage_outcome CHECK (NOT (is_won AND is_lost))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- leads
--
-- Cột score do Track B ghi, nhưng ghi QUA API PUT /internal/leads/{id}/score
-- chứ không nối thẳng CSDL (ADR-0002). Đây là ngoại lệ liên làn duy nhất.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE sales.leads (
    id                     uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              uuid          NOT NULL REFERENCES platform.tenants (id),
    contact_id             uuid          NOT NULL,
    source_conversation_id uuid,
    source                 varchar(30)   NOT NULL
                           CHECK (source IN ('AI_AUTO','MANUAL')),
    status                 varchar(30)   NOT NULL DEFAULT 'NEW'
                           CHECK (status IN ('NEW','CONTACTED','QUALIFIED',
                                             'CONVERTED','DISQUALIFIED')),
    interested_product     varchar(200),
    budget_min             numeric(18,2) CHECK (budget_min >= 0),
    budget_max             numeric(18,2) CHECK (budget_max >= 0),
    budget_confidence      varchar(10)   CHECK (budget_confidence IN ('LOW','MEDIUM','HIGH')),
    urgency                varchar(10)   CHECK (urgency IN ('LOW','MEDIUM','HIGH')),
    interest_summary       text,
    current_score          smallint      CHECK (current_score BETWEEN 0 AND 100),
    score_reason           jsonb,
    score_updated_at       timestamptz,
    owner_user_id          uuid,
    converted_at           timestamptz,
    disqualified_reason    varchar(200),
    created_at             timestamptz   NOT NULL DEFAULT now(),
    updated_at             timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT uq_leads_tenant UNIQUE (id, tenant_id),
    CONSTRAINT fk_leads_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id),
    -- Hội thoại bị xoá theo yêu cầu xoá dữ liệu cá nhân thì cơ hội vẫn còn, chỉ mất liên kết.
    CONSTRAINT fk_leads_conversation FOREIGN KEY (source_conversation_id, tenant_id)
        REFERENCES engagement.conversations (id, tenant_id) ON DELETE SET NULL,
    CONSTRAINT fk_leads_owner FOREIGN KEY (owner_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    CONSTRAINT ck_leads_budget CHECK (budget_min IS NULL OR budget_max IS NULL
                                      OR budget_max >= budget_min),
    CONSTRAINT ck_leads_scored CHECK ((current_score IS NULL) = (score_updated_at IS NULL))
);

CREATE INDEX ix_leads_priority
    ON sales.leads (tenant_id, status, current_score DESC NULLS LAST);
CREATE INDEX ix_leads_contact ON sales.leads (tenant_id, contact_id);
CREATE INDEX ix_leads_owner   ON sales.leads (tenant_id, owner_user_id, status);

COMMENT ON COLUMN sales.leads.score_reason IS
    'Các tín hiệu đóng góp và trọng số. Không có cột này thì điểm là con số không giải thích được.';
COMMENT ON COLUMN sales.leads.budget_confidence IS
    'Ngân sách lưu dưới dạng KHOẢNG kèm mức chắc chắn — khách hiếm khi nói một con số chính xác.';

-- ─────────────────────────────────────────────────────────────────────────────
-- deals
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE sales.deals (
    id                  uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid          NOT NULL REFERENCES platform.tenants (id),
    lead_id             uuid,
    contact_id          uuid          NOT NULL,
    pipeline_id         uuid          NOT NULL,
    stage_id            uuid          NOT NULL,
    title               varchar(200)  NOT NULL,
    status              varchar(20)   NOT NULL DEFAULT 'OPEN'
                        CHECK (status IN ('OPEN','WON','LOST')),
    source              varchar(20)   NOT NULL
                        CHECK (source IN ('AI_LEAD','MANUAL')),
    amount              numeric(18,2) CHECK (amount >= 0),
    currency            char(3)       NOT NULL DEFAULT 'VND',
    expected_close_date date,
    stage_changed_at    timestamptz   NOT NULL DEFAULT now(),
    closed_at           timestamptz,
    close_reason        varchar(200),
    owner_user_id       uuid,
    created_at          timestamptz   NOT NULL DEFAULT now(),
    updated_at          timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT uq_deals_tenant UNIQUE (id, tenant_id),
    -- Quan hệ 1–1 tuỳ chọn: một Lead chuyển đổi thành đúng một Deal (UC033).
    CONSTRAINT uq_deals_lead UNIQUE (lead_id),
    CONSTRAINT fk_deals_lead FOREIGN KEY (lead_id, tenant_id)
        REFERENCES sales.leads (id, tenant_id),
    CONSTRAINT fk_deals_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id),
    CONSTRAINT fk_deals_pipeline FOREIGN KEY (pipeline_id, tenant_id)
        REFERENCES sales.pipelines (id, tenant_id),
    -- Khoá ngoại này ép giai đoạn phải THUỘC chính phễu của cơ hội. Hai khoá ngoại
    -- rời (pipeline_id -> pipelines, stage_id -> deal_stages) không chặn được việc
    -- kéo cơ hội sang một giai đoạn của phễu khác.
    CONSTRAINT fk_deals_stage FOREIGN KEY (pipeline_id, stage_id)
        REFERENCES sales.deal_stages (pipeline_id, id),
    CONSTRAINT fk_deals_owner FOREIGN KEY (owner_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    CONSTRAINT ck_deals_closed CHECK ((status = 'OPEN') = (closed_at IS NULL))
);

CREATE INDEX ix_deals_kanban
    ON sales.deals (tenant_id, pipeline_id, stage_id, expected_close_date NULLS LAST);
CREATE INDEX ix_deals_contact ON sales.deals (tenant_id, contact_id);
CREATE INDEX ix_deals_owner   ON sales.deals (tenant_id, owner_user_id, status);

-- ─────────────────────────────────────────────────────────────────────────────
-- activities
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE sales.activities (
    id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid         NOT NULL REFERENCES platform.tenants (id),
    contact_id      uuid         NOT NULL,
    lead_id         uuid,
    deal_id         uuid,
    type            varchar(30)  NOT NULL
                    CHECK (type IN ('CALL','MEETING','QUOTE','EMAIL','NOTE')),
    subject         varchar(200),
    content         text,
    outcome         varchar(30)
                    CHECK (outcome IN ('DONE','NO_ANSWER','REFUSED',
                                       'NOT_INTERESTED','RESCHEDULED')),
    source          varchar(20)  NOT NULL DEFAULT 'MANUAL'
                    CHECK (source IN ('MANUAL','AUTO')),
    performed_by    uuid         NOT NULL,
    performed_at    timestamptz,
    remind_at       timestamptz,
    remind_user_id  uuid,
    remind_status   varchar(20)  NOT NULL DEFAULT 'NONE'
                    CHECK (remind_status IN ('NONE','PENDING','SENT','DONE','CANCELED')),
    created_at      timestamptz  NOT NULL DEFAULT now(),
    updated_at      timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT fk_act_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_act_lead FOREIGN KEY (lead_id, tenant_id)
        REFERENCES sales.leads (id, tenant_id) ON DELETE SET NULL,
    CONSTRAINT fk_act_deal FOREIGN KEY (deal_id, tenant_id)
        REFERENCES sales.deals (id, tenant_id) ON DELETE SET NULL,
    CONSTRAINT fk_act_performer FOREIGN KEY (performed_by, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    CONSTRAINT fk_act_reminder FOREIGN KEY (remind_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    -- Có hẹn nhắc thì phải có mốc thời gian, và ngược lại.
    CONSTRAINT ck_act_remind CHECK ((remind_status = 'NONE') = (remind_at IS NULL))
);

CREATE INDEX ix_act_todo
    ON sales.activities (tenant_id, remind_user_id, remind_at)
    WHERE remind_status = 'PENDING';
CREATE INDEX ix_act_contact ON sales.activities (tenant_id, contact_id, created_at DESC);
CREATE INDEX ix_act_deal    ON sales.activities (tenant_id, deal_id, created_at DESC);

COMMENT ON COLUMN sales.activities.source IS
    'AUTO là hoạt động hệ thống sinh khi chuyển giao hội thoại. Tách khỏi MANUAL vì gộp chung '
    'sẽ làm sai chỉ số năng suất nhân viên.';
COMMENT ON TABLE sales.activities IS
    'Ba khoá ngoại nullable thay cho mẫu đa hình (entity_type, entity_id): mẫu đa hình không có '
    'khoá ngoại thật, nên CSDL không chặn được hoạt động trỏ vào cơ hội đã xoá.';
