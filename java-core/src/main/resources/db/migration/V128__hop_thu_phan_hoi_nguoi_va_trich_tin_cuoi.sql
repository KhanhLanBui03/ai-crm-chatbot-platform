-- ═════════════════════════════════════════════════════════════════════════════
-- V128 — UC012/UC013: hộp thư hợp nhất và nhân viên trả lời
-- ═════════════════════════════════════════════════════════════════════════════
-- KHÔNG chừa số trống cho nhánh khác: Flyway mặc định từ chối migration số NHỎ HƠN số đã chạy
-- (validate lỗi trừ khi bật outOfOrder). Nhánh nào merge sau thì lấy số kế tiếp còn trống.
--
-- 1. first_agent_response_at — UC013 bước 9 đo "phản hồi đầu tiên của CON NGƯỜI". Cột cũ
--    first_response_at bị trigger đặt ngay khi BOT trả lời câu đầu, nên không dùng được cho chỉ số
--    này. Giữ cả hai: báo cáo cần cả "khách chờ bao lâu mới có ai trả lời" lẫn "chờ bao lâu mới
--    gặp người thật".
--
-- 2. last_message_preview — danh sách hộp thư là truy vấn nóng nhất hệ thống; hợp đồng
--    (HoiThoaiTomTat) yêu cầu lấy trích tin cuối từ cột tính sẵn, KHÔNG join sang messages.

ALTER TABLE engagement.conversations
    ADD COLUMN first_agent_response_at timestamptz,
    ADD COLUMN last_message_preview    varchar(200);

COMMENT ON COLUMN engagement.conversations.first_agent_response_at IS
    'Lần đầu một NHÂN VIÊN trả lời (sender_type = AGENT). Khác first_response_at (tính cả bot).';
COMMENT ON COLUMN engagement.conversations.last_message_preview IS
    'Trích 200 ký tự của tin cuối không phải ghi chú hệ thống — do trigger giữ đồng bộ.';

-- Định nghĩa lại hàm trigger của V107, thêm hai cột mới. Giữ nguyên mọi hành vi cũ.
CREATE OR REPLACE FUNCTION engagement.sync_conversation_counters() RETURNS trigger AS $$
BEGIN
    UPDATE engagement.conversations
       SET message_count   = message_count + 1,
           -- chỉ tin của khách mới làm hội thoại thành "chưa đọc"
           unread_count    = unread_count + CASE WHEN NEW.sender_type = 'CUSTOMER' THEN 1 ELSE 0 END,
           last_message_at = GREATEST(COALESCE(last_message_at, NEW.sent_at), NEW.sent_at),
           first_response_at = CASE
               WHEN first_response_at IS NULL AND NEW.sender_type IN ('BOT','AGENT')
               THEN NEW.sent_at ELSE first_response_at END,
           first_agent_response_at = CASE
               WHEN first_agent_response_at IS NULL AND NEW.sender_type = 'AGENT'
               THEN NEW.sent_at ELSE first_agent_response_at END,
           last_message_preview = CASE
               WHEN NEW.content_type <> 'SYSTEM_NOTE' THEN left(NEW.content, 200)
               ELSE last_message_preview END,
           updated_at      = now()
     WHERE id = NEW.conversation_id;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

-- Điền cho hội thoại đã có
UPDATE engagement.conversations c
   SET last_message_preview = sub.preview,
       first_agent_response_at = sub.first_agent
  FROM (
        SELECT conversation_id,
               (array_agg(left(content, 200) ORDER BY sent_at DESC)
                    FILTER (WHERE content_type <> 'SYSTEM_NOTE'))[1] AS preview,
               min(sent_at) FILTER (WHERE sender_type = 'AGENT')     AS first_agent
          FROM engagement.messages
         GROUP BY conversation_id
       ) sub
 WHERE sub.conversation_id = c.id;
