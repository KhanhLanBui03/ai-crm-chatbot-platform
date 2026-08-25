-- V208 — Cờ an toàn trên lượt xử lý, và cấu trúc bắt buộc cho sổ đăng ký công cụ.
-- UC021 · UC022 · UC024 · UC025 · UC028 · UC040
--
-- Cả hai thay đổi ở đây đều phục vụ hai use case an toàn cốt lõi (UC028 chặn lời gọi
-- vi phạm, UC040 xem nhật ký kiểm toán), và không cái nào cần bảng mới.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. safety_flag — chỗ ghi của "nhật ký an toàn"
--
-- Ba use case yêu cầu ai-service ghi nhận sự cố an toàn:
--   UC022 5.2  tin nhắn chứa chỉ thị ẩn nhằm thao túng tác tử
--   UC024 6.2  kết quả trả về từ máy chủ ngoài có dạng chỉ thị
--   UC025 3.4  câu hỏi dò tìm dữ liệu của doanh nghiệp khác
--
-- và UC040 bước 7-8 (LUỒNG CHÍNH) đòi xem chúng cùng một chỗ với các lời gọi công
-- cụ bị chặn.
--
-- Vì sao không ghi thẳng platform.audit_logs như java-core: ai_app KHÔNG có USAGE
-- trên schema của Track A (V206) — đó là chủ ý của ADR-0002, không phải thiếu sót.
-- Vì sao không thêm bảng ai.safety_events: cả ba tình huống đều phát sinh TRONG một
-- lượt xử lý đã có bản ghi, nên một cột trên chính lượt đó vừa đủ và không sinh thêm
-- một bảng chỉ-ghi-thêm thứ hai bên cạnh ai_tool_calls.
--
-- /safety-events của dashboard-api hợp nhất ba nguồn: ai_tool_calls.decision =
-- 'BLOCKED' · ai_interactions.safety_flag IS NOT NULL · audit_logs.severity cao.
-- ─────────────────────────────────────────────────────────────────────────────
-- Năm giá trị này phải khớp TỪNG CHỮ với enum LoaiSuKienAnToan ở dashboard-api.yaml,
-- trừ TOOL_CALL_BLOCKED — giá trị đó đến từ ai_tool_calls.decision, không phải từ đây.
-- PROMPT_INJECTION_DOCUMENT ứng với bề mặt T3 (tài liệu bị tiêm chỉ thị gián tiếp);
-- nó không xuất phát từ một use case mà từ docs/threat-model.md, và được giữ vì
-- UC040 bước 8 gom mọi cảnh báo an toàn về một chỗ.
ALTER TABLE ai.ai_interactions
    ADD COLUMN safety_flag varchar(40)
        CHECK (safety_flag IN ('PROMPT_INJECTION_INPUT',
                               'PROMPT_INJECTION_TOOL_RESULT',
                               'PROMPT_INJECTION_DOCUMENT',
                               'CROSS_TENANT_PROBE',
                               'INTERNAL_DATA_PROBE'));

-- Chỉ mục bộ phận: sự cố an toàn là ngoại lệ hiếm trong một bảng lớn, nên chỉ mục
-- đầy đủ gần như toàn NULL.
CREATE INDEX ix_interaction_safety
    ON ai.ai_interactions (tenant_id, safety_flag, created_at DESC)
    WHERE safety_flag IS NOT NULL;

COMMENT ON COLUMN ai.ai_interactions.safety_flag IS
    'Sự cố an toàn phát hiện trong lượt xử lý này. Đánh cờ KHÔNG dừng luồng: UC022 5.2 nói rõ '
    'phải xử lý nội dung như dữ liệu rồi ĐỊNH TUYẾN BÌNH THƯỜNG, vì dừng lại là dạy người tấn '
    'công biết chính xác câu nào bị phát hiện.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. tool_schema_cache — sổ đăng ký công cụ, có cấu trúc cam kết
--
-- UC021 hậu điều kiện: "Danh sách công cụ được khám phá và lưu vào sổ đăng ký KÈM
-- MÃ BĂM LƯỢC ĐỒ. Chỉ những công cụ được BẬT TƯỜNG MINH mới khả dụng cho tác tử AI."
-- UC021 bước 7: lưu ở trạng thái TẮT theo mặc định.
-- UC021 7.2: mã băm đổi so với lần khám phá trước thì tự động tắt công cụ đó.
-- UC028 bước 3: đối chiếu mã băm hiện tại với "giá trị đã được quản trị viên duyệt
--               trong sổ đăng ký" — bước then chốt của toàn bộ use case.
--
-- Cột đã tồn tại từ V205 nhưng không có cấu trúc quy định, nên không nơi nào giữ
-- được schema_hash, requires_approval và risk_level của TỪNG công cụ. Không tách
-- thành bảng integration.tool_registry vì công cụ không có vòng đời độc lập với máy
-- chủ: ngắt máy chủ là toàn bộ công cụ của nó mất hiệu lực (UC021 1a-2a).
--
-- Đánh đổi thật, ghi ra để khỏi tranh cãi sau: jsonb không cho CSDL cưỡng chế từng
-- trường, việc đó rơi về tầng ứng dụng. Đổi lại không phải nối bảng ở đường nóng
-- của UC028, là đường chạy trước MỌI lời gọi công cụ.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE integration.mcp_servers
    ALTER COLUMN tool_schema_cache SET DEFAULT '[]'::jsonb,
    ADD CONSTRAINT ck_tool_cache_array
        CHECK (tool_schema_cache IS NULL OR jsonb_typeof(tool_schema_cache) = 'array');

UPDATE integration.mcp_servers
   SET tool_schema_cache = '[]'::jsonb
 WHERE tool_schema_cache IS NULL;

COMMENT ON COLUMN integration.mcp_servers.tool_schema_cache IS
    'Sổ đăng ký công cụ của UC021. Mảng các đối tượng, mỗi đối tượng bắt buộc có: '
    'name (text) · description (text) · schema_hash (text, SHA-256 của lược đồ tham số đã '
    'chuẩn hoá) · enabled (bool, MẶC ĐỊNH false theo UC021 bước 7) · risk_level '
    '(READ|WRITE) · requires_approval (bool) · approved_at (timestamp ISO-8601). '
    'UC028 bước 3 so schema_hash hiện tại với giá trị ở đây; lệch thì chặn toàn bộ công cụ '
    'của máy chủ đó. UC021 9.2: risk_level = WRITE thì requires_approval BẮT BUỘC true và '
    'không được tắt — ràng buộc này cưỡng chế ở tầng ứng dụng, CSDL không kiểm được trong jsonb.';

COMMENT ON COLUMN integration.mcp_servers.allowed_tools IS
    'Danh sách trắng tên công cụ, giữ song song với tool_schema_cache[].enabled để truy vấn '
    '"công cụ nào đang bật" không phải mở jsonb. Nguồn sự thật khi hai bên lệch là '
    'tool_schema_cache — allowed_tools chỉ là hình chiếu.';
