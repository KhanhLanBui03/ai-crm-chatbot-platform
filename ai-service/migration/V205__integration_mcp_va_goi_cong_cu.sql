-- V205 — Máy chủ MCP và nhật ký gọi công cụ.
-- UC021 · UC024 · UC028

CREATE TABLE integration.mcp_servers (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            uuid         NOT NULL,
    name                 varchar(150) NOT NULL,
    endpoint_url         text         NOT NULL,
    transport            varchar(20)  NOT NULL DEFAULT 'HTTP'
                         CHECK (transport IN ('HTTP','SSE','STDIO')),
    spec_version         varchar(20)  NOT NULL,
    auth_type            varchar(20)  NOT NULL DEFAULT 'NONE'
                         CHECK (auth_type IN ('NONE','API_KEY','OAUTH2')),
    credential_encrypted bytea,
    credential_key_id    varchar(64),
    allowed_tools        text[]       NOT NULL DEFAULT '{}',
    tool_schema_cache    jsonb,
    rate_limit_per_min   int          NOT NULL DEFAULT 60 CHECK (rate_limit_per_min > 0),
    timeout_ms           int          NOT NULL DEFAULT 5000 CHECK (timeout_ms > 0),
    status               varchar(30)  NOT NULL DEFAULT 'DRAFT'
                         CHECK (status IN ('DRAFT','ACTIVE','ERROR','DISABLED')),
    last_health_check_at timestamptz,
    last_error           text,
    created_by           uuid,        -- trỏ platform.users, không FK
    created_at           timestamptz  NOT NULL DEFAULT now(),
    updated_at           timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_mcp_name UNIQUE (tenant_id, name),
    CONSTRAINT ck_mcp_key_id CHECK (
        credential_encrypted IS NULL OR credential_key_id IS NOT NULL
    ),
    CONSTRAINT ck_mcp_auth CHECK (
        auth_type = 'NONE' OR credential_encrypted IS NOT NULL
    )
);

CREATE INDEX ix_mcp_tenant ON integration.mcp_servers (tenant_id, status);

COMMENT ON COLUMN integration.mcp_servers.spec_version IS
    'GHIM phiên bản đặc tả MCP. Máy chủ bên kia nâng cấp không được phép làm hỏng tác tử đang chạy.';
COMMENT ON COLUMN integration.mcp_servers.allowed_tools IS
    'DANH SÁCH TRẮNG. Công cụ ngoài danh sách bị chặn ở UC028 và ghi vào ai_tool_calls với '
    'decision = BLOCKED. Danh sách công cụ do máy chủ MCP công bố, không phải dữ liệu người dùng '
    'quản lý, nên không tách bảng tool_registry.';

-- ─────────────────────────────────────────────────────────────────────────────
-- ai_tool_calls — ghi CẢ lời gọi bị chặn, không chỉ lời gọi thành công.
--
-- Một dòng BLOCKED + CROSS_TENANT_IDENTIFIER là bằng chứng vận hành cụ thể rằng
-- lớp phòng thủ đã làm việc, thay cho một lời khẳng định suông trong báo cáo.
-- Bảng CHỈ GHI THÊM — V206 chỉ cấp SELECT, INSERT.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE ai.ai_tool_calls (
    id                bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id         uuid         NOT NULL,
    ai_interaction_id uuid         NOT NULL REFERENCES ai.ai_interactions (id) ON DELETE CASCADE,
    mcp_server_id     uuid         REFERENCES integration.mcp_servers (id),
    tool_name         varchar(100) NOT NULL,
    risk_level        varchar(20)  NOT NULL DEFAULT 'READ'
                      CHECK (risk_level IN ('READ','WRITE','DESTRUCTIVE')),
    arguments         jsonb        NOT NULL,
    result_summary    jsonb,
    decision          varchar(20)  NOT NULL
                      CHECK (decision IN ('ALLOWED','BLOCKED','NEEDS_APPROVAL')),
    block_reason      varchar(50)
                      CHECK (block_reason IN ('NOT_ALLOWLISTED','TOOL_DISABLED',
                                              'SCHEMA_HASH_MISMATCH','INVALID_ARGUMENTS',
                                              'CROSS_TENANT_IDENTIFIER','RATE_LIMIT_EXCEEDED')),
    approval_status   varchar(20)
                      CHECK (approval_status IN ('PENDING','APPROVED','REJECTED','EXPIRED')),
    approved_by       uuid,        -- trỏ platform.users, không FK
    approved_at       timestamptz,
    outcome           varchar(20)
                      CHECK (outcome IN ('SUCCESS','BUSINESS_ERROR','TIMEOUT','TRANSPORT_ERROR')),
    latency_ms        int          CHECK (latency_ms >= 0),
    error_message     text,
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT ck_tool_blocked   CHECK ((decision = 'BLOCKED') = (block_reason IS NOT NULL)),
    CONSTRAINT ck_tool_approval  CHECK ((decision = 'NEEDS_APPROVAL') = (approval_status IS NOT NULL)),
    -- Chỉ lời gọi được phép mới có kết quả thực thi.
    CONSTRAINT ck_tool_outcome   CHECK (decision = 'ALLOWED' OR outcome IS NULL)
);

CREATE INDEX ix_tool_calls_tenant
    ON ai.ai_tool_calls (tenant_id, decision, created_at DESC);
CREATE INDEX ix_tool_calls_interaction
    ON ai.ai_tool_calls (ai_interaction_id);
CREATE INDEX ix_tool_calls_pending
    ON ai.ai_tool_calls (tenant_id, created_at DESC)
    WHERE approval_status = 'PENDING';

COMMENT ON COLUMN ai.ai_tool_calls.arguments IS
    'Đối số mô hình đề xuất. Lưu CẢ KHI BỊ CHẶN — đây mới là dữ liệu cho thấy mô hình đã cố làm gì.';
COMMENT ON COLUMN ai.ai_tool_calls.updated_at IS
    'Chỉ đổi khi lời gọi NEEDS_APPROVAL được duyệt. Ngoài trường hợp đó thì bằng created_at.';
