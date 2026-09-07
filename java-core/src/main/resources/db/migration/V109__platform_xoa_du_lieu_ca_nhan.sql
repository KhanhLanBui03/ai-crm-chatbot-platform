-- V109 — Yêu cầu xoá dữ liệu cá nhân. UC041, Nghị định 13/2023/NĐ-CP.
--
-- Đặt sau V105 vì tham chiếu engagement.contacts.
-- Đây là bảng làm UC041 phủ TRỌN thay vì phủ một phần: dữ liệu đích (ẩn danh hoá,
-- che tin nhắn) và vết kiểm toán đã có từ trước, nhưng quy trình yêu cầu → xem
-- trước → duyệt → thực thi thì cần trạng thái riêng.

CREATE TABLE platform.data_erasure_requests (
    id                        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                 uuid        NOT NULL REFERENCES platform.tenants (id),
    contact_id                uuid        NOT NULL,
    requested_by              varchar(20) NOT NULL
                              CHECK (requested_by IN ('CONTACT','STAFF')),
    legal_basis               text        NOT NULL,
    status                    varchar(30) NOT NULL DEFAULT 'PENDING'
                              CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETED',
                                                'PARTIALLY_FAILED')),
    items                     jsonb       NOT NULL DEFAULT '[]'::jsonb,
    identity_verified_by      uuid,
    identity_verified_at      timestamptz,
    external_systems_note     text,
    certificate_uri           text,
    requested_at              timestamptz NOT NULL DEFAULT now(),
    started_at                timestamptz,
    completed_at              timestamptz,
    created_at                timestamptz NOT NULL DEFAULT now(),
    updated_at                timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_erasure_contact FOREIGN KEY (contact_id, tenant_id)
        REFERENCES engagement.contacts (id, tenant_id),
    CONSTRAINT fk_erasure_verifier FOREIGN KEY (identity_verified_by, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    CONSTRAINT ck_erasure_items CHECK (jsonb_typeof(items) = 'array'),
    CONSTRAINT ck_erasure_verified
        CHECK ((identity_verified_by IS NULL) = (identity_verified_at IS NULL)),
    -- Không được thực thi khi chưa xác minh danh tính người yêu cầu.
    CONSTRAINT ck_erasure_gate
        CHECK (status = 'PENDING' OR identity_verified_at IS NOT NULL)
);

CREATE INDEX ix_erasure_tenant_status
    ON platform.data_erasure_requests (tenant_id, status, requested_at DESC);
CREATE INDEX ix_erasure_contact
    ON platform.data_erasure_requests (tenant_id, contact_id);

COMMENT ON COLUMN platform.data_erasure_requests.items IS
    'Mảng MucXoa: tiến độ theo từng bảng, mỗi mục có action DELETE | ANONYMIZE | KEEP_AGGREGATE. '
    'Dùng jsonb thay bảng con vì khi lỗi giữa chừng ta chỉ cần biết chỗ nào đã xong để chạy lại '
    'phần dở dang — không có truy vấn nào đọc từng mục độc lập.';
COMMENT ON COLUMN platform.data_erasure_requests.external_systems_note IS
    'Phạm vi xoá KHÔNG vươn tới hệ thống bên ngoài đã nhận dữ liệu qua MCP. Giới hạn này phải '
    'hiển thị cho người duyệt, không được im lặng bỏ qua.';
