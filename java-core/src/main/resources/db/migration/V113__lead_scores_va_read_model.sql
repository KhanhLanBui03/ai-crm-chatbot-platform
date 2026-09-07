-- V113 — Lịch sử chấm điểm, mô hình đọc cho báo cáo, quy tắc phân công.
-- UC006 · UC030 · UC032 · UC036 · UC037 · UC038 · UC039 · (UC014, UC015, UC031)
--
-- Ba thứ ở đây đều là hậu điều kiện hoặc luồng chính của use case đã đặc tả, không
-- phải tiện ích thêm vào. Xem docs/traceability-uc-db-api-screen.md để biết dòng nào
-- của bản đặc tả đòi cái gì. Mục 3 giải thích thứ CỐ Ý không thêm.
--
-- LƯU Ý: V111 cấp quyền bằng GRANT ... ON ALL TABLES, chỉ áp cho bảng ĐANG tồn tại
-- lúc nó chạy. V112 gắn trigger updated_at cũng vậy. Hai bảng mới bên dưới phải tự
-- cấp quyền, tự bật RLS và tự gắn trigger — quên một trong ba thì không có lỗi nào
-- nổ lúc migrate, chỉ hỏng lúc chạy.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. sales.lead_scores — lịch sử điểm tiềm năng
--
-- UC030 hậu điều kiện: "Một bản ghi điểm mới được lưu kèm giá trị điểm, phiên bản
-- mô hình, vector đặc trưng và ba yếu tố đóng góp nhiều nhất. CÁC BẢN GHI ĐIỂM CŨ
-- ĐƯỢC GIỮ LẠI THÀNH LỊCH SỬ THAY VÌ BỊ GHI ĐÈ."
--
-- sales.leads.current_score + score_reason chỉ giữ được giá trị mới nhất, nên một
-- mình chúng không thoả hậu điều kiện đó, và UC032 bước 6 ("lịch sử thay đổi điểm
-- theo thời gian") không có nguồn.
--
-- Đây là NGOẠI LỆ LIÊN LÀN duy nhất của dự án: bảng nằm trong schema của Track A,
-- Track B ghi vào qua PUT /internal/leads/{id}/score chứ KHÔNG nối thẳng CSDL
-- (ADR-0002). Hợp đồng docs/openapi/java-core-to-ai-service.yaml đã khai đúng ba
-- trường score / model_version / features từ trước — bảng này là thứ nó vẫn thiếu.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE sales.lead_scores (
    id            uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid         NOT NULL REFERENCES platform.tenants (id),
    lead_id       uuid         NOT NULL,
    contact_id    uuid         NOT NULL,
    score         smallint     NOT NULL CHECK (score BETWEEN 0 AND 100),
    model_version varchar(50)  NOT NULL,
    features      jsonb        NOT NULL DEFAULT '{}'::jsonb,
    top_factors   jsonb        NOT NULL DEFAULT '[]'::jsonb,
    confidence    varchar(10)  NOT NULL DEFAULT 'HIGH'
                  CHECK (confidence IN ('LOW','MEDIUM','HIGH')),
    scored_at     timestamptz  NOT NULL DEFAULT now(),
    created_at    timestamptz  NOT NULL DEFAULT now(),
    updated_at    timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_lead_scores_tenant UNIQUE (id, tenant_id),
    CONSTRAINT fk_lead_scores_lead FOREIGN KEY (lead_id, tenant_id)
        REFERENCES sales.leads (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_lead_scores_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT ck_lead_scores_factors CHECK (jsonb_typeof(top_factors) = 'array')
);

-- Biểu đồ điểm theo thời gian ở SCR042 đọc đúng theo thứ tự này.
CREATE INDEX ix_lead_scores_timeline
    ON sales.lead_scores (tenant_id, lead_id, scored_at DESC);

COMMENT ON TABLE sales.lead_scores IS
    'Lịch sử chấm điểm, chỉ ghi thêm. leads.current_score là ảnh chụp dòng mới nhất, giữ lại để '
    'danh sách Lead không phải join — không phải nguồn thay thế cho bảng này.';
COMMENT ON COLUMN sales.lead_scores.model_version IS
    'UC030 6.2: bản ghi cũ giữ nguyên phiên bản của chúng. Đổi mô hình chỉ áp cho lần chấm mới, '
    'nếu không thì mọi so sánh giữa hai phiên bản đều vô nghĩa.';
COMMENT ON COLUMN sales.lead_scores.features IS
    'Vector đặc trưng đã chuẩn hoá. Không có nó thì điểm là con số không tái lập được — '
    'không giải thích được vì sao khách này 80 mà khách kia 40.';
COMMENT ON COLUMN sales.lead_scores.confidence IS
    'UC030 2.2: thiếu đặc trưng bắt buộc thì dùng giá trị mặc định và hạ mức tin cậy, '
    'chứ không bỏ qua lượt chấm.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. analytics.metrics_daily — mô hình đọc của báo cáo
--
-- UC036 hậu điều kiện nói tường minh: "Các chỉ số được đọc từ MÔ HÌNH ĐỌC ĐÃ TỔNG
-- HỢP SẴN, KHÔNG truy vấn trực tiếp vào bảng giao dịch." UC006 bước 2 cũng đọc
-- "từ mô hình đọc".
--
-- Nhưng lý do bắt buộc phải có bảng này không phải hiệu năng mà là RANH GIỚI QUYỀN:
-- token, chi phí, độ trễ và tỉ lệ theo nhánh nằm ở ai.ai_interactions (Track B),
-- trong khi /analytics/* và /usage do java-core phục vụ, và V111 không cấp cho
-- crm_app một chút quyền nào trên schema ai. Không có bảng đích thì UC039 hoàn toàn
-- không có đường lấy số.
--
-- Người ghi: consumer analytics-cg, từ crm.conversation.v1 và crm.ai-interaction.v1
-- (docs/events/README.md). Chống trùng bằng analytics.processed_events như mọi
-- consumer khác — ADR-0003.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE analytics.metrics_daily (
    id                 uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          uuid          NOT NULL REFERENCES platform.tenants (id),
    metric_date        date          NOT NULL,
    channel_id         uuid,
    -- Bảy giá trị này phải khớp TỪNG CHỮ với ai.ai_interactions.branch ở V204.
    -- Hai làn không có khoá ngoại nối nhau nên CSDL không bắt được chỗ lệch; lệch
    -- một chữ thì consumer chèn hỏng CHECK và sự kiện nằm lại ở dead letter.
    branch             varchar(30)
                       CHECK (branch IN ('SMALL_TALK','RAG','TOOL_CALL','CLARIFY',
                                         'HANDOFF','SUMMARY','EXTRACTION')),
    model_name         varchar(100),

    -- Đếm hội thoại — nguồn crm.conversation.v1
    conversation_count int           NOT NULL DEFAULT 0 CHECK (conversation_count >= 0),
    ai_handled_count   int           NOT NULL DEFAULT 0 CHECK (ai_handled_count >= 0),
    handover_count     int           NOT NULL DEFAULT 0 CHECK (handover_count >= 0),
    first_response_sum_ms bigint     NOT NULL DEFAULT 0 CHECK (first_response_sum_ms >= 0),
    first_response_count  int        NOT NULL DEFAULT 0 CHECK (first_response_count >= 0),

    -- Đếm lượt xử lý của tác tử — nguồn crm.ai-interaction.v1
    interaction_count  int           NOT NULL DEFAULT 0 CHECK (interaction_count >= 0),
    refusal_count      int           NOT NULL DEFAULT 0 CHECK (refusal_count >= 0),
    positive_feedback  int           NOT NULL DEFAULT 0 CHECK (positive_feedback >= 0),
    negative_feedback  int           NOT NULL DEFAULT 0 CHECK (negative_feedback >= 0),
    prompt_tokens      bigint        NOT NULL DEFAULT 0 CHECK (prompt_tokens >= 0),
    completion_tokens  bigint        NOT NULL DEFAULT 0 CHECK (completion_tokens >= 0),
    cost_vnd           numeric(16,4) NOT NULL DEFAULT 0 CHECK (cost_vnd >= 0),
    latency_sum_ms     bigint        NOT NULL DEFAULT 0 CHECK (latency_sum_ms >= 0),
    latency_p50_ms     int           CHECK (latency_p50_ms >= 0),
    latency_p95_ms     int           CHECK (latency_p95_ms >= 0),

    last_calculated_at timestamptz   NOT NULL DEFAULT now(),
    created_at         timestamptz   NOT NULL DEFAULT now(),
    updated_at         timestamptz   NOT NULL DEFAULT now(),

    -- NULLS NOT DISTINCT: dòng tổng hợp cấp tenant có channel_id / branch / model_name
    -- NULL. Khuôn UNIQUE mặc định coi mỗi NULL là một giá trị khác nhau, nên consumer
    -- sẽ chèn thêm một dòng mới mỗi lần chạy thay vì cộng dồn vào dòng cũ — số liệu
    -- phình dần mà không có gì báo. Cần PostgreSQL 15 trở lên.
    CONSTRAINT uq_metrics_daily UNIQUE NULLS NOT DISTINCT
        (tenant_id, metric_date, channel_id, branch, model_name),
    CONSTRAINT fk_metrics_channel FOREIGN KEY (channel_id, tenant_id)
        REFERENCES engagement.channels (id, tenant_id) ON DELETE CASCADE
);

CREATE INDEX ix_metrics_daily_range
    ON analytics.metrics_daily (tenant_id, metric_date DESC);

COMMENT ON TABLE analytics.metrics_daily IS
    'Mô hình đọc của UC006, UC036, UC037, UC038, UC039. Một dòng = (doanh nghiệp, ngày, kênh, '
    'nhánh xử lý, mô hình). Chiều nào không áp dụng thì để NULL và cộng dồn ở mức thô hơn.';
COMMENT ON COLUMN analytics.metrics_daily.model_name IS
    'UC039 2.2: đổi mô hình giữa kỳ báo cáo thì phải tách số liệu theo từng phiên bản, '
    'nếu không thì so sánh trước/sau là so hai thứ khác nhau.';
COMMENT ON COLUMN analytics.metrics_daily.latency_p50_ms IS
    'Phân vị tính TRONG NGÀY. Gộp nhiều ngày lại thì phân vị của tổng không bằng phân vị của '
    'từng ngày — báo cáo nhiều ngày phải nói rõ là khoảng, hoặc dùng latency_sum_ms/interaction_count '
    'cho trung bình. Giữ dữ liệu thô để tính phân vị chính xác là việc của ai.ai_interactions.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. UC042 — vì sao KHÔNG có analytics.report_exports
--
-- UC042 luồng chính (bước 5-8) mô tả một công việc chạy nền có trạng thái và có
-- hạn dùng của liên kết tải. Nhưng nhánh 4.2 của chính use case đó nói: "Nếu khối
-- lượng dữ liệu nhỏ → xuất trực tiếp và trả tệp ngay, KHÔNG CẦN TẠO CÔNG VIỆC CHẠY
-- NỀN." Ở quy mô doanh nghiệp vừa và nhỏ, mọi báo cáo trong 42 use case đều rơi vào
-- nhánh đó — dữ liệu một chu kỳ của một tenant xuất hết trong một request.
--
-- Nên UC042 hiện thực theo nhánh 4.2: POST /reports/exports sinh tệp đồng bộ và trả
-- thẳng, hậu điều kiện "ghi thao tác xuất vào nhật ký kiểm toán" do platform.audit_logs
-- đảm nhiệm với action = REPORT_EXPORTED kèm phạm vi dữ liệu.
--
-- Cái mất: không có danh sách tệp đã xuất, không có hạn dùng của liên kết — nên
-- SCR053 bị gỡ khỏi dashboard cùng lúc với migration này. Thêm bảng report_exports
-- khi một lần xuất vượt quá 30 giây; nó thuần cộng thêm, không đòi sửa gì đang có.
-- ─────────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Quy tắc phân công — hai cột trên tenants, không phải bảng riêng
--
-- UC014 bước 6 và UC031 bước 5 (luồng chính) chỉ cần "chọn nhân viên phù hợp theo
-- quy tắc phân công đã cấu hình". UC015 2b (luồng THAY THẾ) mới mô tả quy tắc theo
-- kênh và theo thẻ.
--
-- Một doanh nghiệp vừa và nhỏ có một chế độ phân công, không phải một tập quy tắc
-- có vòng đời riêng. Đặt cạnh lead_score_threshold và auto_lead_creation ở V102 vì
-- chúng cùng là cấu hình hành vi tự động của doanh nghiệp.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE platform.tenants
    ADD COLUMN assignment_mode varchar(20) NOT NULL DEFAULT 'LEAST_BUSY'
        CHECK (assignment_mode IN ('ROUND_ROBIN','LEAST_BUSY','MANUAL')),
    ADD COLUMN assignment_config jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN platform.tenants.assignment_mode IS
    'MANUAL: hội thoại vào hàng chờ chung, không tự gán. LEAST_BUSY là mặc định vì nó không '
    'cần cấu hình gì thêm và đúng với luồng chính của UC014/UC031.';
COMMENT ON COLUMN platform.tenants.assignment_config IS
    'Tuỳ chọn theo kênh và theo thẻ của UC015 2b: {"byChannel":{...},"byTag":{...}}. '
    'Rỗng thì áp assignment_mode cho mọi hội thoại.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Quyền cho crm_app — V111 không với tới ba bảng vừa tạo
-- ─────────────────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE
    ON sales.lead_scores, analytics.metrics_daily TO crm_app;

-- Lịch sử điểm chỉ ghi thêm — sửa một điểm cũ là làm hỏng chính thứ UC030 6.2 muốn
-- bảo toàn. DELETE thì vẫn giữ: UC041 phải xoá được features chứa dữ liệu cá nhân.
REVOKE UPDATE ON sales.lead_scores FROM crm_app;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. RLS — khuôn chuẩn của V112
--
-- Cả hai đều có tenant_id và đều được truy vấn theo yêu cầu người dùng, nên KHÔNG
-- thuộc nhóm ngoại lệ outbox_events / processed_events. Sau migration này, truy vấn
-- kiểm ở migration/README.md vẫn phải trả về đúng BA dòng như cũ.
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
    full_name text;
    tbl       text[] := ARRAY[
        'sales.lead_scores',
        'analytics.metrics_daily'
    ];
BEGIN
    FOREACH full_name IN ARRAY tbl LOOP
        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', full_name);
        EXECUTE format('ALTER TABLE %s FORCE  ROW LEVEL SECURITY', full_name);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %s
                USING      (tenant_id = platform.current_tenant())
                WITH CHECK (tenant_id = platform.current_tenant())
        $f$, full_name);
    END LOOP;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. Trigger updated_at — V112 mục 6 chỉ quét các bảng có mặt lúc đó
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TRIGGER trg_touch_updated_at BEFORE UPDATE ON sales.lead_scores
    FOR EACH ROW EXECUTE FUNCTION platform.touch_updated_at();
CREATE TRIGGER trg_touch_updated_at BEFORE UPDATE ON analytics.metrics_daily
    FOR EACH ROW EXECUTE FUNCTION platform.touch_updated_at();
