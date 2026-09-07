-- V103 — Người dùng, vai trò, phân quyền (RBAC).
-- UC001 · UC002 · UC003

-- ─────────────────────────────────────────────────────────────────────────────
-- users — người dùng của tenant VÀ tài khoản quản trị nền tảng (A04).
--
-- NGOẠI LỆ tenant_id NULL: chỉ đúng khi scope = 'PLATFORM'. Ràng bằng CHECK.
-- Policy RLS thường (V110) so tenant_id, nên dòng PLATFORM không lọt vào phạm vi
-- của bất kỳ tenant nào — đúng ý muốn.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE platform.users (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          uuid         REFERENCES platform.tenants (id),
    email              varchar(255) NOT NULL,
    password_hash      varchar(255) NOT NULL,
    full_name          varchar(200) NOT NULL,
    phone              varchar(20),
    avatar_url         text,
    scope              varchar(20)  NOT NULL DEFAULT 'TENANT'
                       CHECK (scope IN ('TENANT','PLATFORM')),
    status             varchar(30)  NOT NULL DEFAULT 'PENDING'
                       CHECK (status IN ('PENDING','ACTIVE','DISABLED')),
    email_verified_at  timestamptz,
    last_login_at      timestamptz,
    failed_login_count smallint     NOT NULL DEFAULT 0,
    locked_until       timestamptz,
    deleted_at         timestamptz,
    created_at         timestamptz  NOT NULL DEFAULT now(),
    updated_at         timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT ck_users_scope CHECK (
        (scope = 'TENANT'   AND tenant_id IS NOT NULL) OR
        (scope = 'PLATFORM' AND tenant_id IS NULL)
    ),
    CONSTRAINT uq_users_tenant UNIQUE (id, tenant_id)
);

-- Hai tenant được phép trùng email; trong một tenant thì không.
-- Chỉ mục biểu thức nên phải là CREATE UNIQUE INDEX, không khai được trong CREATE TABLE.
CREATE UNIQUE INDEX uq_users_tenant_email
    ON platform.users (tenant_id, lower(email))
    WHERE deleted_at IS NULL AND scope = 'TENANT';

CREATE UNIQUE INDEX uq_users_platform_email
    ON platform.users (lower(email))
    WHERE deleted_at IS NULL AND scope = 'PLATFORM';

CREATE INDEX ix_users_tenant_status ON platform.users (tenant_id, status);

COMMENT ON COLUMN platform.users.deleted_at IS
    'Xoá mềm. Hội thoại cũ vẫn phải hiển thị được tên người đã trả lời.';

-- FK còn treo từ V102 (users tạo sau tenant_subscriptions).
ALTER TABLE platform.tenant_subscriptions
    ADD CONSTRAINT fk_subscription_changed_by
    FOREIGN KEY (changed_by) REFERENCES platform.users (id);

-- ─────────────────────────────────────────────────────────────────────────────
-- roles — tenant_id NULL nghĩa là vai trò hệ thống, dùng chung cho mọi tenant.
--
-- Quyền lưu bằng jsonb thay vì hai bảng permissions + role_permissions: danh mục
-- quyền là hằng số ở tầng mã nguồn, không phải dữ liệu người dùng nhập.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE platform.roles (
    id          uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid         REFERENCES platform.tenants (id),
    code        varchar(30)  NOT NULL,
    name        varchar(100) NOT NULL,
    description text,
    permissions jsonb        NOT NULL DEFAULT '[]'::jsonb,
    is_system   boolean      NOT NULL DEFAULT false,
    created_at  timestamptz  NOT NULL DEFAULT now(),
    updated_at  timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT ck_roles_system CHECK (is_system = (tenant_id IS NULL))
);

-- UNIQUE (tenant_id, code) thường KHÔNG chặn được trùng ở vai trò hệ thống:
-- Postgres coi mọi NULL là khác nhau, nên hai dòng (NULL,'AGENT') cùng lọt.
-- Phải tách thành hai chỉ mục bộ phận.
CREATE UNIQUE INDEX uq_roles_system_code
    ON platform.roles (code) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX uq_roles_tenant_code
    ON platform.roles (tenant_id, code) WHERE tenant_id IS NOT NULL;

-- Hai vai trò của hợp đồng dashboard-api.yaml (MaVaiTro). Doanh nghiệp không tự
-- tạo vai trò mới ở phạm vi đồ án; cột tenant_id để ngỏ cho hướng mở rộng.
INSERT INTO platform.roles (tenant_id, code, name, description, is_system, permissions) VALUES
    (NULL, 'TENANT_ADMIN', 'Quản trị viên doanh nghiệp',
     'Toàn quyền trong phạm vi doanh nghiệp: người dùng, kênh, tri thức, MCP, báo cáo, kiểm toán.',
     true,
     '["user:*","tenant:*","subscription:read","channel:*","contact:*","conversation:*",
       "knowledge:*","mcp:*","lead:*","deal:*","activity:*","analytics:*","audit:*","erasure:*"]'::jsonb),
    (NULL, 'AGENT', 'Nhân viên chăm sóc khách hàng',
     'Trả lời hội thoại, quản lý Lead và Deal được phân công. Không cấu hình hệ thống.',
     true,
     '["conversation:read","conversation:write","contact:read","contact:write",
       "knowledge:read","lead:read","lead:write","deal:read","deal:write",
       "activity:*","analytics:own"]'::jsonb);

-- ─────────────────────────────────────────────────────────────────────────────
-- user_roles — bảng nối N–N.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE platform.user_roles (
    user_id    uuid        NOT NULL,
    role_id    uuid        NOT NULL REFERENCES platform.roles (id),
    tenant_id  uuid        NOT NULL REFERENCES platform.tenants (id),
    granted_by uuid        REFERENCES platform.users (id),
    granted_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id)
);

CREATE INDEX ix_user_roles_tenant ON platform.user_roles (tenant_id, role_id);

-- role_id dùng khoá ngoại ĐƠN, không phức hợp: vai trò hệ thống có tenant_id NULL
-- trong khi user_roles.tenant_id NOT NULL, nên cặp (role_id, tenant_id) không bao
-- giờ khớp. Cô lập ở đây do RLS trên chính user_roles lo.
COMMENT ON CONSTRAINT fk_user_roles_user ON platform.user_roles IS
    'Khoá ngoại phức hợp: chặn gán vai trò cho người dùng của tenant khác.';
