-- V211 — Nạp tài liệu chạy qua NHIỀU transaction: đếm lượt, chặng tiến độ, chống trùng sự kiện,
-- quét job kẹt.
-- UC019 · ADR-0024
--
-- Ngày 4 nhận xử lý và phân tích trong MỘT transaction, nên tài liệu đang nạp không bao giờ lộ ra
-- ngoài: SCR033 chỉ thấy PENDING rồi nhảy thẳng sang READY/FAILED. ADR-0024 chọn phương án 2 —
-- commit PROCESSING sớm và ghi từng chặng — để hiện được 6 bước tiến độ. Cái giá: tiến trình chết
-- giữa chừng để lại tài liệu PROCESSING mà không ai nhặt lại. Bốn phần dưới đây trả cái giá đó.
--
-- Không sửa V201–V210: đã chạy trên CSDL dev, sửa là lệch checksum Flyway.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Ba cột tiến độ trên knowledge_documents
--
-- attempt_count — số lần tài liệu đã được NHẬN xử lý (PENDING → PROCESSING). Hai vai trò:
--   (a) trần thử lại: đủ 3 lượt thì chuyển FAILED, không vòng lặp vô hạn trên một tệp làm treo
--       worker;
--   (b) THẺ SỞ HỮU (fencing token): mọi transaction sau bước nhận đều kèm
--       "WHERE status = 'PROCESSING' AND attempt_count = <lượt của mình>". Bộ quét trả tài liệu về
--       PENDING và một lượt khác nhận lại thì attempt_count tăng — lượt cũ (tiến trình treo rồi
--       tỉnh lại) cập nhật 0 dòng và tự dừng, không ghi đè lên lượt mới.
--
-- ingest_step — chặng ĐANG chạy (PROCESSING) hoặc chặng ĐÃ hỏng (FAILED). Hai chặng đầu-cuối của
-- 6 bước SCR033 suy ra từ status, không lưu: PENDING = QUEUED, READY = DONE. Lưu cả hai thì có
-- hai nguồn sự thật cho cùng một điều và sớm muộn sẽ lệch nhau.
--
-- ingest_started_at — lúc lượt hiện tại nhận xử lý. Cùng indexed_at cho ra durationMs của SCR033
-- và thời gian nạp trong báo cáo, không phải đo ở tầng ứng dụng rồi mất khi tiến trình chết.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE knowledge.knowledge_documents
    ADD COLUMN attempt_count smallint NOT NULL DEFAULT 0
        CONSTRAINT ck_doc_attempt CHECK (attempt_count >= 0),
    ADD COLUMN ingest_step varchar(20)
        CONSTRAINT ck_doc_ingest_step_value
        CHECK (ingest_step IN ('EXTRACTING', 'CHUNKING', 'EMBEDDING', 'INDEXING')),
    ADD COLUMN ingest_started_at timestamptz,
    ADD CONSTRAINT ck_doc_ingest_step_status
        CHECK (status IN ('PROCESSING', 'FAILED') OR ingest_step IS NULL);

COMMENT ON COLUMN knowledge.knowledge_documents.attempt_count IS
    'Số lần đã nhận xử lý. Trần 3 (ADR-0024). Cũng là thẻ sở hữu: mọi ghi sau bước nhận đều kèm '
    'attempt_count = lượt của mình, lượt bị bộ quét tước quyền cập nhật 0 dòng và tự dừng.';
COMMENT ON COLUMN knowledge.knowledge_documents.ingest_step IS
    'Chặng đang chạy (PROCESSING) hoặc đã hỏng (FAILED). QUEUED/DONE suy ra từ status, không lưu.';
COMMENT ON COLUMN knowledge.knowledge_documents.ingest_started_at IS
    'Lúc lượt nạp hiện tại nhận xử lý. indexed_at - ingest_started_at = thời gian nạp.';

-- updated_at (trigger V207) là NHỊP TIM: mỗi chặng và mỗi lô 32 đoạn đều UPDATE dòng này. Bộ quét
-- chỉ đọc hai trạng thái đang dở dang — chỉ mục bộ phận nhỏ bằng số tài liệu đang nạp, không phình
-- theo cả kho.
CREATE INDEX ix_doc_dang_nap
    ON knowledge.knowledge_documents (updated_at)
    WHERE status IN ('PENDING', 'PROCESSING');

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. ai.processed_events — chống xử lý trùng sự kiện Kafka
--
-- Vì sao KHÔNG dùng analytics.processed_events (V110) như .claude/rules/kafka-events.md ghi:
-- bảng đó thuộc schema của Track A, và ai_app không có USAGE trên schema analytics — cố ý, là lớp
-- chặn cuối của ADR-0002. Mở quyền cho một bảng hạ tầng là mở một lỗ trên đúng ranh giới đó.
-- Cùng khoá (consumer_group, event_id), cùng cách dùng INSERT … ON CONFLICT DO NOTHING — chỉ khác
-- chỗ ở.
--
-- KHÁC V110 ở chỗ CÓ RLS: consumer của Track B đọc tenant từ vỏ sự kiện TRƯỚC khi ghi bảng này,
-- nên không có lý do "chưa biết tenant" như phía analytics. Dòng ghi nằm cùng transaction với bước
-- nhận xử lý tài liệu (ADR-0024) — sự kiện được đánh dấu đã xử lý đúng lúc tài liệu vào tay
-- worker, không sớm hơn, không muộn hơn.
--
-- event_id là bigint vì java-core lấy platform.outbox_events.id làm event_id (V110).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE ai.processed_events (
    consumer_group varchar(60) NOT NULL,
    event_id       bigint      NOT NULL,
    -- KHÔNG có REFERENCES platform.tenants: tham chiếu liên làn (ADR-0002).
    tenant_id      uuid        NOT NULL,
    aggregate_id   uuid,
    processed_at   timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (consumer_group, event_id)
);

