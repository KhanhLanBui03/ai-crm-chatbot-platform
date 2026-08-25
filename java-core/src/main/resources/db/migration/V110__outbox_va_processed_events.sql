-- V110 — Hai bảng hạ tầng nhắn tin (ADR-0003).
--
-- outbox_events: service KHÔNG gọi KafkaTemplate.send() thẳng. Sự kiện ghi vào
-- đây trong CÙNG transaction nghiệp vụ, một job nền đọc và phát. Không có bước
-- này thì transaction thành công nhưng sự kiện mất, hoặc ngược lại.
--
-- processed_events: giao nhận ít nhất một lần nghĩa là CHẮC CHẮN sẽ nhận trùng,
-- không phải rủi ro. Consumer kiểm bảng này trước khi xử lý.

CREATE TABLE platform.outbox_events (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id      uuid        NOT NULL REFERENCES platform.tenants (id),
    aggregate_type varchar(50) NOT NULL,
    aggregate_id   uuid        NOT NULL,
    event_type     varchar(60) NOT NULL,
    topic          varchar(60) NOT NULL,
    payload        jsonb       NOT NULL,
    headers        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    published_at   timestamptz,
    attempt_count  smallint    NOT NULL DEFAULT 0,
    last_error     text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

-- Chỉ mục BỘ PHẬN trên các bản ghi chưa phát. Job nền quét mỗi 500ms; chỉ mục đầy
-- đủ sẽ phình theo toàn bộ lịch sử sự kiện trong khi vùng cần đọc luôn rất nhỏ.
CREATE INDEX ix_outbox_unpublished
    ON platform.outbox_events (created_at)
    WHERE published_at IS NULL;

COMMENT ON COLUMN platform.outbox_events.id IS
    'Chính là event_id mà docs/events/*.json khai kiểu integer.';

CREATE TABLE analytics.processed_events (
    consumer_group varchar(60) NOT NULL,
    event_id       bigint      NOT NULL,
    tenant_id      uuid        NOT NULL REFERENCES platform.tenants (id),
    processed_at   timestamptz NOT NULL DEFAULT now(),
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (consumer_group, event_id)
);

COMMENT ON TABLE analytics.processed_events IS
    'Khoá (consumer_group, event_id) là cơ chế chống xử lý trùng. Phải có TRƯỚC khi viết '
    'consumer đầu tiên, không phải thêm sau khi phát hiện dữ liệu nhân đôi.';
