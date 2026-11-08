-- V215 — UC038 Thống kê chủ đề hội thoại, phần phân cụm: lưu kết quả mỗi kỳ chạy.
--
-- Không sửa V201–V214: đã chạy trên CSDL dev, sửa là lệch checksum Flyway.
--
-- Vì sao ai-service lưu kết quả ở schema của mình chứ không ghi sang engagement/analytics:
--   AI không ghi bảng nghiệp vụ CRM (ADR-0002). java-core lấy kết quả qua
--   GET /v1/topic-clusters/latest (mạng nội bộ, gateway chặn từ ngoài — cùng khuôn UC040) rồi tự ghép
--   với số liệu từ chối nó đã có ở analytics.topic_conversations (V138 bên java-core).
--
-- Ba bảng:
--   topic_cluster_runs         — một dòng mỗi kỳ chạy của mỗi doanh nghiệp, KỂ CẢ kỳ bị bỏ qua
--                                (TOO_FEW_CONVERSATIONS, EMBED_UNAVAILABLE) — để biết vì sao màn trống
--   topic_clusters             — các cụm của một kỳ, kèm nhãn do mô hình (hoặc luật từ khoá) đặt
--   topic_cluster_assignments  — hội thoại nào thuộc cụm nào
--
-- KHÔNG lưu câu hỏi của khách: tên cụm và gán cụm là đủ cho báo cáo. Câu hỏi (đã che PII) vẫn nằm
-- ở ai.ai_interactions, xoá theo UC041 như cũ.
--
-- Mã cụm (cluster_id) chỉ ổn định TRONG một kỳ: dữ liệu đổi thì phân cụm đổi (đánh đổi đặc tả đã ghi).

CREATE TABLE ai.topic_cluster_runs (
    id                  uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid          NOT NULL,
    started_at          timestamptz   NOT NULL DEFAULT now(),
    finished_at         timestamptz,
    window_from         timestamptz   NOT NULL,
    window_to           timestamptz   NOT NULL,
    conversation_count  int           NOT NULL DEFAULT 0 CHECK (conversation_count >= 0),
    min_conversations   int           NOT NULL CHECK (min_conversations > 0),
    status              varchar(10)   NOT NULL CHECK (status IN ('DONE', 'SKIPPED', 'FAILED')),
    skip_reason         varchar(40)   CHECK (skip_reason IN ('TOO_FEW_CONVERSATIONS', 'EMBED_UNAVAILABLE',
                                                             'CLUSTER_SERVICE_ERROR')),
    -- 'bge-m3' (đúng đặc tả) hoặc 'router-tfidf-ngram' (nguồn thay thế theo chữ) — báo cáo phải ghi rõ
    vector_source       varchar(40),
    k                   int           CHECK (k > 0),
    silhouette          numeric(5,4),
    -- 'llm' hoặc 'tu-khoa' (luật từ khoá khi không có LLM)
    naming_method       varchar(10),
    created_at          timestamptz   NOT NULL DEFAULT now(),
    updated_at          timestamptz   NOT NULL DEFAULT now(),
    CONSTRAINT ck_run_done CHECK (status <> 'DONE' OR (k IS NOT NULL AND vector_source IS NOT NULL)),
    CONSTRAINT ck_run_skip CHECK (status = 'DONE' OR skip_reason IS NOT NULL)
);

-- "Kỳ gần nhất đã xong" — truy vấn duy nhất của java-core
CREATE INDEX ix_cluster_run_moi_nhat ON ai.topic_cluster_runs (tenant_id, status, started_at DESC);

CREATE TABLE ai.topic_clusters (
    run_id              uuid          NOT NULL REFERENCES ai.topic_cluster_runs (id) ON DELETE CASCADE,
    cluster_id          uuid          NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           uuid          NOT NULL,
    -- Nhãn do máy sinh trên nội dung khách: chỉ HIỂN THỊ như văn bản thuần, không làm khoá tra cứu
    label               varchar(200)  NOT NULL,
    size                int           NOT NULL CHECK (size > 0),
    created_at          timestamptz   NOT NULL DEFAULT now(),
    updated_at          timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (cluster_id)
);
CREATE INDEX ix_cluster_run ON ai.topic_clusters (tenant_id, run_id);

