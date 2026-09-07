-- V106 — Kênh kết nối và danh tính khách trên từng kênh.
-- UC008 · UC009 · UC010 · UC011

-- ─────────────────────────────────────────────────────────────────────────────
-- channels — một bảng cho cả ba kênh; phần khác nhau nằm trong config jsonb.
-- Tách ba bảng theo loại kênh là nhân ba mọi truy vấn hộp thư hợp nhất mà không
-- thêm ràng buộc nào có ích.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE engagement.channels (
    id                       uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                uuid         NOT NULL REFERENCES platform.tenants (id),
    type                     varchar(30)  NOT NULL
                             CHECK (type IN ('WEB_WIDGET','ZALO','FACEBOOK')),
    name                     varchar(150) NOT NULL,
    external_id              varchar(255),
    widget_key               varchar(64),
    status                   varchar(30)  NOT NULL DEFAULT 'DISCONNECTED'
                             CHECK (status IN ('DISCONNECTED','PENDING_VERIFY','ACTIVE','ERROR')),
    config                   jsonb        NOT NULL DEFAULT '{}'::jsonb,
    credential_encrypted     bytea,
    credential_key_id        varchar(64),
    token_expires_at         timestamptz,
    webhook_secret_encrypted bytea,
    last_error               text,
    last_synced_at           timestamptz,
    created_by               uuid,
    created_at               timestamptz  NOT NULL DEFAULT now(),
    updated_at               timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_channels_tenant UNIQUE (id, tenant_id),
    CONSTRAINT uq_channels_widget_key UNIQUE (widget_key),
    CONSTRAINT fk_channels_creator FOREIGN KEY (created_by, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    -- Web Widget nhận diện bằng widget_key; hai kênh còn lại bằng ID của nền tảng.
    CONSTRAINT ck_channels_identifier CHECK (
        (type = 'WEB_WIDGET' AND widget_key IS NOT NULL) OR
        (type <> 'WEB_WIDGET' AND widget_key IS NULL)
    ),
    -- Bí mật đã mã hoá thì phải biết mã bằng khoá nào, nếu không thì không xoay khoá được.
    CONSTRAINT ck_channels_key_id CHECK (
        credential_encrypted IS NULL OR credential_key_id IS NOT NULL
    )
);

CREATE UNIQUE INDEX uq_channels_external
    ON engagement.channels (tenant_id, type, external_id)
    WHERE external_id IS NOT NULL;

CREATE INDEX ix_channels_tenant ON engagement.channels (tenant_id, status);

COMMENT ON COLUMN engagement.channels.config IS
    'Gộp cấu hình Web Widget vào đây: màu, lời chào, tên miền được phép, vị trí bong bóng.';
COMMENT ON COLUMN engagement.channels.credential_encrypted IS
    'Access token ĐÃ MÃ HOÁ. Không bao giờ lưu văn bản thô (UC008 bước 7).';
COMMENT ON COLUMN engagement.channels.widget_key IS
    'Khoá công khai nhúng vào thẻ script. UNIQUE toàn cục vì tra cứu trước khi biết tenant.';

-- ─────────────────────────────────────────────────────────────────────────────
-- channel_identities — bảng làm cho "đa kênh" có nghĩa.
--
-- Không có bảng này thì một người nhắn qua Zalo rồi qua widget là hai khách hàng
-- khác nhau, và toàn bộ giá trị của hộp thư hợp nhất biến mất. Hợp nhất danh tính
-- là đặt contact_id cho nhiều dòng cùng trỏ về một contact.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE engagement.channel_identities (
    id               uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid         NOT NULL REFERENCES platform.tenants (id),
    channel_id       uuid         NOT NULL,
    contact_id       uuid,
    external_user_id varchar(255) NOT NULL,
    display_name     varchar(200),
    avatar_url       text,
    raw_profile      jsonb,
    first_seen_at    timestamptz  NOT NULL DEFAULT now(),
    last_seen_at     timestamptz  NOT NULL DEFAULT now(),
    created_at       timestamptz  NOT NULL DEFAULT now(),
    updated_at       timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_identity_external UNIQUE (tenant_id, channel_id, external_user_id),
    CONSTRAINT uq_identity_tenant UNIQUE (id, tenant_id),
    CONSTRAINT fk_identity_channel FOREIGN KEY (channel_id, tenant_id)
        REFERENCES engagement.channels (id, tenant_id),
    CONSTRAINT fk_identity_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id)
);

CREATE INDEX ix_identity_contact ON engagement.channel_identities (tenant_id, contact_id);

COMMENT ON COLUMN engagement.channel_identities.contact_id IS
    'NULL cho tới khi hợp nhất được danh tính — khách ẩn danh vẫn nhắn tin được.';
COMMENT ON COLUMN engagement.channel_identities.external_user_id IS
    'PSID Messenger / user id Zalo OA / uuid trình duyệt của Web Widget.';
