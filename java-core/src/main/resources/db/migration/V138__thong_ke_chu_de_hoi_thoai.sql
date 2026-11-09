-- V138 — UC038 Thống kê chủ đề hội thoại: mô hình đọc "hội thoại × chủ đề × ngày".
--
-- Vì sao một dòng cho mỗi HỘI THOẠI chứ không chỉ bộ đếm theo ngày:
--   Màn SCR052 đếm theo hội thoại ("bao nhiêu hội thoại hỏi về giá, bao nhiêu trong đó bị từ chối"),
--   mà sự kiện ai.turn.completed đến theo LƯỢT. Một hội thoại hỏi giá ba lượt chỉ được tính một lần;
--   muốn biết "đã tính chưa" thì phải nhớ hội thoại nào đã vào chủ đề nào trong ngày. Bảng này chính
--   là trí nhớ đó, và báo cáo gộp nó lại lúc đọc (quy mô doanh nghiệp vừa và nhỏ: vài nghìn dòng/tháng).
--
-- Hai lớp chủ đề dùng chung bảng, tách bằng cột dimension:
--   INTENT  — 7 ý định router (UC022), cộng dồn theo từng sự kiện ai.turn.completed (phần 1)
--   CLUSTER — cụm ngữ nghĩa do công việc phân cụm hằng tuần đặt nhãn (phần 2)
--
-- topic_label CHỤP LẠI lúc ghi (hợp đồng ThongKeChuDe): đổi tên chủ đề về sau không làm số cũ đổi theo.
-- Nhãn do mô hình đặt là dữ liệu máy sinh trên nội dung khách — chỉ hiển thị, không làm khoá tra cứu.

CREATE TABLE analytics.topic_conversations (
    tenant_id        uuid          NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    stat_date        date          NOT NULL,
    dimension        varchar(10)   NOT NULL CHECK (dimension IN ('INTENT', 'CLUSTER')),
    topic_key        varchar(100)  NOT NULL,
    topic_label      varchar(200)  NOT NULL,
    conversation_id  uuid          NOT NULL,
    turn_count       int           NOT NULL DEFAULT 0 CHECK (turn_count >= 0),
    answered_count   int           NOT NULL DEFAULT 0 CHECK (answered_count >= 0),
    refusal_count    int           NOT NULL DEFAULT 0 CHECK (refusal_count >= 0),
    handoff_count    int           NOT NULL DEFAULT 0 CHECK (handoff_count >= 0),
    first_at         timestamptz   NOT NULL DEFAULT now(),
    updated_at       timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, dimension, topic_key, stat_date, conversation_id),
    -- Khoá ngoại kép (id, tenant_id) như V107: không thể gắn hội thoại của doanh nghiệp khác.
    -- Xoá hội thoại (UC041 xoá dữ liệu cá nhân) thì số liệu chủ đề của nó đi theo.
    FOREIGN KEY (conversation_id, tenant_id)
        REFERENCES engagement.conversations (id, tenant_id) ON DELETE CASCADE
);

-- Báo cáo luôn lọc theo doanh nghiệp + lớp + khoảng ngày
CREATE INDEX idx_topic_conversations_report
    ON analytics.topic_conversations (tenant_id, dimension, stat_date);
CREATE INDEX idx_topic_conversations_conversation
    ON analytics.topic_conversations (conversation_id);

COMMENT ON TABLE analytics.topic_conversations IS
    'UC038 — hội thoại × chủ đề × ngày. Lớp INTENT cộng từ ai.turn.completed; lớp CLUSTER từ công việc phân cụm hằng tuần.';
COMMENT ON COLUMN analytics.topic_conversations.refusal_count IS
    'Số lượt bị từ chối (is_answered = false, không phải chuyển giao). Hội thoại có ≥ 1 lượt từ chối thì tính là "bị từ chối" ở báo cáo.';

-- Quyền + RLS — khuôn chuẩn V112/V113 (V111 không với tới bảng tạo sau nó)
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.topic_conversations TO crm_app;

ALTER TABLE analytics.topic_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.topic_conversations FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON analytics.topic_conversations
    USING      (tenant_id = platform.current_tenant())
    WITH CHECK (tenant_id = platform.current_tenant());
