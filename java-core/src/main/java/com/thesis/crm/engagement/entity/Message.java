package com.thesis.crm.engagement.entity;

import com.thesis.crm.common.enums.SenderType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.DynamicUpdate;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * {@code engagement.messages} — một tin nhắn (V107, V126).
 *
 * <p>INSERT một tin kích hoạt trigger {@code trg_sync_conversation_counters} (V130): hội thoại tự cộng
 * số tin, số chưa đọc và cập nhật tin cuối — không tự cộng ở code.
 *
 * <p>{@code metadata} (V126) là object JSON — trích dẫn của câu trả lời AI, đánh giá 👍/👎…; ràng buộc
 * {@code ck_msg_metadata} chặn mảng hay giá trị trơn. {@code attachments} ngược lại phải là mảng
 * ({@code ck_msg_attachments}).
 *
 * <p>Ràng buộc {@code ck_msg_sender}: chỉ {@link SenderType#AGENT} có {@code sender_user_id} — constructor
 * ép điều đó thay vì để CSDL từ chối lúc ghi.
 */
@Entity
@DynamicUpdate
@Table(name = "messages", schema = "engagement")
public class Message {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "conversation_id", nullable = false, updatable = false)
    private UUID conversationId;

    @Enumerated(EnumType.STRING)
    @Column(name = "sender_type", nullable = false, length = 20, updatable = false)
    private SenderType senderType;

    @Column(name = "sender_user_id", updatable = false)
    private UUID senderUserId;

    /** {@code INBOUND} (khách gửi tới) | {@code OUTBOUND} (hệ thống/nhân viên gửi đi). */
    @Column(nullable = false, length = 10, updatable = false)
    private String direction;

    @Column(nullable = false)
    private String content;

    /** {@code TEXT | IMAGE | FILE | STICKER | LOCATION | SYSTEM_NOTE}. */
    @Column(name = "content_type", nullable = false, length = 20)
    private String contentType = "TEXT";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "attachments", nullable = false)
    private List<Map<String, Object>> attachments = new ArrayList<>();

    @Column(name = "external_message_id", length = 255)
    private String externalMessageId;

    /** {@code PENDING | SENT | DELIVERED | FAILED}. */
    @Column(name = "delivery_status", nullable = false, length = 20)
    private String deliveryStatus = "PENDING";

    @Column(name = "ai_interaction_id")
    private UUID aiInteractionId;

    /** Đã che dữ liệu cá nhân trong {@code content} (UC041) — không hoàn tác. */
    @Column(name = "is_redacted", nullable = false)
    private boolean redacted;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata", nullable = false)
    private Map<String, Object> metadata = new HashMap<>();

    @Column(name = "sent_at", nullable = false, updatable = false)
    private Instant sentAt = Instant.now();

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    /** Trigger {@code trg_touch_updated_at} tự đặt mỗi lần UPDATE. */
    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt = Instant.now();

    protected Message() {
        // JPA yêu cầu constructor không tham số
    }

    /**
     * @param senderUserId bắt buộc khi {@code senderType = AGENT}, phải {@code null} với loại còn lại
     */
    public Message(UUID tenantId, UUID conversationId, SenderType senderType, UUID senderUserId,
            String direction, String content) {
        if ((senderType == SenderType.AGENT) != (senderUserId != null)) {
            throw new IllegalArgumentException("Chỉ tin của nhân viên (AGENT) mới có senderUserId.");
        }
        this.tenantId = tenantId;
        this.conversationId = conversationId;
        this.senderType = senderType;
        this.senderUserId = senderUserId;
        this.direction = direction;
        this.content = content;
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getConversationId() { return conversationId; }
    public SenderType getSenderType() { return senderType; }
    public UUID getSenderUserId() { return senderUserId; }
    public String getDirection() { return direction; }
    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
    public String getContentType() { return contentType; }
    public void setContentType(String contentType) { this.contentType = contentType; }
    public List<Map<String, Object>> getAttachments() { return attachments; }
    public void setAttachments(List<Map<String, Object>> attachments) { this.attachments = attachments; }
    public String getExternalMessageId() { return externalMessageId; }
    public void setExternalMessageId(String externalMessageId) { this.externalMessageId = externalMessageId; }
    public String getDeliveryStatus() { return deliveryStatus; }
    public void setDeliveryStatus(String deliveryStatus) { this.deliveryStatus = deliveryStatus; }
    public UUID getAiInteractionId() { return aiInteractionId; }
    public void setAiInteractionId(UUID aiInteractionId) { this.aiInteractionId = aiInteractionId; }
    public boolean isRedacted() { return redacted; }
    public Map<String, Object> getMetadata() { return metadata; }
    public void setMetadata(Map<String, Object> metadata) { this.metadata = metadata; }
    public Instant getSentAt() { return sentAt; }
    public void setSentAt(Instant sentAt) { this.sentAt = sentAt; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    /** Che nội dung (UC041) — thay toàn bộ {@code content}, đánh dấu đã che. Một chiều. */
    public void redact(String replacement) {
        this.content = replacement;
        this.redacted = true;
    }
}
