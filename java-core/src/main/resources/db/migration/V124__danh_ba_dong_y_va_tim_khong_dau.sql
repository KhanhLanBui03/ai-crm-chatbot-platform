-- V124 — Danh bạ: cho phép trùng để gợi ý hợp nhất, đồng ý xử lý dữ liệu, tìm không dấu.
-- UC016 (danh sách · hồ sơ · tạo thủ công).
--
-- Ba thay đổi, cả ba để khớp hợp đồng docs/openapi/dashboard-api.yaml (/api/v1/contacts):

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Trùng số điện thoại / địa chỉ thư: CẢNH BÁO, không chặn.
--
-- Hợp đồng (LuuKhachHangRequest, TaoKhachHangResult) và giao diện SCR027 đều thiết kế
-- "trùng thì vẫn tạo, trả duplicateCandidates để gợi ý hợp nhất" — chặn cứng làm luồng hợp
-- nhất (SCR025) không chạy được, vì muốn hợp nhất thì hai hồ sơ phải cùng tồn tại. V105 lại
-- đặt UNIQUE nên POST trùng sẽ vỡ với lỗi CSDL. Đổi sang chỉ mục THƯỜNG — vẫn tra trùng nhanh.
-- ─────────────────────────────────────────────────────────────────────────────
DROP INDEX engagement.uq_contacts_email;
DROP INDEX engagement.uq_contacts_phone;

CREATE INDEX ix_contacts_email ON engagement.contacts (tenant_id, lower(email))
    WHERE email IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_contacts_phone ON engagement.contacts (tenant_id, phone)
    WHERE phone IS NOT NULL AND deleted_at IS NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Đồng ý xử lý dữ liệu cá nhân — Nghị định 13/2023/NĐ-CP.
--
-- consent_marketing (V105) là đồng ý NHẬN QUẢNG CÁO — nghĩa pháp lý khác, giữ nguyên.
-- Hợp đồng cần consentGranted · consentAt · consentSource: không có thời điểm và nguồn thì
-- không chứng minh được khách đã đồng ý khi nào, qua kênh nào.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE engagement.contacts
    ADD COLUMN consent_granted boolean     NOT NULL DEFAULT false,
    ADD COLUMN consent_at      timestamptz,
    ADD COLUMN consent_source  varchar(20)
        CHECK (consent_source IN ('WIDGET','ZALO','FACEBOOK','AGENT_MANUAL')),
    -- Đã đồng ý thì phải có thời điểm và nguồn; chưa đồng ý thì không được có.
    ADD CONSTRAINT ck_contacts_consent CHECK (
        consent_granted = (consent_at IS NOT NULL)
        AND consent_granted = (consent_source IS NOT NULL)
    );

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Tìm kiếm không phân biệt hoa thường và KHÔNG PHÂN BIỆT DẤU ('nguyen' ra 'Nguyễn').
--
-- Cột search_text = tên + thư + số điện thoại, bỏ dấu, viết thường — do TRIGGER tính, không do
-- Java: khách hàng được ghi từ nhiều nơi (UC016 tạo tay, UC011 tiếp nhận tin nhắn, script nhập
-- liệu…). Tính ở tầng ứng dụng thì mọi đường ghi khác để cột trống và khách đó KHÔNG BAO GIỜ tìm
-- ra được (lỗi phát hiện khi rà soát 06/10). Trigger là nguồn sự thật duy nhất.
--
-- Bỏ dấu bằng normalize(NFD) + xoá dấu kết hợp U+0300–U+036F: đúng với cả chữ dựng sẵn lẫn chữ
-- tách dấu (bàn phím macOS/iOS). Không dùng unaccent(): extension đó do scripts/init-db.sql cài,
-- không do Flyway quản. Phải khớp ContactNormalizer.foldAccents (Java) — phía tìm kiếm.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE engagement.contacts
    ADD COLUMN search_text text NOT NULL DEFAULT '';

CREATE FUNCTION engagement.fold_vi(s text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT lower(regexp_replace(
               normalize(replace(replace(coalesce(s, ''), 'đ', 'd'), 'Đ', 'D'), NFD),
               '[̀-ͯ]', '', 'g'))
$$;

CREATE FUNCTION engagement.contacts_fill_search_text() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.search_text := btrim(engagement.fold_vi(concat_ws(' ', NEW.full_name, NEW.email, NEW.phone)));
    RETURN NEW;
END $$;

CREATE TRIGGER trg_contacts_search_text
    BEFORE INSERT OR UPDATE OF full_name, email, phone ON engagement.contacts
    FOR EACH ROW EXECUTE FUNCTION engagement.contacts_fill_search_text();

-- Dữ liệu sẵn có
UPDATE engagement.contacts
   SET search_text = btrim(engagement.fold_vi(concat_ws(' ', full_name, email, phone)));

GRANT EXECUTE ON FUNCTION engagement.fold_vi(text) TO crm_app;

COMMENT ON COLUMN engagement.contacts.search_text IS
    'Tên + thư + số điện thoại, bỏ dấu, viết thường — trigger trg_contacts_search_text tính, '
    'ứng dụng KHÔNG ghi. Tìm bằng LIKE từng từ; bảng nhỏ ở phạm vi đồ án nên chưa cần chỉ mục trigram.';
