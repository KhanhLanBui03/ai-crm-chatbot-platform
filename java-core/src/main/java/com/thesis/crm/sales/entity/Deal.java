package com.thesis.crm.sales.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;
import org.hibernate.annotations.DynamicUpdate;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * {@code sales.deals} — cơ hội bán hàng trên phễu (UC033/034; V108, V133).
 *
 * <p>Ràng buộc: trạng thái {@code OPEN} khi và chỉ khi {@code closed_at} trống — dùng
 * {@link #setStatus(String, Instant)} để đặt hai cột cùng lúc. {@code status} {@code OPEN | WON | LOST},
 * {@code source} {@code AI_LEAD | MANUAL}.
 */
@Entity
@DynamicUpdate
@Table(name = "deals", schema = "sales")
public class Deal {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "lead_id")
    private UUID leadId;

    @Column(name = "contact_id", nullable = false, updatable = false)
    private UUID contactId;

    @Column(name = "pipeline_id", nullable = false)
    private UUID pipelineId;

    @Column(name = "stage_id", nullable = false)
    private UUID stageId;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(nullable = false, length = 20)
    private String status = "OPEN";

    @Column(nullable = false, length = 20, updatable = false)
    private String source;

    @Column(precision = 18, scale = 2)
    private BigDecimal amount;

    /** Cột {@code char(3)} — khai {@code CHAR} để {@code ddl-auto: validate} không đòi {@code varchar}. */
    @JdbcTypeCode(SqlTypes.CHAR)
    @Column(nullable = false, length = 3)
    private String currency = "VND";

    @Column(name = "expected_close_date")
    private LocalDate expectedCloseDate;

    @Column(name = "stage_changed_at", nullable = false)
    private Instant stageChangedAt = Instant.now();

    @Column(name = "closed_at")
    private Instant closedAt;

    @Column(name = "close_reason", length = 200)
    private String closeReason;

    @Column(name = "owner_user_id")
    private UUID ownerUserId;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    /** Trigger {@code trg_touch_updated_at} tự đặt mỗi lần UPDATE. */
    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt = Instant.now();

    protected Deal() {
        // JPA yêu cầu constructor không tham số
    }

    public Deal(UUID tenantId, UUID contactId, UUID pipelineId, UUID stageId, String title, String source) {
        this.tenantId = tenantId;
        this.contactId = contactId;
        this.pipelineId = pipelineId;
        this.stageId = stageId;
        this.title = title;
        this.source = source;
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getLeadId() { return leadId; }
    public void setLeadId(UUID v) { this.leadId = v; }
    public UUID getContactId() { return contactId; }
    public UUID getPipelineId() { return pipelineId; }
    public UUID getStageId() { return stageId; }
    public void setStageId(UUID v) { this.stageId = v; }
    public String getTitle() { return title; }
    public void setTitle(String v) { this.title = v; }
    public String getStatus() { return status; }
    public String getSource() { return source; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal v) { this.amount = v; }
    public String getCurrency() { return currency; }
    public LocalDate getExpectedCloseDate() { return expectedCloseDate; }
    public void setExpectedCloseDate(LocalDate v) { this.expectedCloseDate = v; }
    public Instant getStageChangedAt() { return stageChangedAt; }
    public void setStageChangedAt(Instant v) { this.stageChangedAt = v; }
    public Instant getClosedAt() { return closedAt; }
    public String getCloseReason() { return closeReason; }
    public void setCloseReason(String v) { this.closeReason = v; }
    public UUID getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(UUID v) { this.ownerUserId = v; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    /** Đổi trạng thái và {@code closed_at} cùng lúc — giữ ràng buộc OPEN ⇔ chưa đóng. */
    public void setStatus(String status, Instant at) {
        this.status = status;
        this.closedAt = "OPEN".equals(status) ? null : at;
    }
}
