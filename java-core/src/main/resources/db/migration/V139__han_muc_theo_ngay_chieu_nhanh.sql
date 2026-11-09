-- V139 — UC006 bước 5–7: số liệu sử dụng theo ngày tách theo NHÁNH xử lý cần đếm HỘI THOẠI, không đếm lượt.
--
-- Đặc tả UC006 6.1: "một hội thoại đi qua nhiều nhánh, gộp lại sẽ nhân đôi số đếm" — nên mỗi nhánh đếm hội
-- thoại riêng, và không có lời gọi nào gộp hai chiều. Sự kiện ai.turn.completed đến theo LƯỢT; muốn biết
-- "hội thoại X hôm nay đã được đếm cho nhánh RAG chưa" thì phải nhớ cặp (hội thoại, nhánh, ngày). Bảng
-- analytics.topic_conversations (V138) đã nhớ đúng loại cặp đó cho ý định — thêm chiều thứ ba thay vì dựng
-- bảng thứ hai cùng hình dạng.
--
-- Chiều kênh KHÔNG cần ở đây: một hội thoại thuộc đúng một kênh, đếm thẳng từ engagement.conversations.

ALTER TABLE analytics.topic_conversations
    DROP CONSTRAINT topic_conversations_dimension_check;

ALTER TABLE analytics.topic_conversations
    ADD CONSTRAINT topic_conversations_dimension_check
        CHECK (dimension IN ('INTENT', 'CLUSTER', 'ROUTE'));

COMMENT ON COLUMN analytics.topic_conversations.dimension IS
    'INTENT — 7 ý định router (UC038) · CLUSTER — cụm ngữ nghĩa (UC038) · ROUTE — 7 nhánh xử lý (UC006, đếm '
    'hội thoại theo nhánh). Chỉ đọc MỘT chiều mỗi lần — một hội thoại có mặt ở nhiều dòng của cùng một chiều.';
