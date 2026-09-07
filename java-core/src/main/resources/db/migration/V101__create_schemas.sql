-- V101 — Bốn schema của Track A và hàm tiện ích dùng chung.
--
-- Dải V1xx thuộc Track A. Không bao giờ đụng knowledge / ai / integration (dải V2xx).
-- Chạy bằng crm_owner (DB_MIGRATION_USER). Ứng dụng chạy bằng crm_app — xem V109.

CREATE SCHEMA IF NOT EXISTS platform;
CREATE SCHEMA IF NOT EXISTS engagement;
CREATE SCHEMA IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS analytics;

COMMENT ON SCHEMA platform   IS 'Doanh nghiệp thuê bao, người dùng, gói dịch vụ, kiểm toán';
COMMENT ON SCHEMA engagement IS 'Kênh, danh tính, danh bạ, hội thoại, tin nhắn';
COMMENT ON SCHEMA sales      IS 'Phễu bán hàng, Lead, Deal, hoạt động chăm sóc';
COMMENT ON SCHEMA analytics  IS 'Số liệu tổng hợp và chống xử lý trùng sự kiện';

-- crm_app chỉ được đi vào schema; quyền trên từng bảng cấp ở V109.
GRANT USAGE ON SCHEMA platform, engagement, sales, analytics TO crm_app;

-- ─────────────────────────────────────────────────────────────────────────────
-- Hàm chạm updated_at. Gắn cho mọi bảng có cột này ở cuối V110.
--
-- Đặt ở tầng CSDL chứ không phó mặc tầng ứng dụng: có nhiều đường ghi vào cùng
-- một bảng (JPA, job nền, script vá dữ liệu), quên một đường là số liệu "sửa lần
-- cuối" sai mà không có gì báo.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION platform.touch_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$ LANGUAGE plpgsql;

-- ─────────────────────────────────────────────────────────────────────────────
-- Tenant của phiên hiện tại. Mọi policy RLS gọi hàm này thay vì đọc thẳng
-- current_setting('app.tenant_id').
--
-- Vì sao cần hàm riêng: viết thẳng
--     tenant_id = current_setting('app.tenant_id', true)::uuid
-- thì khi ứng dụng QUÊN đặt biến phiên, câu truy vấn nổ
--     ERROR: invalid input syntax for type uuid: ""
-- Vẫn an toàn (không rò dữ liệu), nhưng thông báo không chỉ ra nguyên nhân, và
-- người debug sẽ đi tìm chỗ nào truyền uuid rỗng thay vì tìm chỗ thiếu SET LOCAL.
--
-- Cũng KHÔNG trả NULL để lặng lẽ ra rỗng: thiếu ngữ cảnh tenant là lỗi lập trình,
-- và danh sách rỗng trông y hệt "chưa có dữ liệu" — loại lỗi tệ nhất vì không ai
-- nhận ra. Báo lỗi rõ ràng, mã 42501 để Spring dịch thành lỗi phân quyền.
--
-- STABLE nên Postgres tính một lần cho cả câu, không phải mỗi dòng.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION platform.current_tenant() RETURNS uuid
LANGUAGE plpgsql STABLE AS $$
DECLARE v text := current_setting('app.tenant_id', true);
BEGIN
    IF v IS NULL OR v = '' THEN
        RAISE EXCEPTION
            'Chưa đặt app.tenant_id. Mọi truy vấn nghiệp vụ phải chạy trong ngữ cảnh tenant '
            '(java-core: filter ở security/; ai-service: app/db/session.py).'
            USING ERRCODE = '42501';
    END IF;
    RETURN v::uuid;
END $$;

GRANT EXECUTE ON FUNCTION platform.current_tenant() TO crm_app;
