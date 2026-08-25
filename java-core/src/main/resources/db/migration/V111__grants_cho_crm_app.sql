-- V111 — Quyền của tài khoản runtime.
--
-- ADR-0001: ứng dụng KHÔNG BAO GIỜ chạy bằng crm_owner. Chủ bảng bypass RLS, nên
-- dùng nó lúc chạy là vô hiệu hoá toàn bộ cô lập tenant — và test vẫn xanh.

-- Mặc định: đọc ghi đầy đủ trên ba schema nghiệp vụ.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA platform, engagement, sales, analytics TO crm_app;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA platform, analytics TO crm_app;

-- ─────────────────────────────────────────────────────────────────────────────
-- Ba chỗ thu hẹp lại. Đây là phần dễ bỏ sót nhất của cả file.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Danh mục gói do quản trị nền tảng định nghĩa. Tenant chỉ được đọc.
REVOKE INSERT, UPDATE, DELETE ON platform.subscription_plans FROM crm_app;

-- 2. Nhật ký kiểm toán CHỈ GHI THÊM. Một nhật ký mà ứng dụng sửa hay xoá được
--    thì không phải nhật ký kiểm toán — RLS không giúp gì ở đây, chỉ quyền mới chặn.
REVOKE UPDATE, DELETE ON platform.audit_logs FROM crm_app;

-- 3. Vai trò hệ thống (tenant_id NULL) không được sửa. Không thu hồi UPDATE toàn
--    bảng vì hướng mở rộng cho phép tenant tạo vai trò riêng; chặn bằng RLS ở V112.

COMMENT ON SCHEMA platform IS
    'Doanh nghiệp thuê bao, người dùng, gói dịch vụ, kiểm toán. '
    'Runtime dùng crm_app; crm_owner chỉ dành cho Flyway.';
