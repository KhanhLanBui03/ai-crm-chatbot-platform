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
-- Java tính sẵn khi lưu (ContactSearchText): tên + thư + số điện thoại, bỏ dấu, viết thường.
-- Không dùng unaccent() trong migration: extension đó do scripts/init-db.sql cài, không do
-- Flyway quản — dựa vào nó là migration hỏng trên máy chưa chạy init-db.
-- Dữ liệu sẵn có được điền bằng translate() với CÙNG bảng ký tự mà Java dùng.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE engagement.contacts
    ADD COLUMN search_text text NOT NULL DEFAULT '';

UPDATE engagement.contacts
   SET search_text = btrim(translate(
           lower(concat_ws(' ', full_name, email, phone)),
           'àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ',
           'aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd'));

COMMENT ON COLUMN engagement.contacts.search_text IS
    'Tên + thư + số điện thoại, bỏ dấu, viết thường — Java (ContactSearchText) tính khi lưu. '
    'Tìm bằng LIKE; bảng nhỏ ở phạm vi đồ án nên chưa cần chỉ mục trigram.';
