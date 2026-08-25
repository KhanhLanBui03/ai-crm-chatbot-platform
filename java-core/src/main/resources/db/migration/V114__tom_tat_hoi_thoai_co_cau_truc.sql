-- V114 — Tóm tắt hội thoại có cấu trúc, kèm phiên bản mô hình đã sinh ra nó.
-- UC026
--
-- Ba cột, không bảng mới. ERD mục 11 đã bác bảng conversation_summaries và bác đúng:
-- thứ giao diện cần là bản tóm tắt MỚI NHẤT, còn các bản cũ vẫn nằm ở
-- ai.ai_interactions với branch = 'SUMMARY'.
--
-- Vì sao V107 chưa đủ: nó có summary text + summarized_at, tức đúng hai trong bốn thứ
-- UC026 đòi. Xem mục 1 và mục 2 bên dưới.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. summary_data — bốn phần có tên, không phải một đoạn văn
--
-- UC026 bước 3 (LUỒNG CHÍNH): "gọi mô hình ngôn ngữ sinh tóm tắt CÓ CẤU TRÚC gồm
-- nhu cầu chính, thông tin khách hàng đã cung cấp, vấn đề chưa được giải quyết và
-- bước tiếp theo được đề xuất."
--
-- Một cột text ép bốn phần có tên thành một đoạn văn, rồi buộc giao diện tách ngược
-- ra bốn khối bằng cách dò chuỗi. Hợp đồng TomTatHoiThoai ở dashboard-api.yaml khai
-- đúng bốn trường rời, và mô tả của chính nó nói "Bốn phần có cấu trúc, không phải
-- một đoạn văn tự do".
--
-- jsonb chứ không phải bốn cột varchar: bốn phần này luôn được đọc và ghi TRỌN GÓI
-- (sinh cùng một lượt gọi mô hình, hiển thị cùng một khối giao diện), không truy vấn
-- nào lọc theo riêng một phần. Cùng lập luận đã dùng cho data_erasure_requests.items.
--
-- summary text GIỮ NGUYÊN: nó là bản phẳng để hiển thị gọn ở danh sách hộp thư và để
-- tìm kiếm toàn văn — hai chỗ không cần tới cấu trúc.
-- ─────────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. summary_model_version — hậu điều kiện đòi tường minh, và không đọc nhờ được
--
-- UC026 bước 4 + hậu điều kiện: "Lưu bản tóm tắt gắn với hội thoại KÈM THỜI ĐIỂM SINH
-- VÀ PHIÊN BẢN MÔ HÌNH ĐÃ SỬ DỤNG."
--
-- Giá trị đó có sẵn ở ai.ai_interactions.model_version, nhưng KHÔNG đọc nhờ được:
-- /conversations/{id}/context do java-core phục vụ, và crm_app không có USAGE trên
-- schema ai (V111). Nối bảng qua ranh giới đó là đúng cái ADR-0002 đóng lại.
--
-- Nên đây là ảnh chụp có chủ ý, cùng loại với usage_records.quota_value: nó là dữ kiện
-- của LẦN SINH ĐÓ, không phải thuộc tính của mô hình đang chạy hôm nay. Đổi mô hình
-- rồi đọc qua tham chiếu thì mọi bản tóm tắt cũ tự khai sai phiên bản.
--
-- ai-service ghi giá trị này qua PATCH /internal/conversations/{id}/summary
-- (docs/openapi/java-core-to-ai-service.yaml), không ghi thẳng CSDL.
-- ─────────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. summary_trigger — bốn sự kiện kích hoạt của UC026 bước 1
--
-- "Nhận sự kiện kích hoạt: chuyển giao nhân viên, kết thúc hội thoại, hoặc đạt ngưỡng
-- số lượt." Cộng MANUAL cho nhân viên tự bấm tóm tắt lại.
--
-- Giữ lý do kích hoạt vì nó đổi cách đọc bản tóm tắt: bản sinh lúc TURN_THRESHOLD là
-- ảnh chụp giữa chừng, bản sinh lúc CLOSING mới là bản tổng kết.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE engagement.conversations
    ADD COLUMN summary_data          jsonb,
    ADD COLUMN summary_trigger       varchar(20)
        CHECK (summary_trigger IN ('HANDOFF','CLOSING','TURN_THRESHOLD','MANUAL')),
    ADD COLUMN summary_model_version varchar(50),

    -- jsonb là kiểu vô hướng với PostgreSQL, nên không có gì ngăn ai đó ghi một mảng
    -- hay một chuỗi vào đây. Cùng khuôn với ck_tool_cache_array của V208.
    ADD CONSTRAINT ck_conv_summary_object
        CHECK (summary_data IS NULL OR jsonb_typeof(summary_data) = 'object'),

    -- Hậu điều kiện UC026 là MỘT mệnh đề: tóm tắt + thời điểm + phiên bản mô hình đi
    -- cùng nhau. Cưỡng chế bằng CHECK chứ không bằng quy ước, cùng khuôn với
    -- ck_conv_assigned và ck_conv_handover ở V107 — nếu không thì một bản tóm tắt
    -- thiếu phiên bản mô hình vẫn ghi được, và hậu điều kiện gãy mà không ai biết.
    ADD CONSTRAINT ck_conv_summary_complete CHECK (
        (summarized_at IS NULL AND summary_data IS NULL
             AND summary_trigger IS NULL AND summary_model_version IS NULL)
        OR
        (summarized_at IS NOT NULL AND summary_data IS NOT NULL
             AND summary_trigger IS NOT NULL AND summary_model_version IS NOT NULL)
    );

COMMENT ON COLUMN engagement.conversations.summary_data IS
    'UC026 bước 3 — bốn phần có tên: {"mainNeed":…, "providedInfo":…, "unresolvedIssues":…, '
    '"nextSteps":…}. Khoá khớp từng chữ với schema TomTatHoiThoai ở dashboard-api.yaml. '
    'Đọc/ghi trọn gói, không truy vấn nào lọc theo riêng một phần.';

COMMENT ON COLUMN engagement.conversations.summary_model_version IS
    'Ảnh chụp phiên bản mô hình đã sinh bản tóm tắt này (UC026 hậu điều kiện). KHÔNG đọc qua '
    'ai.ai_interactions.model_version: crm_app không có USAGE trên schema ai (V111, ADR-0002), '
    'và bản tóm tắt cũ phải giữ đúng phiên bản của nó sau khi đổi mô hình.';

COMMENT ON COLUMN engagement.conversations.summary_trigger IS
    'Sự kiện kích hoạt của UC026 bước 1. TURN_THRESHOLD là ảnh chụp giữa chừng, CLOSING là bản '
    'tổng kết — nhân viên đọc hai loại này khác nhau.';

COMMENT ON COLUMN engagement.conversations.summary IS
    'Bản phẳng của summary_data, dùng cho dòng tóm lược ở danh sách hộp thư và tìm kiếm toàn văn. '
    'Nguồn sự thật là summary_data.';

-- Không cần GRANT: ALTER TABLE ... ADD COLUMN kế thừa quyền của bảng, khác với CREATE
-- TABLE ở V113 (V111 dùng GRANT ... ON ALL TABLES, chỉ áp cho bảng đang tồn tại).
-- Không cần đụng RLS hay trigger updated_at: cả hai đã gắn trên conversations từ V112.
