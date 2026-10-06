-- V125 — Ghi chú và gắn thẻ. UC017 (SCR028), docs/openapi/dashboard-api.yaml.
-- Phụ thuộc V124 (engagement.fold_vi).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. contact_notes: ghi chú viết trong hội thoại nào, xoá mềm, thời điểm sửa NỘI DUNG.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE engagement.contact_notes
    ADD COLUMN conversation_id uuid,
    ADD COLUMN deleted_at      timestamptz,
    -- KHÔNG dùng updated_at làm editedAt: ghim/bỏ ghim cũng đổi updated_at (trigger
    -- touch_updated_at), nên ghi chú vừa ghim sẽ bị hiện "(đã sửa)". edited_at chỉ đổi khi
    -- nội dung đổi.
    ADD COLUMN edited_at       timestamptz,
    ADD CONSTRAINT fk_notes_conversation FOREIGN KEY (conversation_id, tenant_id)
        REFERENCES engagement.conversations (id, tenant_id);

-- Chỉ mục cũ phục vụ đúng thứ tự hiển thị (ghim trước, mới trước); thêm điều kiện chưa xoá.
DROP INDEX engagement.ix_notes_contact;
CREATE INDEX ix_notes_contact
    ON engagement.contact_notes (tenant_id, contact_id, is_pinned DESC, created_at DESC)
    WHERE deleted_at IS NULL;

COMMENT ON COLUMN engagement.contact_notes.edited_at IS
    'Lần sửa NỘI DUNG gần nhất (editedAt của hợp đồng). Khác updated_at — ghim cũng đổi updated_at.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. tags: trùng tên tính cả khi khác hoa thường LẪN khác dấu ('Khách quen' = 'khach quen').
-- Hợp đồng POST /tags: "so sánh trên lower(unaccent(name))" — dùng engagement.fold_vi (V124)
-- thay unaccent vì extension đó không do Flyway quản.
-- ─────────────────────────────────────────────────────────────────────────────
DROP INDEX engagement.uq_tags_tenant_name;
CREATE UNIQUE INDEX uq_tags_tenant_name ON engagement.tags (tenant_id, engagement.fold_vi(btrim(name)));

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. tags.usage_count do trigger đếm, không do ứng dụng: thẻ được gắn từ nhiều nơi (nhân viên,
-- tác tử AI — tagged_by NULL), đếm ở ứng dụng là lệch ngay khi có đường gắn thứ hai.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE FUNCTION engagement.contact_tags_count() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE engagement.tags SET usage_count = usage_count + 1
         WHERE id = NEW.tag_id AND tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE engagement.tags SET usage_count = greatest(usage_count - 1, 0)
         WHERE id = OLD.tag_id AND tenant_id = OLD.tenant_id;
    END IF;
    RETURN NULL;
END $$;

CREATE TRIGGER trg_contact_tags_count
    AFTER INSERT OR DELETE ON engagement.contact_tags
    FOR EACH ROW EXECUTE FUNCTION engagement.contact_tags_count();

-- Dữ liệu sẵn có
UPDATE engagement.tags t
   SET usage_count = (SELECT count(*) FROM engagement.contact_tags ct
                       WHERE ct.tag_id = t.id AND ct.tenant_id = t.tenant_id);
