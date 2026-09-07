-- V209 — Bốn đại lượng bản đặc tả đòi mà lược đồ chưa có chỗ ghi.
-- UC018 · UC023 · UC028
--
-- Cả bốn đều lọt qua đợt rà soát trước vì chúng là CỘT, không phải bảng: đợt đó truy
-- vết ở mức bảng và dừng đúng lúc mọi bảng đều truy được về use case. Bốn cột, không
-- bảng mới, không cột nào thay thế được bằng trường suy ra.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. groundedness_score — điểm BÁM NGUỒN, không phải điểm truy hồi
--
-- UC023 hậu điều kiện: "Danh sách đoạn đã truy hồi, ĐIỂM BÁM NGUỒN, số token tiêu thụ,
-- độ trễ và chi phí quy đổi được ghi đầy đủ vào bản ghi tương tác." Bước 10 nhắc lại
-- cùng danh sách.
--
-- Vì sao retrieval_top_score KHÔNG dùng thay được — hai đại lượng đo hai thứ khác nhau,
-- và bản đặc tả tách chúng ở hai bước riêng:
--   bước 5   "đối chiếu ĐỘ LIÊN QUAN của tập đoạn cuối cùng với ngưỡng"  → retrieval_top_score
--   bước 8.1 "nếu kết quả XÁC MINH BÁM NGUỒN không đạt ngưỡng"           → cột này
-- Cái trước đo "tìm được đoạn giống câu hỏi". Cái sau đo "câu trả lời vừa sinh ra có
-- thật sự dựa vào đoạn đó không". Truy hồi tốt mà mô hình vẫn bịa là trường hợp có
-- thật, và là đúng trường hợp UC023 8.1 muốn bắt.
--
-- numeric(4,3) cùng khuôn với intent_confidence: 0.000–1.000, đủ phân giải để đặt
-- ngưỡng mà không lưu rác thập phân.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE ai.ai_interactions
    ADD COLUMN groundedness_score numeric(4,3)
        CHECK (groundedness_score >= 0 AND groundedness_score <= 1);

COMMENT ON COLUMN ai.ai_interactions.groundedness_score IS
    'UC023 bước 8 — điểm xác minh câu trả lời có bám vào đoạn đã truy hồi. KHÁC '
    'retrieval_top_score (bước 5, đo độ liên quan của đoạn với câu hỏi): truy hồi tốt mà mô '
    'hình vẫn bịa là trường hợp có thật. NULL ở các nhánh không truy hồi (SMALL_TALK, '
    'TOOL_CALL, SUMMARY, EXTRACTION). Nguồn của ThongKeHieuQuaAi.avgGroundedness (UC039).';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. is_cached — lượt trả lời lấy từ bộ nhớ đệm ngữ nghĩa
--
-- UC023 1.1-1.2 (luồng thay thế): "Nếu câu hỏi đã tồn tại trong bộ nhớ đệm ngữ nghĩa
-- và kho tri thức chưa thay đổi kể từ lần trả lời trước → trả lại câu trả lời từ bộ
-- nhớ đệm, ĐÁNH DẤU LƯỢT NÀY LÀ DÙNG ĐỆM và không tính chi phí gọi mô hình."
--
-- Là luồng thay thế, nhưng "đánh dấu" là mệnh lệnh tường minh và cái giá là một
-- boolean. Không suy ra được từ cost_vnd = 0: một lượt lỗi hoặc một lượt bị chặn cũng
-- có chi phí 0, mà ba thứ đó phải đọc khác nhau ở báo cáo UC039.
--
-- Nếu thiếu cột này thì mọi lượt dùng đệm kéo trung bình độ trễ và chi phí của UC039
-- xuống, và bảng hiệu quả AI mô tả một hệ thống nhanh hơn và rẻ hơn thực tế.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE ai.ai_interactions
    ADD COLUMN is_cached boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN ai.ai_interactions.is_cached IS
    'UC023 1.2 — câu trả lời lấy từ bộ nhớ đệm ngữ nghĩa, không gọi mô hình. Báo cáo UC039 phải '
    'tách nhóm này ra khi tính trung bình chi phí và độ trễ, nếu không thì số liệu đẹp hơn thực tế.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. guard_latency_ms — độ trễ của BƯỚC KIỂM DUYỆT, tách khỏi chặng gọi công cụ
--
-- Hai use case nói về hai độ trễ khác nhau, cùng trên một dòng nhật ký:
--   UC024 bước 9  "cập nhật bản ghi tương tác kèm ĐỘ TRỄ CỦA CHẶNG GỌI CÔNG CỤ"
--   UC028 bước 8  "ghi nhật ký lời gọi kèm kết quả kiểm duyệt, ĐỘ TRỄ CỦA BƯỚC KIỂM
--                  DUYỆT và định danh hội thoại liên quan"
--
-- V205 chỉ có một cột latency_ms, và nó đang mang nghĩa của UC024. Một lời gọi BLOCKED
-- không bao giờ chạy tới chặng gọi, nên latency_ms của nó hoặc NULL hoặc mang nghĩa
-- nhập nhằng — mà đúng những dòng BLOCKED mới là thứ UC028 cần đo. Gộp hai đại lượng
-- vào một cột là làm hỏng đúng phép đo mà use case an toàn đòi.
--
-- Đây cũng là con số trả lời được câu hội đồng dễ hỏi: "lớp kiểm duyệt của em tốn bao
-- nhiêu?" — đo được trên mọi lời gọi, kể cả lời gọi bị chặn.
--
-- Định danh hội thoại (cũng ở UC028 bước 8) KHÔNG cần cột: nối
-- ai_interaction_id → ai_interactions.conversation_id, cùng schema ai, không qua ranh
-- giới quyền nào.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE ai.ai_tool_calls
    ADD COLUMN guard_latency_ms int CHECK (guard_latency_ms >= 0);

