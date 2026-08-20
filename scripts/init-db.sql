-- Chạy MỘT LẦN khi container postgres khởi tạo lần đầu.
-- Chỉ tạo extension và tài khoản. Schema và bảng do Flyway quản:
--   dải V1xx -> java-core/src/main/resources/db/migration/
--   dải V2xx -> ai-service/migration/

-- pgvector: lưu embedding ngay trong cụm nghiệp vụ (ADR-0007)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- hỗ trợ tìm gần đúng
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS unaccent;     -- bỏ dấu, dùng cho BM25 tiếng Việt

-- ─────────────────────────────────────────────────────────────────
-- ADR-0001: KHÔNG dùng tài khoản chủ bảng ở runtime.
-- Chủ bảng bypass RLS, nên dùng nó lúc chạy là vô hiệu hóa toàn bộ cô lập tenant.
--
--   crm_owner  (POSTGRES_USER) -> Flyway, có DDL, là chủ bảng
--   crm_app                    -> java-core lúc chạy, CHỊU RLS
--   ai_app                     -> ai-service lúc chạy, CHỊU RLS
-- ─────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'crm_app') THEN
        CREATE ROLE crm_app LOGIN PASSWORD 'changeme';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_app') THEN
        CREATE ROLE ai_app LOGIN PASSWORD 'changeme';
    END IF;
END
$$;

-- Hai tài khoản ứng dụng chỉ được kết nối; quyền trên bảng do migration cấp
-- (Flyway GRANT theo từng schema, sau khi tạo bảng).
GRANT CONNECT ON DATABASE thesis_crm TO crm_app, ai_app;

-- TODO (migration V112 / V210): với mọi bảng có tenant_id
--   ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
--   ALTER TABLE <t> FORCE  ROW LEVEL SECURITY;   -- thiếu dòng này thì chủ bảng vẫn đọc hết
--   CREATE POLICY tenant_isolation ON <t>
--       USING (tenant_id = current_setting('app.tenant_id')::uuid);
