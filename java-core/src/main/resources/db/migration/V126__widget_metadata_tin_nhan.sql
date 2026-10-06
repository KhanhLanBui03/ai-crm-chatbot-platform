-- ═════════════════════════════════════════════════════════════════════════════
-- V126 — UC010: lưu căn cứ của câu trả lời AI cùng tin nhắn
-- ═════════════════════════════════════════════════════════════════════════════
-- UC010 bước 7 "hiển thị câu trả lời kèm nguồn tham chiếu". Không lưu thì khách tải lại trang
-- là mất nguồn trích dẫn, và nhân viên ở hộp thư (UC012) không thấy AI đã dựa vào tài liệu nào.
--
-- jsonb thay vì bảng riêng: trích dẫn không bao giờ được truy vấn độc lập với tin nhắn cha
-- (cùng lý do với cột attachments ở V107).

ALTER TABLE engagement.messages
    ADD COLUMN metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE engagement.messages
    ADD CONSTRAINT ck_msg_metadata CHECK (jsonb_typeof(metadata) = 'object');

COMMENT ON COLUMN engagement.messages.metadata IS
    'Tin BOT: {route, refused, citations:[{documentId, title, snippet}]}. Không chứa dữ liệu cá nhân.';
