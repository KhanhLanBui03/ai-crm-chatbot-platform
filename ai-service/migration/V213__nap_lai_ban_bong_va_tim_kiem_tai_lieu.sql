-- V213 — Nạp lại không có khoảnh khắc kho trống (bản ghi bóng) + tìm tài liệu không phân biệt dấu.
-- UC020 · ADR-0031 · kế hoạch Ngày 11
--
-- Không sửa V201–V212: đã chạy trên CSDL dev, sửa là lệch checksum Flyway.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. replaces_document_id — bản ghi bóng của một lượt nạp lại
--
-- Nạp lại KHÔNG chạy trên chính dòng tài liệu: bước nhận việc của UC019 chuyển dòng sang PROCESSING
-- và xoá sạch đoạn cũ, mà truy hồi chỉ lấy đoạn của tài liệu READY — nạp lại tại chỗ là tài liệu
-- biến mất khỏi kho suốt thời gian nạp. Thay vào đó nạp lại tạo một dòng MỚI (bản bóng) trỏ cùng
-- tệp, version + 1, replaces_document_id = dòng cũ, và đi qua ĐÚNG đường nạp có sẵn. Bản cũ vẫn
-- READY và vẫn phục vụ. Khi bản bóng READY, CÙNG transaction đó xoá đoạn của bản cũ và chuyển nó
-- ARCHIVED (document_repository.hoan_tat) — người đọc thấy bản cũ hoặc bản mới, không bao giờ
-- thấy khoảng trống.
--
-- ON DELETE SET NULL: xoá cứng bản cũ (thao tác tay) không được kéo theo bản bóng.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE knowledge.knowledge_documents
    ADD COLUMN replaces_document_id uuid
        REFERENCES knowledge.knowledge_documents (id) ON DELETE SET NULL;

COMMENT ON COLUMN knowledge.knowledge_documents.replaces_document_id IS
    'Bản bóng của lượt nạp lại (UC020): dòng này READY thì dòng được trỏ tới bị xoá đoạn và chuyển '
    'ARCHIVED trong cùng transaction — 0 giây kho trống. NULL với tài liệu tải lên thường.';

-- Mỗi tài liệu chỉ một lượt nạp lại đang chạy. Hai yêu cầu nạp lại tới cùng lúc: một câu INSERT
-- đụng chỉ mục này ⇒ 409 DOCUMENT_BUSY — CSDL quyết, không cần khoá ở tầng ứng dụng.
CREATE UNIQUE INDEX uq_doc_mot_luot_nap_lai
    ON knowledge.knowledge_documents (replaces_document_id)
    WHERE replaces_document_id IS NOT NULL AND status IN ('PENDING', 'PROCESSING');

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Tìm tài liệu không phân biệt hoa thường và dấu — SCR030
--
-- "bao gia" phải khớp "báo giá". Cùng hàm knowledge.f_unaccent của làn từ khoá (V210) — một hàm
-- bỏ dấu cho mọi chỗ. Chỉ mục trigram trên ĐÚNG biểu thức của câu tìm (document_repository.
-- danh_sach), nếu lệch một ký tự là Postgres không dùng được chỉ mục.
--
-- public.gin_trgm_ops có tên schema: Flyway chạy với defaultSchema=knowledge, gọi trần là không
-- thấy lớp toán tử của pg_trgm (cài ở public — init-db.sql).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;

CREATE INDEX ix_doc_tim_kiem
    ON knowledge.knowledge_documents
    USING gin (
        lower(knowledge.f_unaccent(
            title || ' ' || coalesce(description, '') || ' ' || coalesce(file_name, '')
        )) public.gin_trgm_ops
    );

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. knowledge.tim_job_ket — thêm bản bóng chờ nạp
--
-- Bản bóng do ai-service tạo, không có sự kiện crm.kb.document.uploaded nào mang nó tới worker
-- (topic đó của java-core). Bộ quét (mỗi kb_chu_ky_quet_s = 60 s) nhặt nó NGAY, không chờ quá hạn
-- như job kẹt: PENDING + attempt_count = 0 + replaces_document_id khác NULL chỉ có một nghĩa —
-- yêu cầu nạp lại chưa ai nhận.
--
-- Giữ nguyên chữ ký, bốn cột trả về và bốn chốt của V211 (ADR-0024). CREATE OR REPLACE thay TOÀN
-- BỘ thuộc tính của hàm — SECURITY DEFINER và search_path phải ghi lại; quyền EXECUTE thì giữ.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION knowledge.tim_job_ket(p_qua_han interval, p_toi_da int DEFAULT 100)
    RETURNS TABLE (tenant_id uuid, document_id uuid, status varchar, attempt_count smallint)
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT d.tenant_id, d.id, d.status, d.attempt_count
      FROM knowledge.knowledge_documents d
     WHERE (d.updated_at < now() - p_qua_han
            AND (d.status = 'PROCESSING' OR (d.status = 'PENDING' AND d.attempt_count > 0)))
        OR (d.status = 'PENDING' AND d.attempt_count = 0 AND d.replaces_document_id IS NOT NULL)
     ORDER BY d.updated_at
     LIMIT least(greatest(p_toi_da, 1), 500)
$$;

REVOKE ALL ON FUNCTION knowledge.tim_job_ket(interval, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.tim_job_ket(interval, int) TO ai_app;