COMMENT ON COLUMN ai.ai_tool_calls.guard_latency_ms IS
    'UC028 bước 8 — độ trễ của bước kiểm duyệt (danh sách trắng, đối chiếu schema_hash, kiểm '
    'đối số, hạn mức). Ghi cho MỌI lời gọi kể cả BLOCKED. Khác latency_ms, là độ trễ của chặng '
    'gọi công cụ ở UC024 bước 9 và chỉ có nghĩa khi decision = ALLOWED.';

COMMENT ON COLUMN ai.ai_tool_calls.latency_ms IS
    'UC024 bước 9 — độ trễ của chặng gọi máy chủ MCP. NULL khi lời gọi bị chặn trước lúc gọi; '
    'chi phí của lớp chặn nằm ở guard_latency_ms.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. description — siêu dữ liệu người dùng nhập lúc tải tài liệu
--
-- UC018 bước 3: "Chọn tệp, nhập tiêu đề VÀ MÔ TẢ NGẮN VỀ NỘI DUNG TÀI LIỆU."
-- UC018 bước 7: "Tạo bản ghi tài liệu ở trạng thái chờ xử lý KÈM SIÊU DỮ LIỆU DO
--                NGƯỜI DÙNG NHẬP."
--
-- Hợp đồng đã nhận trường này ở multipart của POST /documents và trả nó lại trong
-- TaiLieu, nhưng bảng không có cột — nên mô tả người dùng gõ bị mất ngay tại bước ghi.
--
-- Không nhét vào metadata jsonb của knowledge_chunks: đây là thuộc tính của TÀI LIỆU
-- do người nhập, không phải của đoạn do máy sinh.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE knowledge.knowledge_documents
    ADD COLUMN description text;

COMMENT ON COLUMN knowledge.knowledge_documents.description IS
    'UC018 bước 3 — mô tả ngắn do người tải lên nhập. Hiển thị ở SCR030 và dùng làm ngữ cảnh '
    'bổ sung khi xếp hạng lại kết quả truy hồi.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. tool_schema_cache — COMMENT V208 chưa cam kết đủ khoá mà hợp đồng cần
--
-- Cột là jsonb nên KHÔNG có thay đổi cấu trúc nào ở đây, chỉ sửa bản cam kết. Nhưng
-- COMMENT chính là hợp đồng của cột này — CSDL không cưỡng chế được từng trường bên
-- trong jsonb, nên nếu COMMENT thiếu khoá thì không có chỗ nào khác nói cho người viết
-- ai-service biết phải ghi gì.
--
-- Năm khoá bổ sung, đều lấy từ schema CongCu ở dashboard-api.yaml (SCR039):
--   input_schema           lược đồ tham số thô — dữ liệu KHÔNG đáng tin, hiển thị như văn bản
--   approved_schema_hash   giá trị quản trị viên đã duyệt; UC028 bước 3 so schema_hash với nó
--   auto_disabled_reason   UC021 7.2 tự tắt khi mã băm đổi — phải nói được vì sao tắt
--   approved_by            ai đã duyệt (uuid trỏ platform.users, không FK — liên làn)
--   last_seen_at           lần khám phá gần nhất còn thấy công cụ này
--
-- Và sửa một chỗ sai của V208: risk_level ghi là (READ|WRITE) trong khi enum MucRuiRo
-- của hợp đồng có ba giá trị. ai_tool_calls.risk_level ở V205 vốn đã CHECK đủ ba.
-- ─────────────────────────────────────────────────────────────────────────────
COMMENT ON COLUMN integration.mcp_servers.tool_schema_cache IS
    'Sổ đăng ký công cụ của UC021. Mảng các đối tượng, mỗi đối tượng bắt buộc có: '
    'name (text) · description (text) · input_schema (object, lược đồ tham số thô do máy chủ '
    'MCP cung cấp — DỮ LIỆU KHÔNG ĐÁNG TIN, đi vào lời nhắc nên là bề mặt tiêm chỉ thị) · '
    'schema_hash (text, SHA-256 của lược đồ tham số đã chuẩn hoá) · approved_schema_hash '
    '(text|null, giá trị quản trị viên đã duyệt) · enabled (bool, MẶC ĐỊNH false theo UC021 '
    'bước 7) · risk_level (READ|WRITE|DESTRUCTIVE) · requires_approval (bool) · '
    'auto_disabled_reason (SCHEMA_HASH_CHANGED|SERVER_DISCONNECTED|ADMIN_DISABLED|null, '
    'UC021 7.2) · approved_by (uuid|null, trỏ platform.users — không FK, liên làn) · '
    'approved_at (timestamp ISO-8601|null) · last_seen_at (timestamp ISO-8601). '
    'UC028 bước 3 so schema_hash hiện tại với approved_schema_hash; lệch thì chặn TOÀN BỘ công '
    'cụ của máy chủ đó. UC021 9.2: risk_level khác READ thì requires_approval BẮT BUỘC true và '
    'không được tắt — ràng buộc này cưỡng chế ở tầng ứng dụng, CSDL không kiểm được trong jsonb.';

-- Không GRANT, không RLS, không trigger: cả ba bảng đã có đủ từ V206 và V207, và
-- ADD COLUMN kế thừa quyền của bảng.
