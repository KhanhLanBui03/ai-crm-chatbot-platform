-- Chỉ mục HNSW cho truy hồi vector. CHẠY SAU KHI ĐÃ NẠP DỮ LIỆU, không phải trước.
--
-- Vì sao không nằm trong dải Flyway V2xx: Flyway chạy lúc khởi động ứng dụng, tức
-- luôn là lúc bảng còn rỗng. Dựng HNSW trên bảng rỗng rồi chèn từng dòng cho đồ thị
-- kém hơn hẳn dựng một lần trên tập đã đủ — chất lượng truy hồi giảm mà không có
-- dấu hiệu nào báo, chỉ thấy Recall@5 thấp bất thường ở chương thực nghiệm.
--
-- Cách chạy:
--   docker compose exec -T postgres psql -U crm_owner -d thesis_crm \
--       < ai-service/scripts/create_hnsw_index.sql
--
-- Chạy lại được nhiều lần: có IF NOT EXISTS. Muốn xây lại sau khi đổi mô hình nhúng
-- thì DROP trước, xem cuối file.

SET maintenance_work_mem = '512MB';   -- dựng đồ thị nhanh hơn hẳn; trả về mặc định sau khi xong

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_chunk_embedding
    ON knowledge.knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

RESET maintenance_work_mem;

ANALYZE knowledge.knowledge_chunks;

-- Kiểm chỉ mục có được dùng thật không — nếu thấy Seq Scan thì ef_search quá nhỏ
-- hoặc bảng còn quá ít dòng để bộ tối ưu chọn chỉ mục:
--
--   SET hnsw.ef_search = 40;
--   EXPLAIN ANALYZE
--   SELECT id FROM knowledge.knowledge_chunks
--    WHERE tenant_id = '<uuid>'
--    ORDER BY embedding <=> '[...]'::vector LIMIT 8;
--
-- Xây lại sau khi đổi mô hình nhúng (embedding_model / embedding_version đổi):
--
--   DROP INDEX CONCURRENTLY knowledge.ix_chunk_embedding;
--   -- nạp lại embedding cho các dòng cần đổi, rồi chạy lại file này