CREATE TABLE ai.topic_cluster_assignments (
    run_id              uuid          NOT NULL REFERENCES ai.topic_cluster_runs (id) ON DELETE CASCADE,
    cluster_id          uuid          NOT NULL REFERENCES ai.topic_clusters (cluster_id) ON DELETE CASCADE,
    tenant_id           uuid          NOT NULL,
    -- Tham chiếu LOGIC sang engagement.conversations — không khoá ngoại liên làn (ADR-0002)
    conversation_id     uuid          NOT NULL,
    created_at          timestamptz   NOT NULL DEFAULT now(),
    updated_at          timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, conversation_id)
);
CREATE INDEX ix_cluster_gan_run ON ai.topic_cluster_assignments (tenant_id, run_id);
-- UC041 xoá dữ liệu cá nhân xoá theo conversation_id
CREATE INDEX ix_cluster_gan_hoi_thoai ON ai.topic_cluster_assignments (tenant_id, conversation_id);

COMMENT ON TABLE ai.topic_cluster_runs IS
    'UC038 — mỗi kỳ phân cụm chủ đề (hằng tuần, tách theo doanh nghiệp). Ghi cả kỳ bị bỏ qua kèm lý do.';

-- Quyền + RLS — khuôn V206/V207 (bảng tạo sau không được GRANT ALL TABLES của V206 phủ)
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ai.topic_cluster_runs, ai.topic_clusters, ai.topic_cluster_assignments TO ai_app;

DO $$
DECLARE
    full_name text;
    tbl       text[] := ARRAY['ai.topic_cluster_runs', 'ai.topic_clusters', 'ai.topic_cluster_assignments'];
BEGIN
    FOREACH full_name IN ARRAY tbl LOOP
        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', full_name);
        EXECUTE format('ALTER TABLE %s FORCE  ROW LEVEL SECURITY', full_name);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %s
                USING      (tenant_id = ai.current_tenant())
                WITH CHECK (tenant_id = ai.current_tenant())
        $f$, full_name);
        EXECUTE format(
            'CREATE TRIGGER trg_touch_updated_at BEFORE UPDATE ON %s
               FOR EACH ROW EXECUTE FUNCTION ai.touch_updated_at()', full_name);
    END LOOP;
END $$;

-- Công việc hằng tuần cần biết doanh nghiệp NÀO có hội thoại trong cửa sổ — câu hỏi xuyên tenant mà
-- ai_app (chịu RLS FORCE) không hỏi được. SECURITY DEFINER như ai.tim_luot_can_cham (V212): chỉ trả
-- mã doanh nghiệp + số hội thoại, không trả nội dung. Phần đọc câu hỏi chạy trong phiên đã gắn tenant.
CREATE FUNCTION ai.tenant_co_hoi_thoai(p_tu timestamptz)
    RETURNS TABLE (tenant_id uuid, so_hoi_thoai bigint)
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT i.tenant_id, count(DISTINCT i.conversation_id)
      FROM ai.ai_interactions i
     WHERE i.created_at >= p_tu
       AND i.branch <> 'SUMMARY'
     GROUP BY i.tenant_id
$$;

REVOKE ALL ON FUNCTION ai.tenant_co_hoi_thoai(timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ai.tenant_co_hoi_thoai(timestamptz) TO ai_app;

COMMENT ON FUNCTION ai.tenant_co_hoi_thoai(timestamptz) IS
    'SECURITY DEFINER — UC038: doanh nghiệp có hội thoại từ mốc cho trước, kèm số hội thoại. Chỉ trả mã và số đếm.';
