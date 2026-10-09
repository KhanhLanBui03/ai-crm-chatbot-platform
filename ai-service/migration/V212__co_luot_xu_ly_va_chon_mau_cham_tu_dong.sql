-- V212 — Ba cờ của lượt xử lý cho tín hiệu chất lượng, và hàm chọn mẫu cho bộ chấm tự động.
-- UC025 · UC027 · UC039 · kế hoạch Ngày 10
--
-- Từ Ngày 10 ai-service ghi THẬT ai.ai_interactions mỗi lượt chat (trước đó chỉ ghi log). Ba tín
-- hiệu rẻ của UC027 (tỉ lệ suy giảm, tỉ lệ chuyển giao, tỉ lệ không gọi LLM) cần ba sự thật mà
-- các cột V204–V209 không suy ra được — chú thích từng cột nói vì sao.
--
-- Không sửa V201–V211: đã chạy trên CSDL dev, sửa là lệch checksum Flyway.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Ba cờ trên ai_interactions
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE ai.ai_interactions
    ADD COLUMN llm_called  boolean NOT NULL DEFAULT false,
    ADD COLUMN is_degraded boolean NOT NULL DEFAULT false,
    ADD COLUMN is_handoff  boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN ai.ai_interactions.llm_called IS
    'Lượt này có gửi yêu cầu tới nhà cung cấp LLM không — mẫu số của KPI "≥ 55% lượt không gọi '
    'LLM" (§1.6). Không suy ra được từ model_name hay prompt_tokens: lượt suy giảm vì mạch đã mở '
    'mang tên model mà không gọi, lượt quá hạn có gọi (có thể đã tính tiền) mà 0 token.';
COMMENT ON COLUMN ai.ai_interactions.is_degraded IS
    'LLM không phục vụ được, câu trả lời là trích nguyên văn đoạn liên quan nhất (UC023, Ngày 9). '
    'Vẫn is_answered = true nên phải tách riêng: gộp vào thì tỉ lệ trả lời và độ phủ trích dẫn '
    'đẹp hơn thực tế đúng vào lúc hệ thống đang hỏng.';
COMMENT ON COLUMN ai.ai_interactions.is_handoff IS
    'Lượt này trả handoff = true cho java-core. Không suy ra được từ branch: từ Ngày 10 nhánh RAG '
    'cũng chuyển giao khi câu hỏi cần dữ liệu nghiệp vụ (OUT_OF_SCOPE_DATA) hoặc khi từ chối lặp '
    'lại trong cùng hội thoại (UC025 luồng phụ 3.3).';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. ai.tim_luot_can_cham — chọn mẫu cho bộ chấm tự động, lỗ CÓ CHỦ ĐÍCH trong RLS
--
-- Cùng lý do và cùng bốn chốt với knowledge.tim_job_ket (V211, ADR-0024): bộ chấm chạy nền phải
-- thấy lượt của MỌI tenant, ai_app chịu RLS FORCE. Hàm chỉ trả (tenant_id, id, created_at) — không
-- câu hỏi, không câu trả lời. Mọi bước đọc nội dung và ghi đánh giá sau đó chạy trong phiên đã gắn
-- đúng tenant, dưới RLS như thường.
--
-- created_at để worker DỜI MỐC QUÉT đúng: lô đầy (đủ p_toi_da) thì mốc lần sau là created_at của
-- lượt cuối trong lô, không phải "bây giờ" — dời thẳng tới bây giờ là bỏ rơi vĩnh viễn phần ứng
-- viên vượt trần (lỗi bắt được ở test tích hợp Ngày 10).
--
-- CHỌN MẪU TẤT ĐỊNH THEO id, KHÔNG random(): md5 của id quyết định lượt nào thuộc mẫu, nên chạy
-- lại bao nhiêu lần cũng ra cùng một tập — đếm được "bao nhiêu % lượt đã được chấm" và không có
-- chuyện một lượt được chấm hai lần vì lần sau gieo trúng lại nó. random() thì mỗi lần quét chọn
-- một mẫu khác, tổng số lượt bị chấm trôi dần lên quá 5%.
--
-- Chỉ chấm lượt LLM thật sự sinh ra câu trả lời: lượt từ chối, mẫu câu, suy giảm không có gì để
-- một giám khảo LLM đánh giá — chúng đã có tín hiệu rẻ riêng (UC027 bước 6).
--
-- ⚠️ Như V211: hàm chỉ vượt được RLS khi CHỦ HÀM có BYPASSRLS. [CẦN XÁC NHẬN] trên RDS — Ngày 18.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE FUNCTION ai.tim_luot_can_cham(p_tu timestamptz, p_ty_le numeric, p_toi_da int DEFAULT 50)
    RETURNS TABLE (tenant_id uuid, interaction_id uuid, created_at timestamptz)
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT i.tenant_id, i.id, i.created_at
      FROM ai.ai_interactions i
     WHERE i.created_at >= p_tu
       AND i.branch = 'RAG'
       AND i.is_answered
       AND i.llm_called
       AND NOT i.is_degraded
       -- 8 chữ số hex đầu của md5(id) → số nguyên 0..2^32-1 → phần vạn. Khớp mau_cham() ở Python.
       AND ('x' || substr(md5(i.id::text), 1, 8))::bit(32)::bigint % 10000
           < least(greatest(p_ty_le, 0), 1) * 10000
       AND NOT EXISTS (
           SELECT 1 FROM ai.ai_feedback f
            WHERE f.ai_interaction_id = i.id AND f.rater_type = 'AUTO_EVAL'
       )
     ORDER BY i.created_at, i.id
     LIMIT least(greatest(p_toi_da, 1), 200)
$$;

REVOKE ALL ON FUNCTION ai.tim_luot_can_cham(timestamptz, numeric, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ai.tim_luot_can_cham(timestamptz, numeric, int) TO ai_app;

COMMENT ON FUNCTION ai.tim_luot_can_cham(timestamptz, numeric, int) IS
    'SECURITY DEFINER — chọn mẫu tất định (md5 của id) cho bộ chấm tự động UC027. Chỉ trả id; '
    'đọc nội dung và ghi ai_feedback chạy trong phiên đã gắn tenant, dưới RLS.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Không GRANT, không RLS mới: ba cột kế thừa quyền và policy của bảng (V206, V207).
--    ai_app đã có INSERT/UPDATE trên ai_feedback (V206) — đủ cho UPSERT đánh giá.
-- ─────────────────────────────────────────────────────────────────────────────
