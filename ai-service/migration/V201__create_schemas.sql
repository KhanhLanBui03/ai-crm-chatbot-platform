-- V201 — Ba schema của Track B.
--
-- Dải V2xx thuộc Track B. Không bao giờ đụng platform / engagement / sales /
-- analytics (dải V1xx).
--
-- KHÔNG có khoá ngoại nào từ đây sang schema của Track A. Đó không phải thiếu
-- sót mà là ADR-0002: ai-service không nối thẳng bảng nghiệp vụ. Nếu mô hình
-- ngôn ngữ bị tiêm chỉ thị, nó không có đường nào chạm tới dữ liệu khách hàng.
-- Cái giá — mất toàn vẹn tham chiếu qua ranh giới — được bù bằng kiểm tra ở
-- tầng API và tiến trình dọn tham chiếu mồ côi.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE SCHEMA IF NOT EXISTS ai;
CREATE SCHEMA IF NOT EXISTS integration;

COMMENT ON SCHEMA knowledge   IS 'Tài liệu tri thức và đoạn đã nhúng vector (RAG)';
COMMENT ON SCHEMA ai          IS 'Lượt xử lý của tác tử, nhật ký gọi công cụ, đánh giá chất lượng';
COMMENT ON SCHEMA integration IS 'Máy chủ MCP của từng doanh nghiệp';

GRANT USAGE ON SCHEMA knowledge, ai, integration TO ai_app;

CREATE OR REPLACE FUNCTION ai.touch_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$ LANGUAGE plpgsql;

-- ─────────────────────────────────────────────────────────────────────────────
-- Tenant của phiên hiện tại. Mọi policy RLS của Track B gọi hàm này.
--
-- Bản sao có chủ ý của platform.current_tenant(): Track B không phụ thuộc vào
-- bất cứ thứ gì trong schema của Track A, kể cả một hàm. Hai làn phải nạp được
-- độc lập — chạy riêng dải V2xx trên một CSDL trống vẫn phải thành công.
--
-- Viết thẳng current_setting(...)::uuid trong policy thì khi quên đặt biến phiên,
-- truy vấn nổ "invalid input syntax for type uuid" — an toàn nhưng không chỉ ra
-- nguyên nhân. Trả NULL để lặng lẽ ra rỗng còn tệ hơn: danh sách rỗng trông y hệt
-- "chưa có dữ liệu".
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION ai.current_tenant() RETURNS uuid
LANGUAGE plpgsql STABLE AS $$
DECLARE v text := current_setting('app.tenant_id', true);
BEGIN
    IF v IS NULL OR v = '' THEN
        RAISE EXCEPTION
            'Chưa đặt app.tenant_id. Phiên SQLAlchemy phải đặt biến này từ header '
            'X-Tenant-Id do gateway gắn (app/db/session.py).'
            USING ERRCODE = '42501';
    END IF;
    RETURN v::uuid;
END $$;

GRANT EXECUTE ON FUNCTION ai.current_tenant() TO ai_app;
