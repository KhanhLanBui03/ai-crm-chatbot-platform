-- V202 — Tài liệu tri thức.
-- UC018 · UC019 · UC020
--
-- Trạng thái nạp gộp thẳng vào cột status thay vì bảng ingestion_jobs riêng: một
-- tài liệu có đúng một tiến trình nạp đang chạy.

CREATE TABLE knowledge.knowledge_documents (
    id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    -- KHÔNG có REFERENCES platform.tenants: tham chiếu liên làn (ADR-0002).
    tenant_id       uuid         NOT NULL,
    title           varchar(255) NOT NULL,
    source_type     varchar(30)  NOT NULL
                    CHECK (source_type IN ('PDF','DOCX','TXT','MD','HTML','URL')),
    file_name       varchar(255),
    file_path       text,
    mime_type       varchar(100),
    file_size_bytes bigint       CHECK (file_size_bytes >= 0),
    source_url      text,
    language        varchar(10)  NOT NULL DEFAULT 'vi',
    status          varchar(30)  NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING','PROCESSING','READY','FAILED','ARCHIVED')),
    chunk_count     int          NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
    error_message   text,
    version         int          NOT NULL DEFAULT 1 CHECK (version > 0),
    uploaded_by     uuid,        -- trỏ platform.users, không FK
    indexed_at      timestamptz,
    created_at      timestamptz  NOT NULL DEFAULT now(),
    updated_at      timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_doc_title_version UNIQUE (tenant_id, title, version),
    -- Nạp hỏng thì phải nói vì sao; hiển thị nguyên văn cho người dùng sửa file.
    CONSTRAINT ck_doc_failed CHECK (status <> 'FAILED' OR error_message IS NOT NULL),
    CONSTRAINT ck_doc_source CHECK (
        (source_type = 'URL' AND source_url IS NOT NULL) OR
        (source_type <> 'URL' AND file_path IS NOT NULL)
    )
);

CREATE INDEX ix_doc_tenant_status
    ON knowledge.knowledge_documents (tenant_id, status, created_at DESC);

COMMENT ON COLUMN knowledge.knowledge_documents.version IS
    'Tải lại tài liệu cùng tên thì tăng version, không đè bản cũ — câu trả lời đã sinh vẫn '
    'trích dẫn được đúng bản đã dùng.';
COMMENT ON COLUMN knowledge.knowledge_documents.status IS
    'Gộp vòng đời nạp vào đây thay cho bảng ingestion_jobs. Endpoint /ingestion-jobs của hợp '
    'đồng hiện chạy trên dữ liệu giả lập — xem docs/erd-ai-crm.md mục "Endpoint chưa có bảng thật".';
