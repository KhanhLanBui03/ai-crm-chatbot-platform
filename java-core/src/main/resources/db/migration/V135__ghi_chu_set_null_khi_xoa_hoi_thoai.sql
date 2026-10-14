-- Ghi chú gắn hội thoại: xoá hội thoại thì GIỮ ghi chú, chỉ gỡ liên kết.
--
-- V125 thêm khoá ngoại fk_notes_conversation KHÔNG có ON DELETE (mặc định NO ACTION) — xoá một hội
-- thoại mà có ghi chú trỏ tới là CSDL từ chối. Hệ quả: yêu cầu xoá dữ liệu cá nhân (UC041) không xoá
-- được hội thoại nào nhân viên từng ghi chú. Đây là khoá ngoại cuối cùng còn chặn việc xoá hội thoại
-- (messages, handoff_events: CASCADE; leads, activities: SET NULL — V132, V134).
--
-- Vì sao SET NULL chứ không CASCADE: ghi chú thuộc về KHÁCH HÀNG (contact_id), hội thoại chỉ là ngữ
-- cảnh lúc ghi. Xoá ghi chú theo hội thoại là mất ghi chú nghiệp vụ của nhân viên. Nội dung ghi chú có
-- chứa dữ liệu cá nhân hay không là việc của luồng xoá UC041, không phải của khoá ngoại.
--
-- Ghi đích danh cột (Postgres 15+): "SET NULL" trần đặt NULL cho CẢ HAI cột của khoá kép, kể cả
-- tenant_id NOT NULL — đúng lỗi đã sửa ở V132.
ALTER TABLE engagement.contact_notes
    DROP CONSTRAINT fk_notes_conversation,
    ADD CONSTRAINT fk_notes_conversation FOREIGN KEY (conversation_id, tenant_id)
        REFERENCES engagement.conversations (id, tenant_id) ON DELETE SET NULL (conversation_id);
