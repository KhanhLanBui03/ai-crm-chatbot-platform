-- V104 — Nhật ký kiểm toán.
-- UC003 · UC007 · UC016 · UC021 · UC040 · UC041
--
-- Bảng CHỈ GHI THÊM. V111 chỉ cấp SELECT, INSERT cho crm_app — không UPDATE,
-- không DELETE. Một nhật ký kiểm toán mà ứng dụng sửa được thì không phải nhật
-- ký kiểm toán.

CREATE TABLE platform.audit_logs (
    id            bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id     uuid        NOT NULL REFERENCES platform.tenants (id),
    actor_type    varchar(20) NOT NULL
                  CHECK (actor_type IN ('USER','AI_AGENT','SYSTEM','PLATFORM_ADMIN')),
    actor_user_id uuid        REFERENCES platform.users (id),
    action        varchar(60) NOT NULL,
    entity_type   varchar(50) NOT NULL,
    entity_id     uuid,
    before_data   jsonb,
    after_data    jsonb,
    ip_address    inet,
    user_agent    text,
    request_id    varchar(64),
    severity      varchar(20) NOT NULL DEFAULT 'INFO'
                  CHECK (severity IN ('INFO','WARNING','CRITICAL')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),

    -- Tác nhân là người thì phải biết là ai; là AI hoặc tiến trình nền thì không.
    CONSTRAINT ck_audit_actor CHECK (
        (actor_type IN ('USER','PLATFORM_ADMIN') AND actor_user_id IS NOT NULL) OR
        (actor_type IN ('AI_AGENT','SYSTEM'))
    )
);

CREATE INDEX ix_audit_tenant_time   ON platform.audit_logs (tenant_id, created_at DESC);
CREATE INDEX ix_audit_tenant_entity ON platform.audit_logs (tenant_id, entity_type, entity_id);
CREATE INDEX ix_audit_tenant_action ON platform.audit_logs (tenant_id, action, created_at DESC);

COMMENT ON TABLE platform.audit_logs IS
    'Chỉ ghi thêm. Hành động của quản trị nền tảng cũng luôn nhắm vào một tenant cụ thể, '
    'nên tenant_id NOT NULL không phải ngoại lệ.';
COMMENT ON COLUMN platform.audit_logs.before_data IS
    'Giá trị trước khi đổi. Dữ liệu cá nhân phải che trước khi ghi vào đây.';
COMMENT ON COLUMN platform.audit_logs.updated_at IS
    'Bằng created_at, không bao giờ đổi. Giữ cột cho đồng nhất với các bảng khác.';
