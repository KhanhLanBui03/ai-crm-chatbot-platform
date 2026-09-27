-- V120 — Tạo vai trò PLATFORM_ADMIN và tài khoản Quản trị viên Hệ thống (Platform Admin)
-- Phục vụ cho Cổng Quản trị Nền tảng (Platform Admin Portal).

-- 1. Đảm bảo vai trò PLATFORM_ADMIN tồn tại trong platform.roles
INSERT INTO platform.roles (tenant_id, code, name, description, is_system, permissions)
VALUES (
    NULL,
    'PLATFORM_ADMIN',
    'Quản trị viên hệ thống',
    'Toàn quyền quản trị nền tảng: quản lý doanh nghiệp, gói dịch vụ, tài nguyên AI, kiểm toán.',
    true,
    '["platform.tenants.read","platform.tenants.write","platform.plans.read","platform.plans.write","platform.ai-usage.read","platform.audit.read"]'::jsonb
) ON CONFLICT DO NOTHING;

-- 2. Chèn tài khoản Platform Admin admin@platform.vn (mật khẩu: Admin@123456)
-- Mật khẩu được mã hóa bằng BCrypt ($2a$10$wv1XPVzuOhI3qcqXsQ4fxOaFj6e/TtjeJyLX29pSd61t52aiAukOe)
INSERT INTO platform.users (
    id,
    tenant_id,
    email,
    password_hash,
    full_name,
    scope,
    status,
    email_verified_at,
    created_at,
    updated_at
) VALUES (
    'a0000000-0000-4000-8000-000000000099',
    NULL,
    'admin@platform.vn',
    '$2a$10$wv1XPVzuOhI3qcqXsQ4fxOaFj6e/TtjeJyLX29pSd61t52aiAukOe',
    'Quản trị viên Hệ thống',
    'PLATFORM',
    'ACTIVE',
    now(),
    now(),
    now()
) ON CONFLICT (lower(email)) WHERE deleted_at IS NULL AND scope = 'PLATFORM' DO UPDATE
  SET password_hash = EXCLUDED.password_hash,
      status = 'ACTIVE',
      email_verified_at = COALESCE(platform.users.email_verified_at, now()),
      updated_at = now();
