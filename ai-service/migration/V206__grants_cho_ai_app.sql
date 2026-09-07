-- V206 — Quyền của tài khoản runtime Track B.
--
-- ADR-0001: ai-service chạy bằng ai_app, không bao giờ bằng crm_owner.

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA knowledge, ai, integration TO ai_app;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai TO ai_app;

-- Nhật ký gọi công cụ CHỈ GHI THÊM, trừ một ngoại lệ: lời gọi NEEDS_APPROVAL phải
-- cập nhật được approval_status khi người duyệt bấm đồng ý. Nên giữ UPDATE nhưng
-- thu hồi DELETE — không có đường nào xoá bằng chứng.
REVOKE DELETE ON ai.ai_tool_calls FROM ai_app;

-- ai_app KHÔNG có quyền gì trên schema của Track A. Không cần GRANT USAGE, và
-- việc thiếu nó là lớp chặn cuối nếu ai đó lỡ viết truy vấn nối thẳng (ADR-0002).
