-- V204 — Lượt xử lý của tác tử AI và đánh giá chất lượng.
-- UC022 · UC023 · UC024 · UC025 · UC026 · UC027 · UC029 · UC039
--
-- ai_interactions là bảng đắt giá nhất về mặt điểm số. Không có nó thì không tính
-- được chi phí mỗi hội thoại, không phân tích được độ trễ theo nhánh, và không trả
-- lời được câu chắc chắn bị hỏi: "làm sao chứng minh bot không bịa?" —
-- retrieved_chunk_ids chính là câu trả lời.

CREATE TABLE ai.ai_interactions (
    id                  uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid          NOT NULL,
    -- Ba cột dưới trỏ sang engagement.* nhưng KHÔNG có khoá ngoại — liên làn.
    conversation_id     uuid          NOT NULL,
    message_id          uuid,
    branch              varchar(30)   NOT NULL
                        CHECK (branch IN ('SMALL_TALK','RAG','TOOL_CALL','CLARIFY',
                                          'HANDOFF','SUMMARY','EXTRACTION')),
    intent              varchar(50),
    intent_confidence   numeric(4,3)  CHECK (intent_confidence BETWEEN 0 AND 1),
    user_query          text,
    response_text       text,
    retrieved_chunk_ids uuid[]        NOT NULL DEFAULT '{}',
    retrieval_top_score numeric(5,4),
    is_answered         boolean       NOT NULL,
    refusal_reason      varchar(50)
                        CHECK (refusal_reason IN ('NOT_COVERED','OUT_OF_SCOPE_DATA',
                                                  'LOW_CONFIDENCE','SAFETY_PROBE')),
    model_name          varchar(100)  NOT NULL,
    model_version       varchar(50),
    prompt_tokens       int           NOT NULL DEFAULT 0 CHECK (prompt_tokens >= 0),
    completion_tokens   int           NOT NULL DEFAULT 0 CHECK (completion_tokens >= 0),
    total_tokens        int           NOT NULL DEFAULT 0 CHECK (total_tokens >= 0),
    cost_vnd            numeric(16,4) NOT NULL DEFAULT 0 CHECK (cost_vnd >= 0),
    latency_ms          int           CHECK (latency_ms >= 0),
    status              varchar(20)   NOT NULL DEFAULT 'SUCCESS'
                        CHECK (status IN ('SUCCESS','FAILED','TIMEOUT')),
    error_message       text,
    created_at          timestamptz   NOT NULL DEFAULT now(),
    updated_at          timestamptz   NOT NULL DEFAULT now(),

    -- Từ chối thì phải nói vì sao. Đây là số liệu gốc của UC025.
    CONSTRAINT ck_interaction_refusal CHECK (is_answered OR refusal_reason IS NOT NULL)
);

CREATE INDEX ix_interaction_tenant_time
    ON ai.ai_interactions (tenant_id, created_at DESC);
CREATE INDEX ix_interaction_conversation
    ON ai.ai_interactions (tenant_id, conversation_id, created_at);
CREATE INDEX ix_interaction_branch
    ON ai.ai_interactions (tenant_id, branch, created_at DESC);
-- Truy vấn "vì sao bot từ chối" của màn phân tích chất lượng.
CREATE INDEX ix_interaction_refusal
    ON ai.ai_interactions (tenant_id, refusal_reason, created_at DESC)
    WHERE NOT is_answered;

COMMENT ON COLUMN ai.ai_interactions.cost_vnd IS
    'Bốn chữ số thập phân: một lượt gọi mô hình nhỏ hơn một đồng, làm tròn sớm là mất số liệu.';
COMMENT ON COLUMN ai.ai_interactions.retrieved_chunk_ids IS
    'Mảng thay bảng nối N–N: chỉ đọc theo một chiều ("lượt này trích dẫn đoạn nào"), và bảng nối '
    'sẽ sinh ~5 dòng cho MỖI lượt hỏi đáp — tức bảng lớn nhất hệ thống chỉ để phục vụ một tra cứu.';

-- ─────────────────────────────────────────────────────────────────────────────
-- ai_feedback — nguồn số liệu cho câu "trên N hội thoại thực tế, tỉ lệ phản hồi
-- tích cực là X%", câu mà phần lớn đồ án không viết được.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE ai.ai_feedback (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid        NOT NULL,
    ai_interaction_id uuid        NOT NULL
                      REFERENCES ai.ai_interactions (id) ON DELETE CASCADE,
    rater_type        varchar(20) NOT NULL
                      CHECK (rater_type IN ('CUSTOMER','AGENT','AUTO_EVAL')),
    rater_user_id     uuid,
    rating            varchar(20) NOT NULL CHECK (rating IN ('POSITIVE','NEGATIVE')),
    reason_code       varchar(30)
                      CHECK (reason_code IN ('WRONG_INFO','IRRELEVANT','INCOMPLETE','BAD_TONE')),
    comment           text,
    correction_text   text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    -- Chê thì phải chọn lý do; khen thì không cần.
    CONSTRAINT ck_feedback_reason CHECK (rating = 'POSITIVE' OR reason_code IS NOT NULL),
    CONSTRAINT ck_feedback_rater CHECK (
        (rater_type = 'AGENT' AND rater_user_id IS NOT NULL) OR
        (rater_type <> 'AGENT' AND rater_user_id IS NULL)
    )
);

-- Một lượt chỉ nhận một đánh giá từ mỗi phía.
CREATE UNIQUE INDEX uq_feedback_rater
    ON ai.ai_feedback (ai_interaction_id, rater_type, COALESCE(rater_user_id, '00000000-0000-0000-0000-000000000000'::uuid));

CREATE INDEX ix_feedback_tenant ON ai.ai_feedback (tenant_id, rating, created_at DESC);

COMMENT ON COLUMN ai.ai_feedback.correction_text IS
    'Câu trả lời đúng do nhân viên sửa lại. Đây là nguồn phát hiện khoảng trống tri thức: '
    'truy vấn ai_interactions (is_answered = false) cộng cột này ra danh sách cần bổ sung tài liệu.';
