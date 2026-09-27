package com.thesis.crm.platform.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * Một sự kiện chờ phát — {@code platform.outbox_events} (V110, ADR-0003).
 *
 * <p>Ghi trong CÙNG transaction với thay đổi nghiệp vụ; job nền đọc bảng này và phát lên Kafka.
 * Bảng KHÔNG bật RLS (V112 mục 4) — job phát không có ngữ cảnh tenant và phải thấy mọi dòng —
 * nên không bao giờ đọc bảng này theo yêu cầu của người dùng.
 *
 * <p>{@code id} là {@code event_id} của vỏ sự kiện ({@code docs/events/*.json}) — consumer chống
 * trùng theo nó ở {@code analytics.processed_events}.
 */
@Entity
@Table(name = "outbox_events", schema = "platform")
public class OutboxEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    /** Cũng là khoá phân vùng Kafka — thứ tự sự kiện giữ trong phạm vi một tenant. */
    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "aggregate_type", nullable = false, length = 50, updatable = false)
    private String aggregateType;

    @Column(name = "aggregate_id", nullable = false, updatable = false)
    private UUID aggregateId;

    @Column(name = "event_type", nullable = false, length = 60, updatable = false)
    private String eventType;

    @Column(name = "topic", nullable = false, length = 60, updatable = false)
    private String topic;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "payload", nullable = false, updatable = false)
    private Map<String, Object> payload;

    /** Header Kafka — Trace ID đi ở đây, không ở payload (docs/events/README.md, quy ước 3). */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "headers", nullable = false, updatable = false)
    private Map<String, Object> headers;

    @Column(name = "published_at")
    private Instant publishedAt;

    @Column(name = "attempt_count", nullable = false)
    private short attemptCount;

    @Column(name = "last_error")
    private String lastError;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected OutboxEvent() {
        // JPA yêu cầu constructor không tham số
    }

    public OutboxEvent(UUID tenantId, String aggregateType, UUID aggregateId, String eventType,
            String topic, Map<String, Object> payload, Map<String, Object> headers) {
        Instant now = Instant.now();
        this.tenantId = tenantId;
        this.aggregateType = aggregateType;
        this.aggregateId = aggregateId;
        this.eventType = eventType;
        this.topic = topic;
        this.payload = payload;
        this.headers = headers;
        this.attemptCount = 0;
        this.createdAt = now;
        this.updatedAt = now;
    }

    /** Kafka đã xác nhận (acks=all). Từ đây job phát không bao giờ chạm lại dòng này. */
    public void markPublished(Instant at) {
        this.publishedAt = at;
        this.updatedAt = at;
    }

    /**
     * Lần phát này hỏng. {@code updated_at} là mốc để tính lần thử lại kế tiếp (lùi dần), nên
     * cập nhật nó ở đây thay vì trông vào trigger — trigger chỉ chạy lúc flush, còn bộ đếm lùi
     * cần mốc ngay trong vòng lặp hiện tại.
     */
    public void markFailed(String error, Instant at) {
        if (attemptCount < Short.MAX_VALUE) {
            attemptCount++;
        }
        this.lastError = error.length() > 1000 ? error.substring(0, 1000) : error;
        this.updatedAt = at;
    }

    public Long getId() {
        return id;
    }

    public UUID getTenantId() {
        return tenantId;
    }

    public String getAggregateType() {
        return aggregateType;
    }

    public UUID getAggregateId() {
        return aggregateId;
    }

    public String getEventType() {
        return eventType;
    }

    public String getTopic() {
        return topic;
    }

    public Map<String, Object> getPayload() {
        return payload;
    }

    public Map<String, Object> getHeaders() {
        return headers;
    }

    public Instant getPublishedAt() {
        return publishedAt;
    }

    public short getAttemptCount() {
        return attemptCount;
    }

    public String getLastError() {
        return lastError;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
