package com.thesis.crm.engagement.entity;

import com.thesis.crm.common.enums.ConversationStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.DynamicUpdate;

/**
 * {@code engagement.conversations} — một cuộc hội thoại (V107, V130, V131).
 *
 * <p><b>Cột do trigger quản — chỉ đọc ở đây.</b> Mỗi tin nhắn mới, trigger
 * {@code trg_sync_conversation_counters} (V130) cộng {@code message_count}, đặt {@code last_message_at},
 * {@code first_response_at}, {@code first_agent_response_at}, {@code last_message_preview}. Nếu Entity
 * được phép ghi các cột này, một lần nạp → sửa trạng thái → lưu sẽ đè số cũ lên số trigger vừa cộng
 * (tin đến giữa lúc nạp và lúc lưu là mất). {@code unread_count} vẫn ghi được: hộp thư đặt về 0 khi
 * nhân viên đọc.
 *
 * <p>{@link DynamicUpdate}: câu {@code UPDATE} chỉ chứa cột thật sự đổi — hai luồng sửa hai cột khác
 * nhau (gán người phụ trách / đánh giá CSAT) không đè lên nhau.
 *
 * <p><b>Chưa map năm cột tóm tắt</b> ({@code summary}, {@code summarized_at}, {@code summary_data},
 * {@code summary_trigger}, {@code summary_model_version}) — UC026 thêm ở commit riêng. Năm cột phải ghi
 * cùng lúc (ràng buộc {@code ck_conv_summary_complete}), nên thêm đủ một lần.
 *
 * <p>Mọi truy vấn qua Entity này vẫn phải chạy trong transaction đã gọi
 * {@code TenantTransactionScope.apply()} — RLS lọc tenant ở tầng CSDL, Entity không tự lọc.
 */
@Entity
@DynamicUpdate
@Table(name = "conversations", schema = "engagement")
public class Conversation {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "channel_id", nullable = false, updatable = false)
    private UUID channelId;

    @Column(name = "channel_identity_id", nullable = false, updatable = false)
    private UUID channelIdentityId;

    @Column(name = "contact_id")
    private UUID contactId;

    @Column(length = 200)
    private String subject;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private ConversationStatus status = ConversationStatus.BOT_HANDLING;

    /** {@code LOW | NORMAL | HIGH | URGENT} — job quá hạn (UC014) nâng dần. */
    @Column(nullable = false, length = 20)
    private String priority = "NORMAL";

    /** Ràng buộc {@code ck_conv_assigned}: cùng có hoặc cùng trống với {@link #assignedAt}. */
    @Column(name = "assigned_user_id")
    private UUID assignedUserId;

    @Column(name = "assigned_at")
    private Instant assignedAt;

    /** Ràng buộc {@code ck_conv_handover}: cùng có hoặc cùng trống với {@link #handoverReason}. */
    @Column(name = "handover_at")
    private Instant handoverAt;

    /** Mã lý do chuyển giao — khớp {@code LyDoChuyenGiao} của hợp đồng. */
    @Column(name = "handover_reason", length = 30)
    private String handoverReason;

    @Column(name = "queued_at")
    private Instant queuedAt;

    @Column(name = "primary_intent", length = 50)
    private String primaryIntent;

    @Column(length = 100)
    private String topic;

    /** {@code POSITIVE | NEUTRAL | NEGATIVE}. */
    @Column(length = 20)
    private String sentiment;

    @Column(name = "message_count", nullable = false, insertable = false, updatable = false)
    private int messageCount;

    @Column(name = "unread_count", nullable = false)
    private int unreadCount;

    @Column(name = "first_response_at", insertable = false, updatable = false)
    private Instant firstResponseAt;

    @Column(name = "first_agent_response_at", insertable = false, updatable = false)
    private Instant firstAgentResponseAt;

    @Column(name = "last_message_at", insertable = false, updatable = false)
    private Instant lastMessageAt;

    @Column(name = "last_message_preview", length = 200, insertable = false, updatable = false)
    private String lastMessagePreview;

    @Column(name = "resolved_at")
    private Instant resolvedAt;

    @Column(name = "closed_reason", length = 50)
    private String closedReason;

    /** Điểm hài lòng 1–5 (UC027). */
    @Column(name = "csat_score")
    private Short csatScore;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    /** Trigger {@code trg_touch_updated_at} tự đặt mỗi lần UPDATE. */
    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt = Instant.now();

    protected Conversation() {
        // JPA yêu cầu constructor không tham số
    }

    public Conversation(UUID tenantId, UUID channelId, UUID channelIdentityId, UUID contactId) {
        this.tenantId = tenantId;
        this.channelId = channelId;
        this.channelIdentityId = channelIdentityId;
        this.contactId = contactId;
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getChannelId() { return channelId; }
    public UUID getChannelIdentityId() { return channelIdentityId; }
    public UUID getContactId() { return contactId; }
    public void setContactId(UUID contactId) { this.contactId = contactId; }
    public String getSubject() { return subject; }
    public void setSubject(String subject) { this.subject = subject; }
    public ConversationStatus getStatus() { return status; }
    public void setStatus(ConversationStatus status) { this.status = status; }
    public String getPriority() { return priority; }
    public void setPriority(String priority) { this.priority = priority; }
    public UUID getAssignedUserId() { return assignedUserId; }
    public Instant getAssignedAt() { return assignedAt; }
    public Instant getHandoverAt() { return handoverAt; }
    public String getHandoverReason() { return handoverReason; }
    public Instant getQueuedAt() { return queuedAt; }
    public void setQueuedAt(Instant queuedAt) { this.queuedAt = queuedAt; }
    public String getPrimaryIntent() { return primaryIntent; }
    public void setPrimaryIntent(String primaryIntent) { this.primaryIntent = primaryIntent; }
    public String getTopic() { return topic; }
    public void setTopic(String topic) { this.topic = topic; }
    public String getSentiment() { return sentiment; }
    public void setSentiment(String sentiment) { this.sentiment = sentiment; }
    public int getMessageCount() { return messageCount; }
    public int getUnreadCount() { return unreadCount; }
    public void setUnreadCount(int unreadCount) { this.unreadCount = unreadCount; }
    public Instant getFirstResponseAt() { return firstResponseAt; }
    public Instant getFirstAgentResponseAt() { return firstAgentResponseAt; }
    public Instant getLastMessageAt() { return lastMessageAt; }
    public String getLastMessagePreview() { return lastMessagePreview; }
    public Instant getResolvedAt() { return resolvedAt; }
    public void setResolvedAt(Instant resolvedAt) { this.resolvedAt = resolvedAt; }
    public String getClosedReason() { return closedReason; }
    public void setClosedReason(String closedReason) { this.closedReason = closedReason; }
    public Short getCsatScore() { return csatScore; }
    public void setCsatScore(Short csatScore) { this.csatScore = csatScore; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    /** Gán người phụ trách — đặt cặp cột cùng lúc để không vi phạm {@code ck_conv_assigned}. */
    public void assignTo(UUID userId, Instant at) {
        this.assignedUserId = userId;
        this.assignedAt = userId == null ? null : at;
    }

    /** Ghi chuyển giao — đặt cặp cột cùng lúc để không vi phạm {@code ck_conv_handover}. */
    public void markHandover(String reason, Instant at) {
        this.handoverReason = reason;
        this.handoverAt = reason == null ? null : at;
    }
}
