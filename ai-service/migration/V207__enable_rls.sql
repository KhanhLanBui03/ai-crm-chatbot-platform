-- V207 — Row-Level Security cho sáu bảng của Track B. ADR-0001, bề mặt T6.
--
-- ai-service lấy tenant_id từ header X-Tenant-Id do gateway gắn, rồi
-- app/db/session.py đặt SET LOCAL app.tenant_id cho mỗi phiên SQLAlchemy.
-- Repository KHÔNG tự thêm WHERE tenant_id = ? — để RLS lo. Tự lọc ở tầng ứng
-- dụng tạo cảm giác an toàn giả và che mất lỗi cấu hình RLS.

DO $$
DECLARE
    full_name text;
    tbl       text[] := ARRAY[
        'knowledge.knowledge_documents',
        'knowledge.knowledge_chunks',
        'integration.mcp_servers',
        'ai.ai_interactions',
        'ai.ai_tool_calls',
        'ai.ai_feedback'
    ];
BEGIN
    FOREACH full_name IN ARRAY tbl LOOP
        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', full_name);
        EXECUTE format('ALTER TABLE %s FORCE  ROW LEVEL SECURITY', full_name);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %s
                USING      (tenant_id = ai.current_tenant())
                WITH CHECK (tenant_id = ai.current_tenant())
        $f$, full_name);
    END LOOP;
END $$;

-- Trigger chạm updated_at.
DO $$
DECLARE r record;
BEGIN
    FOR r IN
        SELECT c.table_schema, c.table_name
          FROM information_schema.columns c
          JOIN information_schema.tables t
            ON t.table_schema = c.table_schema AND t.table_name = c.table_name
         WHERE c.column_name = 'updated_at'
           AND t.table_type = 'BASE TABLE'
           AND c.table_schema IN ('knowledge','ai','integration')
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_touch_updated_at BEFORE UPDATE ON %I.%I
               FOR EACH ROW EXECUTE FUNCTION ai.touch_updated_at()',
            r.table_schema, r.table_name);
    END LOOP;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cái bẫy của truy vấn vector: RLS chặn được dòng nhưng KHÔNG đổi được thứ tự quét.
--
--     SELECT ... FROM knowledge_chunks ORDER BY embedding <=> $1 LIMIT 8
--
-- Câu trên đúng về mặt bảo mật nhờ RLS, nhưng chỉ mục HNSW xếp hạng trên TOÀN BỘ
-- bảng rồi RLS mới lọc bỏ — nên với kho nhiều tenant, tám kết quả đầu có thể bị
-- lọc sạch và câu trả về rỗng dù tenant hiện tại có đoạn phù hợp.
-- Vì vậy tầng ứng dụng VẪN phải ghi tenant_id vào mệnh đề WHERE (ADR-0007):
--
--     WHERE tenant_id = $2 ORDER BY embedding <=> $1 LIMIT 8
--
-- Đây là chỗ DUY NHẤT trong dự án mà lọc tenant ở tầng ứng dụng là bắt buộc, và
-- lý do là hiệu năng chứ không phải bảo mật.
-- ─────────────────────────────────────────────────────────────────────────────
