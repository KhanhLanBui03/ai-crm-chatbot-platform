-- V107 — Hội thoại và tin nhắn. Thực thể trung tâm của hệ thống.
-- UC010 · UC012 · UC013 · UC014 · UC015 · UC026 · UC038 · UC041

-- ─────────────────────────────────────────────────────────────────────────────
-- conversations
--
-- status là MỘT cột, không tách status + handled_by: hợp đồng
-- docs/openapi/dashboard-api.yaml (TrangThaiHoiThoai) khai đúng năm giá trị này,
-- và ba giá trị đầu đã mã hoá sẵn việc ai đang xử lý.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE engagement.conversations (
    id                  uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid         NOT NULL REFERENCES platform.tenants (id),
    channel_id          uuid         NOT NULL,
    channel_identity_id uuid         NOT NULL,
    contact_id          uuid,
    subject             varchar(200),
    status              varchar(30)  NOT NULL DEFAULT 'BOT_HANDLING'
                        CHECK (status IN ('BOT_HANDLING','PENDING_AGENT','AGENT_HANDLING',
                                          'RESOLVED','CLOSED')),
    priority            varchar(20)  NOT NULL DEFAULT 'NORMAL'
                        CHECK (priority IN ('LOW','NORMAL','HIGH','URGENT')),
    assigned_user_id    uuid,
    assigned_at         timestamptz,
    handover_at         timestamptz,
    handover_reason     varchar(30)
                        CHECK (handover_reason IN ('CUSTOMER_REQUEST','LOW_CONFIDENCE',
                                                   'NO_GROUNDING','NEGATIVE_SENTIMENT',
                                                   'REPEATED_FAILURE','WRITE_TOOL_APPROVAL',
                                                   'QUOTA_EXCEEDED','LLM_ERROR')),
    primary_intent      varchar(50),
    topic               varchar(100),
    sentiment           varchar(20)
                        CHECK (sentiment IN ('POSITIVE','NEUTRAL','NEGATIVE')),
    summary             text,
    summarized_at       timestamptz,
    message_count       int          NOT NULL DEFAULT 0 CHECK (message_count >= 0),
    unread_count        int          NOT NULL DEFAULT 0 CHECK (unread_count >= 0),
    first_response_at   timestamptz,
    last_message_at     timestamptz,
    resolved_at         timestamptz,
    closed_reason       varchar(50),
    csat_score          smallint     CHECK (csat_score BETWEEN 1 AND 5),
    created_at          timestamptz  NOT NULL DEFAULT now(),
    updated_at          timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_conversations_tenant UNIQUE (id, tenant_id),
    CONSTRAINT fk_conv_channel FOREIGN KEY (channel_id, tenant_id)
        REFERENCES engagement.channels (id, tenant_id),
    CONSTRAINT fk_conv_identity FOREIGN KEY (channel_identity_id, tenant_id)
        REFERENCES engagement.channel_identities (id, tenant_id),
    CONSTRAINT fk_conv_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id),
    CONSTRAINT fk_conv_assignee FOREIGN KEY (assigned_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    -- UC015: đã giao cho ai thì phải biết giao lúc nào.
    CONSTRAINT ck_conv_assigned CHECK ((assigned_user_id IS NULL) = (assigned_at IS NULL)),
    -- UC014: chuyển giao thì phải có lý do — số liệu này là cơ sở đo tỉ lệ tự xử lý.
    CONSTRAINT ck_conv_handover CHECK ((handover_at IS NULL) = (handover_reason IS NULL))
);

-- Truy vấn chạy nhiều nhất trong toàn hệ thống: hộp thư hợp nhất.
CREATE INDEX ix_conv_inbox
    ON engagement.conversations (tenant_id, status, last_message_at DESC NULLS LAST);
CREATE INDEX ix_conv_mine
    ON engagement.conversations (tenant_id, assigned_user_id, status);
CREATE INDEX ix_conv_contact
    ON engagement.conversations (tenant_id, contact_id, created_at DESC);
CREATE INDEX ix_conv_topic
    ON engagement.conversations (tenant_id, topic, created_at DESC)
    WHERE topic IS NOT NULL;

