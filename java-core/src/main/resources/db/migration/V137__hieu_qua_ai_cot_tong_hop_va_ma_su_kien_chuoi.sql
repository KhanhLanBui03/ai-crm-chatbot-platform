-- UC039 — Báo cáo hiệu quả và chi phí AI: bộ tiêu thụ analytics-cg cộng dồn ai.turn.completed vào
-- analytics.metrics_daily (V113). V113 thiếu vài bộ đếm mà trang "Hiệu quả tác tử AI" cần.

ALTER TABLE analytics.metrics_daily
    -- KPI §1.6: ≥ 55% lượt KHÔNG gọi LLM = 1 − llm_call_count / interaction_count
    ADD COLUMN llm_call_count       int           NOT NULL DEFAULT 0 CHECK (llm_call_count >= 0),
    -- Lượt dùng đệm có chi phí 0 — phải TÁCH khi tính trung bình, gộp vào là báo cáo đẹp hơn thực tế
    ADD COLUMN cached_count         int           NOT NULL DEFAULT 0 CHECK (cached_count >= 0),
    ADD COLUMN degraded_count       int           NOT NULL DEFAULT 0 CHECK (degraded_count >= 0),
    ADD COLUMN failed_count         int           NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
    -- Trung bình độ bám nguồn = tổng ÷ số lượt CÓ chấm (lượt mẫu câu không có điểm)
    ADD COLUMN groundedness_sum     numeric(14,3) NOT NULL DEFAULT 0 CHECK (groundedness_sum >= 0),
    ADD COLUMN groundedness_count   int           NOT NULL DEFAULT 0 CHECK (groundedness_count >= 0),
    -- {"retrieve_ms": {"sum": 1234, "n": 5}, …} — trung bình từng chặng chia theo số lượt CHẠY chặng đó,
    -- không chia cho mọi lượt (lượt mẫu câu không truy hồi thì không kéo trung bình truy hồi xuống).
    ADD COLUMN stage_latency        jsonb         NOT NULL DEFAULT '{}'::jsonb
                                    CHECK (jsonb_typeof(stage_latency) = 'object');

-- event_id của ai.turn.completed là interaction_id (UUID) — ai-service không có outbox để cấp số bigint
-- như các sự kiện crm.*. Đổi sang chuỗi: số cũ chuyển thành chuỗi số, khoá chính dựng lại theo cột mới.
ALTER TABLE analytics.processed_events
    ALTER COLUMN event_id TYPE varchar(64) USING event_id::text;

COMMENT ON COLUMN analytics.metrics_daily.stage_latency IS
    'Độ trễ từng chặng: {"<chặng>_ms": {"sum": tổng ms, "n": số lượt chạy chặng}} — nguồn ai.turn.completed (UC039).';
