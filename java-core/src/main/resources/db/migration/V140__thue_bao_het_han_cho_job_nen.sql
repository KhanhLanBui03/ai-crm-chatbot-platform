-- V140 — UC006: job nền mở chu kỳ thuê bao mới cần tìm được doanh nghiệp có chu kỳ đã hết hạn.
--
-- Job chạy nền KHÔNG có ngữ cảnh tenant nên RLS chặn mọi dòng của platform.tenant_subscriptions
-- (ENABLE + FORCE từ V112). Cùng khuôn với engagement.tenants_with_overdue_handoffs (V131): hàm
-- SECURITY DEFINER chỉ trả về MÃ doanh nghiệp, không trả một cột dữ liệu nào — job lấy danh sách rồi
-- mở một transaction có app.tenant_id cho từng doanh nghiệp, RLS vẫn áp như mọi truy vấn khác.
--
-- Vì sao cần: trước V140 không có gì mở chu kỳ mới. Chu kỳ hết hạn thì đứng im — hạn mức hội thoại và
-- token không bao giờ về 0, lịch hạ gói (scheduled_plan_id) không bao giờ được áp, và doanh nghiệp
-- nhận 409 "Hãy gia hạn hoặc chọn gói" mà cả hai đường đều không cứu được (Dev A gặp 10/11/2026, phải
-- dời period_end bằng SQL tay trên CSDL dev).
--
-- CANCELED và EXPIRED không nằm trong danh sách: đã dừng hẳn, không tự lăn sang chu kỳ mới.

CREATE FUNCTION platform.tenants_with_expired_subscription(p_now timestamptz)
RETURNS SETOF uuid
LANGUAGE sql SECURITY DEFINER SET search_path = platform, pg_temp STABLE
AS $$
    SELECT DISTINCT s.tenant_id
      FROM platform.tenant_subscriptions s
     WHERE s.period_end <= p_now
       AND s.status IN ('TRIALING', 'ACTIVE', 'PAST_DUE')
$$;

REVOKE ALL ON FUNCTION platform.tenants_with_expired_subscription(timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION platform.tenants_with_expired_subscription(timestamptz) TO crm_app;

COMMENT ON FUNCTION platform.tenants_with_expired_subscription(timestamptz) IS
    'SECURITY DEFINER — UC006: doanh nghiệp có chu kỳ thuê bao đã hết hạn mà chưa đóng. Chỉ trả mã.';
