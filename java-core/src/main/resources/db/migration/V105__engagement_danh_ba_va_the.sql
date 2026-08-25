-- V105 — Danh bạ khách hàng, thẻ phân loại, ghi chú nội bộ.
-- UC011 · UC016 · UC017 · UC029 · UC041

-- ─────────────────────────────────────────────────────────────────────────────
-- contacts — khách hàng đã hợp nhất từ nhiều kênh.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE engagement.contacts (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            uuid         NOT NULL REFERENCES platform.tenants (id),
    full_name            varchar(200),
    email                varchar(255),
    phone                varchar(20),
    company              varchar(200),
    primary_channel      varchar(30)  NOT NULL
                         CHECK (primary_channel IN ('WEB_WIDGET','ZALO','FACEBOOK','PHONE')),
    owner_user_id        uuid,
    status               varchar(30)  NOT NULL DEFAULT 'ACTIVE'
                         CHECK (status IN ('ACTIVE','MERGED','ANONYMIZED')),
    merged_into_contact_id uuid,
    last_contacted_at    timestamptz,
    consent_marketing    boolean      NOT NULL DEFAULT false,
    anonymized_at        timestamptz,
    deleted_at           timestamptz,
    created_at           timestamptz  NOT NULL DEFAULT now(),
    updated_at           timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_contacts_tenant UNIQUE (id, tenant_id),
    CONSTRAINT fk_contacts_owner FOREIGN KEY (owner_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    CONSTRAINT fk_contacts_merged FOREIGN KEY (merged_into_contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id),
    -- UC016: gộp khách hàng thì phải nói gộp vào đâu; ngược lại thì không.
    CONSTRAINT ck_contacts_merged CHECK (
        (status = 'MERGED') = (merged_into_contact_id IS NOT NULL)
    ),
    CONSTRAINT ck_contacts_anonymized CHECK (
        (status = 'ANONYMIZED') = (anonymized_at IS NOT NULL)
    )
);

-- UNIQUE BỘ PHẬN, không phải UNIQUE thường: khách ẩn danh chưa có email, và bản
-- ghi đã xoá mềm phải nhường chỗ cho bản ghi mới cùng email.
CREATE UNIQUE INDEX uq_contacts_email ON engagement.contacts (tenant_id, lower(email))
    WHERE email IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX uq_contacts_phone ON engagement.contacts (tenant_id, phone)
    WHERE phone IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX ix_contacts_tenant_recent
    ON engagement.contacts (tenant_id, last_contacted_at DESC NULLS LAST)
    WHERE deleted_at IS NULL;
CREATE INDEX ix_contacts_owner ON engagement.contacts (tenant_id, owner_user_id);

COMMENT ON COLUMN engagement.contacts.anonymized_at IS
    'UC041, Nghị định 13/2023/NĐ-CP: ẩn danh hoá thay cho xoá vật lý.';

-- ─────────────────────────────────────────────────────────────────────────────
-- tags và bảng nối contact_tags
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE engagement.tags (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid        NOT NULL REFERENCES platform.tenants (id),
    name        varchar(50) NOT NULL,
    color       varchar(7)  NOT NULL DEFAULT '#6366F1'
                CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    description text,
    usage_count int         NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
    created_by  uuid,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_tags_tenant UNIQUE (id, tenant_id),
    CONSTRAINT fk_tags_creator FOREIGN KEY (created_by, tenant_id)
        REFERENCES platform.users (id, tenant_id)
);

-- lower(name): chặn "VIP" và "vip" cùng tồn tại trong một doanh nghiệp.
CREATE UNIQUE INDEX uq_tags_tenant_name ON engagement.tags (tenant_id, lower(name));

CREATE TABLE engagement.contact_tags (
    contact_id uuid        NOT NULL,
    tag_id     uuid        NOT NULL,
    tenant_id  uuid        NOT NULL REFERENCES platform.tenants (id),
    tagged_by  uuid,
    tagged_at  timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (contact_id, tag_id),
    CONSTRAINT fk_contact_tags_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_contact_tags_tag FOREIGN KEY (tag_id, tenant_id)
        REFERENCES engagement.tags (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_contact_tags_user FOREIGN KEY (tagged_by, tenant_id)
        REFERENCES platform.users (id, tenant_id)
);

CREATE INDEX ix_contact_tags_tag ON engagement.contact_tags (tenant_id, tag_id);

COMMENT ON COLUMN engagement.contact_tags.tagged_by IS 'NULL nghĩa là do tác tử AI gắn tự động.';

-- ─────────────────────────────────────────────────────────────────────────────
-- contact_notes — ghi chú nội bộ, KHÔNG BAO GIỜ hiển thị cho khách hàng.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE engagement.contact_notes (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid        NOT NULL REFERENCES platform.tenants (id),
    contact_id     uuid        NOT NULL,
    author_user_id uuid        NOT NULL,
    content        text        NOT NULL CHECK (length(btrim(content)) > 0),
    is_pinned      boolean     NOT NULL DEFAULT false,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_notes_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_notes_author FOREIGN KEY (author_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id)
);

CREATE INDEX ix_notes_contact
    ON engagement.contact_notes (tenant_id, contact_id, is_pinned DESC, created_at DESC);