ALTER TABLE ai.processed_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.processed_events FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ai.processed_events
    USING      (tenant_id = ai.current_tenant())
    WITH CHECK (tenant_id = ai.current_tenant());

-- Chỉ SELECT + INSERT. Không UPDATE: một sự kiện đã xử lý thì không "bỏ xử lý". Không DELETE:
-- dọn dòng cũ hơn thời gian giữ của Kafka (30 ngày — quá hạn đó không còn bản tin nào để nhận
-- trùng) là việc của job bảo trì chạy bằng role khác, chưa có.
GRANT SELECT, INSERT ON ai.processed_events TO ai_app;

COMMENT ON TABLE ai.processed_events IS
    'Chống xử lý trùng cho consumer của ai-service (ADR-0024). Bản sao có chủ ý của '
    'analytics.processed_events (V110): ai_app không được chạm schema của Track A (ADR-0002).';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. knowledge.tim_job_ket — lỗ CÓ CHỦ ĐÍCH trong RLS, hẹp nhất có thể
--
-- Bộ quét phải tìm tài liệu kẹt của MỌI tenant, nhưng ai_app chịu RLS FORCE: không đặt
-- app.tenant_id thì mọi câu đọc ném 42501 (V201), đặt thì chỉ thấy một tenant. Và ai-service không
-- biết danh sách tenant — platform.tenants là của Track A.
--
-- SECURITY DEFINER chạy bằng quyền của chủ hàm (role chạy Flyway), nên vượt được RLS. Bốn chốt giữ
-- cho lỗ này hẹp:
--   - Chỉ trả (tenant_id, document_id, status, attempt_count) — không nội dung, không tiêu đề,
--     không file_path. Biết một id của tenant khác không đọc được gì: mọi thao tác tiếp theo chạy
--     trong phiên đã gắn đúng tenant đó, dưới RLS như thường.
--   - Không nhận tham số nào lọt vào tên bảng hay SQL động — chỉ một khoảng thời gian và một trần.
--   - search_path ghim về pg_catalog, pg_temp: không ai chèn được hàm/bảng giả vào đường tìm tên
--     để chạy mã của mình bằng quyền chủ hàm.
--   - REVOKE khỏi PUBLIC, chỉ GRANT cho ai_app.
--
-- Hai loại tài liệu kẹt:
--   PROCESSING quá hạn nhịp tim         — tiến trình chết giữa chừng.
--   PENDING có attempt_count > 0 quá hạn — đã được trả về hàng đợi (lỗi tạm thời, hoặc bộ quét
--                                          vừa trả) rồi tiến trình chết trước khi nhận lại.
-- PENDING có attempt_count = 0 KHÔNG thuộc diện quét: đó là tài liệu chưa từng có sự kiện — hoặc
-- sự kiện còn trên đường, hoặc java-core đã rollback lượt tải (hợp đồng UC018 mục 4). Tự nạp nó là
-- nạp một tài liệu không được tính hạn mức.
--
-- ⚠️ Hàm chỉ vượt được RLS khi CHỦ HÀM có BYPASSRLS (hoặc là superuser). Trên CSDL dev và test,
-- crm_owner là superuser. Trên RDS, role chủ KHÔNG phải superuser thật và FORCE RLS áp lên cả chủ
-- bảng — khi đó hàm ném 42501 (ai.current_tenant() không có tenant), tức hỏng ồn ào chứ không trả
-- rỗng im lặng. [CẦN XÁC NHẬN] cấp BYPASSRLS cho role chạy Flyway trên RDS — Ngày 18.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE FUNCTION knowledge.tim_job_ket(p_qua_han interval, p_toi_da int DEFAULT 100)
    RETURNS TABLE (tenant_id uuid, document_id uuid, status varchar, attempt_count smallint)
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT d.tenant_id, d.id, d.status, d.attempt_count
      FROM knowledge.knowledge_documents d
     WHERE d.updated_at < now() - p_qua_han
       AND (d.status = 'PROCESSING' OR (d.status = 'PENDING' AND d.attempt_count > 0))
     ORDER BY d.updated_at
     LIMIT least(greatest(p_toi_da, 1), 500)
$$;

REVOKE ALL ON FUNCTION knowledge.tim_job_ket(interval, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.tim_job_ket(interval, int) TO ai_app;

COMMENT ON FUNCTION knowledge.tim_job_ket(interval, int) IS
    'SECURITY DEFINER — lỗ có chủ đích trong RLS cho bộ quét job kẹt (ADR-0024). Chỉ trả id + '
    'trạng thái; mọi thao tác sau đó chạy trong phiên đã gắn tenant, dưới RLS.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Không GRANT thêm cho knowledge_documents / knowledge_chunks: ba cột mới kế thừa quyền và
--    policy của bảng (V206, V207). ai_app đã có DELETE trên knowledge_chunks (V206) — cần để dọn
--    đoạn dở dang trước mỗi lượt thử lại.
-- ─────────────────────────────────────────────────────────────────────────────
