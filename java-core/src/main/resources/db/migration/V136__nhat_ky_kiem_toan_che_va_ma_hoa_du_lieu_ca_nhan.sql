-- UC040 — Nhật ký kiểm toán: email người làm chụp lại lúc ghi, và dữ liệu cá nhân "che khi ghi, xem đầy đủ
-- được khi có lý do".
--
-- Đặc tả UC040 đòi hai điều tưởng như ngược nhau: (1) dữ liệu cá nhân che TRƯỚC khi ghi — không phải che
-- lúc hiển thị, vì khi đó dữ liệu thật vẫn nằm trong bảng và ai đọc được bảng là thấy; (2) quản trị viên
-- được "xem đầy đủ" khi nêu lý do. Cách gỡ: before_data/after_data chỉ chứa BẢN ĐÃ CHE; bản gốc mã hoá
-- AES-GCM ở tầng ứng dụng rồi mới ghi vào pii_encrypted. Đọc trộm bảng (kể cả bằng tài khoản chủ bảng)
-- chỉ thấy bản che và một khối byte vô nghĩa; giải mã cần khoá nằm ngoài CSDL (biến môi trường).
--
-- pii_key_id cho phép xoay khoá: dòng cũ vẫn giải mã được bằng khoá cũ khi khoá mới đã dùng cho dòng mới.

ALTER TABLE platform.audit_logs
    -- Chụp lúc ghi: người dùng bị xoá sau đó thì dòng nhật ký vẫn đọc được "ai đã làm".
    ADD COLUMN actor_email            varchar(255),
    ADD COLUMN contains_personal_data boolean NOT NULL DEFAULT false,
    ADD COLUMN pii_encrypted          bytea,
    ADD COLUMN pii_key_id             varchar(64),
    -- Lý do của chính hành động — bắt buộc với "xem đầy đủ" (UC040 luồng 6.2).
    ADD COLUMN reason                 text,
    ADD CONSTRAINT ck_audit_pii CHECK (
        pii_encrypted IS NULL OR (pii_key_id IS NOT NULL AND contains_personal_data)
    );

-- Điền email cho các dòng đã có. updated_at "bằng created_at, không bao giờ đổi" (V104) — tắt trigger chạm
-- updated_at trong lúc điền để không làm sai cột đó trên toàn bộ dòng cũ.
ALTER TABLE platform.audit_logs DISABLE TRIGGER trg_touch_updated_at;
UPDATE platform.audit_logs a
   SET actor_email = u.email
  FROM platform.users u
 WHERE u.id = a.actor_user_id AND a.actor_email IS NULL;
ALTER TABLE platform.audit_logs ENABLE TRIGGER trg_touch_updated_at;

-- Màn nhật ký lọc theo mức nghiêm trọng và theo người làm, luôn kèm tenant và mới nhất trước.
CREATE INDEX ix_audit_tenant_severity ON platform.audit_logs (tenant_id, severity, created_at DESC);
CREATE INDEX ix_audit_tenant_actor    ON platform.audit_logs (tenant_id, actor_user_id, created_at DESC);

COMMENT ON COLUMN platform.audit_logs.pii_encrypted IS
    'Bản gốc phần trước/sau, mã hoá AES-GCM ở ứng dụng (khoá AUDIT_PII_KEY). before_data/after_data chỉ chứa bản đã che.';
COMMENT ON COLUMN platform.audit_logs.actor_email IS
    'Chụp lại lúc ghi — vẫn đọc được sau khi người dùng bị xoá.';
