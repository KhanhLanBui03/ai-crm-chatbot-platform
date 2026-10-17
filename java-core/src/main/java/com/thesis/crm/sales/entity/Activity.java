package com.thesis.crm.sales.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.DynamicUpdate;

/**
 * {@code sales.activities} — cuộc gọi, gặp mặt, báo giá… kèm lời nhắc (UC035; V108, V134).
 *
 * <p>Ràng buộc: gắn tối đa MỘT trong lead/deal ({@code ck_act_toi_da_mot_dich});
 * {@code remind_status = 'NONE'} khi và chỉ khi {@code remind_at} trống — dùng {@link #setReminder}
 * để đặt các cột nhắc cùng lúc.
 */
@Entity
@DynamicUpdate
@Table(name = "activities", schema = "sales")
public class Activity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "contact_id", nullable = false, updatable = false)
    private UUID contactId;

    @Column(name = "lead_id")
    private UUID leadId;

    @Column(name = "deal_id")
    private UUID dealId;

    @Column(name = "conversation_id")
    private UUID conversationId;

    /** {@code CALL | MEETING | QUOTE | EMAIL | NOTE}. */
    @Column(nullable = false, length = 30, updatable = false)
    private String type;

    @Column(length = 200)
    private String subject;

    private String content;

    /** {@code DONE | NO_ANSWER | REFUSED | NOT_INTERESTED | RESCHEDULED}. */
    @Column(length = 30)
    private String outcome;

    /** {@code MANUAL | AUTO}. */
    @Column(nullable = false, length = 20, updatable = false)
    private String source = "MANUAL";

    @Column(name = "performed_by", nullable = false, updatable = false)
    private UUID performedBy;

    @Column(name = "performed_at")
    private Instant performedAt;

    @Column(name = "remind_at")
    private Instant remindAt;

    @Column(name = "remind_user_id")
    private UUID remindUserId;

    /** {@code NONE | PENDING | SENT | DONE | CANCELED}. */
    @Column(name = "remind_status", nullable = false, length = 20)
    private String remindStatus = "NONE";

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    /** Trigger {@code trg_touch_updated_at} tự đặt mỗi lần UPDATE. */
    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt = Instant.now();

    protected Activity() {
        // JPA yêu cầu constructor không tham số
    }

    public Activity(UUID tenantId, UUID contactId, String type, String source, UUID performedBy) {
        this.tenantId = tenantId;
        this.contactId = contactId;
        this.type = type;
        this.source = source;
        this.performedBy = performedBy;
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getContactId() { return contactId; }
    public UUID getLeadId() { return leadId; }
    public void setLeadId(UUID v) { this.leadId = v; }
    public UUID getDealId() { return dealId; }
    public void setDealId(UUID v) { this.dealId = v; }
    public UUID getConversationId() { return conversationId; }
    public void setConversationId(UUID v) { this.conversationId = v; }
    public String getType() { return type; }
    public String getSubject() { return subject; }
    public void setSubject(String v) { this.subject = v; }
    public String getContent() { return content; }
    public void setContent(String v) { this.content = v; }
    public String getOutcome() { return outcome; }
    public void setOutcome(String v) { this.outcome = v; }
    public String getSource() { return source; }
    public UUID getPerformedBy() { return performedBy; }
    public Instant getPerformedAt() { return performedAt; }
    public void setPerformedAt(Instant v) { this.performedAt = v; }
    public Instant getRemindAt() { return remindAt; }
    public UUID getRemindUserId() { return remindUserId; }
    public String getRemindStatus() { return remindStatus; }
    public Instant getCreatedAt() { return createdAt; }

    /** Đặt lời nhắc — các cột nhắc cùng lúc, giữ ràng buộc NONE ⇔ không có giờ nhắc. */
    public void setReminder(Instant at, UUID userId, String status) {
        this.remindAt = at;
        this.remindUserId = userId;
        this.remindStatus = status;
    }
}
