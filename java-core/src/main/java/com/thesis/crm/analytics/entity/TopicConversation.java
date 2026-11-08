package com.thesis.crm.analytics.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import java.io.Serializable;
import java.time.Instant;
import java.time.LocalDate;
import java.util.Objects;
import java.util.UUID;
import org.hibernate.annotations.DynamicUpdate;

/**
 * {@code analytics.topic_conversations} (V138) — UC038: một hội thoại đã chạm một chủ đề trong một ngày.
 *
 * <p>Báo cáo đếm theo HỘI THOẠI còn sự kiện đến theo LƯỢT, nên mỗi lượt cộng vào đúng một dòng: hội thoại
 * hỏi giá ba lượt vẫn là một hội thoại "hỏi giá", với {@code turnCount = 3}.
 *
 * <p>{@code dimension} tách hai lớp: {@code INTENT} (7 ý định router) và {@code CLUSTER} (cụm ngữ nghĩa).
 */
@Entity
@DynamicUpdate
@IdClass(TopicConversation.Key.class)
@Table(name = "topic_conversations", schema = "analytics")
public class TopicConversation {

    public static final String INTENT = "INTENT";
    public static final String CLUSTER = "CLUSTER";

    /** Khoá chính kép — JPA bắt buộc có constructor rỗng, {@code equals} và {@code hashCode}. */
    public static class Key implements Serializable {
        private UUID tenantId;
        private String dimension;
        private String topicKey;
        private LocalDate statDate;
        private UUID conversationId;

        protected Key() {
        }

        public Key(UUID tenantId, String dimension, String topicKey, LocalDate statDate, UUID conversationId) {
            this.tenantId = tenantId;
            this.dimension = dimension;
            this.topicKey = topicKey;
            this.statDate = statDate;
            this.conversationId = conversationId;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Key k && Objects.equals(tenantId, k.tenantId) && Objects.equals(dimension, k.dimension)
                    && Objects.equals(topicKey, k.topicKey) && Objects.equals(statDate, k.statDate)
                    && Objects.equals(conversationId, k.conversationId);
        }

        @Override
        public int hashCode() {
            return Objects.hash(tenantId, dimension, topicKey, statDate, conversationId);
        }
    }

    @Id
    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Id
    @Column(length = 10, nullable = false, updatable = false)
    private String dimension;

    @Id
    @Column(name = "topic_key", length = 100, nullable = false, updatable = false)
    private String topicKey;

    @Id
    @Column(name = "stat_date", nullable = false, updatable = false)
    private LocalDate statDate;

    @Id
    @Column(name = "conversation_id", nullable = false, updatable = false)
    private UUID conversationId;

    /** Chụp lại lúc ghi — đổi tên chủ đề về sau không làm số liệu cũ đổi theo. */
    @Column(name = "topic_label", length = 200, nullable = false)
    private String topicLabel;

    @Column(name = "turn_count", nullable = false)
    private int turnCount;

    @Column(name = "answered_count", nullable = false)
    private int answeredCount;

    @Column(name = "refusal_count", nullable = false)
    private int refusalCount;

    @Column(name = "handoff_count", nullable = false)
    private int handoffCount;

    @Column(name = "first_at", nullable = false, updatable = false)
    private Instant firstAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected TopicConversation() {
        // JPA yêu cầu constructor không tham số
    }

    public TopicConversation(Key k, String topicLabel, Instant luc) {
        this.tenantId = k.tenantId;
        this.dimension = k.dimension;
        this.topicKey = k.topicKey;
        this.statDate = k.statDate;
        this.conversationId = k.conversationId;
        this.topicLabel = topicLabel;
        this.firstAt = luc;
        this.updatedAt = luc;
    }

    /** Kết quả một lượt, đã phân loại ở {@code TopicMetricsService}. */
    public enum KetQua { TRA_LOI, CHUYEN_GIAO, TU_CHOI, KHAC }

    /** Cộng một lượt. {@code KHAC} (hỏi lại, lỗi hệ thống) chỉ tăng số lượt — không phải lỗ hổng tri thức. */
    public void cong(KetQua kq, Instant luc) {
        turnCount++;
        switch (kq) {
            case TRA_LOI -> answeredCount++;
            case CHUYEN_GIAO -> handoffCount++;
            case TU_CHOI -> refusalCount++;
            case KHAC -> { }
        }
        updatedAt = luc;
    }

    public UUID getTenantId() { return tenantId; }
    public String getDimension() { return dimension; }
    public String getTopicKey() { return topicKey; }
    public LocalDate getStatDate() { return statDate; }
    public UUID getConversationId() { return conversationId; }
    public String getTopicLabel() { return topicLabel; }
    public int getTurnCount() { return turnCount; }
    public int getAnsweredCount() { return answeredCount; }
    public int getRefusalCount() { return refusalCount; }
    public int getHandoffCount() { return handoffCount; }
}
