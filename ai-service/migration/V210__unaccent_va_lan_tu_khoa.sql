-- V210 — Làn từ khoá tìm được cả khi khách gõ KHÔNG DẤU.
-- UC019 · UC023
--
-- Ba việc, theo đúng thứ tự phụ thuộc:
--   1. extension unaccent
--   2. hàm bọc knowledge.f_unaccent() khai IMMUTABLE
--   3. content_segmented thành cột GENERATED tính từ content qua hàm ở bước 2
--
-- Không sửa V203: V201–V209 đã chạy trên CSDL dev, sửa là lệch checksum Flyway.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. unaccent — bỏ dấu tiếng Việt, kể cả đ → d
--
-- Khách gõ "chinh sach doi tra" trên điện thoại; tài liệu viết "Chính sách đổi trả". Không
-- bỏ dấu thì làn từ khoá không khớp một âm tiết nào — chỉ còn làn vector gánh, mà vector
-- vốn yếu đúng ở chỗ làn từ khoá mạnh: mã sản phẩm, số liệu, tên riêng.
--
-- scripts/init-db.sql đã tạo sẵn extension này cho container dev, nhưng đó là script khởi
-- tạo của Docker — CSDL production (RDS) không chạy nó. Hàm ở bước 2 phụ thuộc vào extension,
-- nên migration phải tự bảo đảm nó có mặt. IF NOT EXISTS: chạy trên dev thì không làm gì.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. f_unaccent — vì sao phải có hàm BỌC, không gọi thẳng unaccent()
--
-- Cột GENERATED và chỉ mục biểu thức chỉ nhận hàm IMMUTABLE: Postgres tính giá trị MỘT lần
-- lúc ghi rồi lưu lại, nên phải được hứa rằng cùng đầu vào luôn ra cùng đầu ra. unaccent(text)
-- bản gốc chỉ là STABLE, vì nó tìm từ điển "unaccent" theo search_path LÚC CHẠY — đổi
-- search_path là có thể ra kết quả khác. Postgres từ chối nó với lỗi
--   "generation expression is not immutable".
--
-- Hàm bọc gỡ được điều đó bằng cách chốt cứng cả hai thứ phụ thuộc vào search_path:
--   - gọi public.unaccent (có tên schema)
--   - truyền thẳng từ điển 'public.unaccent'::regdictionary (dạng hai tham số)
-- Khi đó kết quả chỉ còn phụ thuộc đầu vào, và lời hứa IMMUTABLE là thật.
--
-- Cái giá phải biết: IMMUTABLE là LỜI HỨA của người viết, Postgres không kiểm. Nếu ai đó sửa
-- tệp unaccent.rules trên máy chủ, các dòng đã lưu vẫn mang giá trị cũ cho tới khi ghi lại.
-- Với tiếng Việt, bảng quy tắc là bất biến trên thực tế — chấp nhận được.
--
-- PARALLEL SAFE: cho phép quét song song. STRICT: NULL vào thì NULL ra, không gọi hàm.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION knowledge.f_unaccent(text)
    RETURNS text
    LANGUAGE sql
    IMMUTABLE PARALLEL SAFE STRICT
AS $$
    SELECT public.unaccent('public.unaccent'::regdictionary, $1)
$$;

COMMENT ON FUNCTION knowledge.f_unaccent(text) IS
    'Bỏ dấu tiếng Việt, IMMUTABLE để dùng được trong cột GENERATED và chỉ mục. Dùng cho CẢ HAI '
    'đầu của làn từ khoá: content_segmented lúc ghi, và to_tsquery(''simple'', '
    'knowledge.f_unaccent(:q)) lúc truy vấn. Hai đầu bỏ dấu bằng hai hàm khác nhau là recall tụt '
    'mà không có lỗi nào báo ra.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. content_segmented thành cột GENERATED
--
-- V203 để cột này là tsvector thường, ứng dụng tự tính rồi ghi vào. Đổi sang GENERATED vì:
--   - Không còn đường nào ghi một tsvector tính KHÁC công thức: ứng dụng chỉ ghi content,
--     Postgres tự tính phần còn lại. INSERT có kèm content_segmented bị từ chối.
--   - Sửa content (UC020) là tsvector tự tính lại — không có chuyện quên cập nhật.
--
-- Chỉ mục theo ÂM TIẾT, không theo từ đã tách bằng pyvi. Đã đo trước khi quyết:
--   - Postgres coi '_' là dấu tách, nên "chính_sách" của pyvi vẫn thành hai âm tiết
--     'chinh':1 'sach':2 liền kề — tách từ phía tài liệu không đổi được chỉ mục.
--   - pyvi không ghép được từ trong câu KHÔNG DẤU ("chinh sach" ra hai âm tiết rời), nên chỉ
--     mục theo từ ghép sẽ trượt đúng loại câu hỏi cần làn này nhất.
-- Việc ghép từ ghép chuyển sang phía câu hỏi: src/ai/rag/tsquery.py dựng "chinh <-> sach"
-- (liền kề) cho từ ghép, OR giữa các từ. Tên cột giữ nguyên để không đổi hợp đồng ERD.
--
-- 'simple': không stemming, không stopword — cả hai đều viết cho tiếng Anh, áp lên tiếng
-- Việt chỉ làm hỏng. to_tsvector(regconfig, text) dạng HAI tham số mới là IMMUTABLE; dạng
-- một tham số đọc default_text_search_config lúc chạy nên chỉ là STABLE.
--
-- DROP rồi ADD thay vì ALTER: Postgres 16 không đổi được một cột thường thành GENERATED.
-- An toàn vì bảng chưa có chunk thật (UC019 bắt đầu từ Ngày 4); nếu đã có thì cột mới vẫn
-- được tính lại đầy đủ cho mọi dòng ngay trong câu ADD COLUMN.
-- ─────────────────────────────────────────────────────────────────────────────
DROP INDEX IF EXISTS knowledge.ix_chunk_fts;

ALTER TABLE knowledge.knowledge_chunks DROP COLUMN content_segmented;

ALTER TABLE knowledge.knowledge_chunks
    ADD COLUMN content_segmented tsvector
        GENERATED ALWAYS AS (
            to_tsvector('simple'::regconfig, knowledge.f_unaccent(content))
        ) STORED;

CREATE INDEX ix_chunk_fts ON knowledge.knowledge_chunks USING GIN (content_segmented);

COMMENT ON COLUMN knowledge.knowledge_chunks.content_segmented IS
    'GENERATED — to_tsvector(''simple'', knowledge.f_unaccent(content)): theo âm tiết, chữ '
    'thường, bỏ dấu. Không ghi trực tiếp. Truy vấn bằng to_tsquery(''simple'', '
    'knowledge.f_unaccent(<chuỗi từ src/ai/rag/tsquery.py>)).';

-- Không GRANT, không RLS: cột mới kế thừa quyền và policy của bảng (V206, V207). Hàm mới
-- mặc định EXECUTE cho PUBLIC; ai_app đã có USAGE trên schema knowledge.