COMMENT ON COLUMN engagement.conversations.message_count IS
    'Denormalization CÓ CHỦ Ý, giữ đồng bộ bằng trigger bên dưới. Hộp thư là màn mở nhiều nhất; '
    'đếm lại messages cho 50 dòng danh sách là 50 lần quét bảng lớn nhất.';

-- ─────────────────────────────────────────────────────────────────────────────
-- messages
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE engagement.messages (
    id                  uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid         NOT NULL REFERENCES platform.tenants (id),
    conversation_id     uuid         NOT NULL,
    sender_type         varchar(20)  NOT NULL
                        CHECK (sender_type IN ('CUSTOMER','BOT','AGENT','SYSTEM')),
    sender_user_id      uuid,
    direction           varchar(10)  NOT NULL CHECK (direction IN ('INBOUND','OUTBOUND')),
    content             text         NOT NULL,
    content_type        varchar(20)  NOT NULL DEFAULT 'TEXT'
                        CHECK (content_type IN ('TEXT','IMAGE','FILE','STICKER',
                                                'LOCATION','SYSTEM_NOTE')),
    attachments         jsonb        NOT NULL DEFAULT '[]'::jsonb,
    external_message_id varchar(255),
    delivery_status     varchar(20)  NOT NULL DEFAULT 'PENDING'
                        CHECK (delivery_status IN ('PENDING','SENT','DELIVERED','FAILED')),
    ai_interaction_id   uuid,
    is_redacted         boolean      NOT NULL DEFAULT false,
    sent_at             timestamptz  NOT NULL DEFAULT now(),
    created_at          timestamptz  NOT NULL DEFAULT now(),
    updated_at          timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT fk_msg_conversation FOREIGN KEY (conversation_id, tenant_id)
        REFERENCES engagement.conversations (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_msg_sender FOREIGN KEY (sender_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    -- Chỉ tin do nhân viên gửi mới có người gửi cụ thể.
    CONSTRAINT ck_msg_sender CHECK (
        (sender_type = 'AGENT' AND sender_user_id IS NOT NULL) OR
        (sender_type <> 'AGENT' AND sender_user_id IS NULL)
    ),
    CONSTRAINT ck_msg_attachments CHECK (jsonb_typeof(attachments) = 'array')
);

-- CHỐNG NHẬN TRÙNG WEBHOOK. Zalo và Messenger đều gửi lại khi không nhận được
-- 200 kịp; không có ràng buộc này thì hội thoại đầy tin nhắn lặp.
CREATE UNIQUE INDEX uq_msg_external
    ON engagement.messages (tenant_id, external_message_id)
    WHERE external_message_id IS NOT NULL;

CREATE INDEX ix_msg_conversation ON engagement.messages (conversation_id, sent_at);
CREATE INDEX ix_msg_tenant_time  ON engagement.messages (tenant_id, sent_at DESC);

COMMENT ON COLUMN engagement.messages.ai_interaction_id IS
    'Trỏ ai.ai_interactions. KHÔNG có khoá ngoại — tham chiếu liên làn (ADR-0002).';
COMMENT ON COLUMN engagement.messages.attachments IS
    'Mảng {url, mime, size, name}. Không tách bảng vì tệp đính kèm không bao giờ '
    'được truy vấn độc lập với tin nhắn cha.';

-- ─────────────────────────────────────────────────────────────────────────────
-- Giữ message_count / unread_count / last_message_at đồng bộ.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE FUNCTION engagement.sync_conversation_counters() RETURNS trigger AS $$
BEGIN
    UPDATE engagement.conversations
       SET message_count   = message_count + 1,
           -- chỉ tin của khách mới làm hội thoại thành "chưa đọc"
           unread_count    = unread_count + CASE WHEN NEW.sender_type = 'CUSTOMER' THEN 1 ELSE 0 END,
           last_message_at = GREATEST(COALESCE(last_message_at, NEW.sent_at), NEW.sent_at),
           first_response_at = CASE
               WHEN first_response_at IS NULL AND NEW.sender_type IN ('BOT','AGENT')
               THEN NEW.sent_at ELSE first_response_at END,
           updated_at      = now()
     WHERE id = NEW.conversation_id;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_conversation_counters
    AFTER INSERT ON engagement.messages
    FOR EACH ROW EXECUTE FUNCTION engagement.sync_conversation_counters();
