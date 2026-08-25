-- V203 — Đoạn tài liệu và vector nhúng. Bảng truy hồi của RAG.
-- UC019 · UC023 · UC025
--
-- Hai làn truy hồi nằm CÙNG một bảng: vector (embedding) và từ khoá
-- (content_segmented). Hợp nhất kết quả bằng RRF k=60 ở tầng ứng dụng rồi rerank
-- lấy top-5. Tách hai bảng thì mỗi lần nạp phải ghi hai nơi và dễ lệch.

CREATE TABLE knowledge.knowledge_chunks (
    id                uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid          NOT NULL,
    document_id       uuid          NOT NULL
                      REFERENCES knowledge.knowledge_documents (id) ON DELETE CASCADE,
    chunk_index       int           NOT NULL CHECK (chunk_index >= 0),
    content           text          NOT NULL,
    content_segmented tsvector,
    token_count       int           NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    embedding         vector(1024),
    embedding_model   varchar(100)  NOT NULL,
    embedding_version varchar(30)   NOT NULL,
    page_number       int,
    heading           varchar(255),
    metadata          jsonb,
    created_at        timestamptz   NOT NULL DEFAULT now(),
    updated_at        timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT uq_chunk_index UNIQUE (document_id, chunk_index)
);

-- Lọc tenant TRƯỚC khi chạm vector. ADR-0007, bề mặt T6: mọi truy vấn vector phải
-- có tenant_id ngay trong câu, không lọc sau khi đã lấy kết quả về.
CREATE INDEX ix_chunk_tenant_doc ON knowledge.knowledge_chunks (tenant_id, document_id);

-- Làn từ khoá của truy hồi lai.
CREATE INDEX ix_chunk_fts ON knowledge.knowledge_chunks USING GIN (content_segmented);

COMMENT ON COLUMN knowledge.knowledge_chunks.embedding_model IS
    'Lưu TRÊN TỪNG DÒNG, không phải một tham số toàn cục: thí nghiệm đổi mô hình nhúng nhiều '
    'lần, và không có cột này thì mỗi lần đổi phải nạp lại toàn bộ kho thay vì xây lại từng phần.';

COMMENT ON TABLE knowledge.knowledge_chunks IS
    'CHỈ MỤC HNSW KHÔNG NẰM Ở ĐÂY. Flyway chạy lúc khởi động, tức luôn là lúc bảng còn rỗng; '
    'dựng HNSW trên bảng rỗng rồi chèn từng dòng cho đồ thị kém hơn hẳn dựng một lần trên tập '
    'đã đủ. Chạy scripts/create_hnsw_index.sql SAU khi nạp xong dữ liệu.';
