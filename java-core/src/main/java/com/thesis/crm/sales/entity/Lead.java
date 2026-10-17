package com.thesis.crm.sales.entity;

import com.thesis.crm.common.enums.LeadSource;
import com.thesis.crm.common.enums.LeadStatus;
import com.thesis.crm.common.enums.Level;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.DynamicUpdate;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * {@code sales.leads} — cơ hội tiềm năng (UC032; V108, V132).
 *
 * <p>Mỗi khách tối đa MỘT lead đang mở ({@code NEW | CONTACTED | QUALIFIED}) — chỉ mục duy nhất có điều
 * kiện {@code uq_leads_mot_lead_mo_moi_khach} (V132). Ba cột điểm ({@code current_score},
 * {@code score_reason}, {@code score_updated_at}) do UC030 ghi, phải có/trống cùng lúc.
 */
@Entity
@DynamicUpdate
@Table(name = "leads", schema = "sales")
public class Lead {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "contact_id", nullable = false, updatable = false)
    private UUID contactId;

    @Column(name = "source_conversation_id")
    private UUID sourceConversationId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30, updatable = false)
    private LeadSource source;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private LeadStatus status = LeadStatus.NEW;

    @Column(name = "interested_product", length = 200)
    private String interestedProduct;

    @Column(name = "budget_min", precision = 18, scale = 2)
    private BigDecimal budgetMin;

    @Column(name = "budget_max", precision = 18, scale = 2)
    private BigDecimal budgetMax;

    @Enumerated(EnumType.STRING)
    @Column(name = "budget_confidence", length = 10)
    private Level budgetConfidence;

    @Enumerated(EnumType.STRING)
    @Column(length = 10)
    private Level urgency;

    @Column(name = "interest_summary")
    private String interestSummary;

    @Column(name = "current_score")
    private Short currentScore;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "score_reason")
    private Map<String, Object> scoreReason;

    @Column(name = "score_updated_at")
    private Instant scoreUpdatedAt;

    @Column(name = "owner_user_id")
    private UUID ownerUserId;

    @Column(name = "converted_at")
    private Instant convertedAt;

    @Column(name = "disqualified_reason", length = 200)
    private String disqualifiedReason;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    /** Trigger {@code trg_touch_updated_at} tự đặt mỗi lần UPDATE. */
    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt = Instant.now();

    protected Lead() {
        // JPA yêu cầu constructor không tham số
    }

    public Lead(UUID tenantId, UUID contactId, LeadSource source) {
        this.tenantId = tenantId;
        this.contactId = contactId;
        this.source = source;
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getContactId() { return contactId; }
    public UUID getSourceConversationId() { return sourceConversationId; }
    public void setSourceConversationId(UUID v) { this.sourceConversationId = v; }
    public LeadSource getSource() { return source; }
    public LeadStatus getStatus() { return status; }
    public void setStatus(LeadStatus status) { this.status = status; }
    public String getInterestedProduct() { return interestedProduct; }
    public void setInterestedProduct(String v) { this.interestedProduct = v; }
    public BigDecimal getBudgetMin() { return budgetMin; }
    public void setBudgetMin(BigDecimal v) { this.budgetMin = v; }
    public BigDecimal getBudgetMax() { return budgetMax; }
    public void setBudgetMax(BigDecimal v) { this.budgetMax = v; }
    public Level getBudgetConfidence() { return budgetConfidence; }
    public void setBudgetConfidence(Level v) { this.budgetConfidence = v; }
    public Level getUrgency() { return urgency; }
    public void setUrgency(Level v) { this.urgency = v; }
    public String getInterestSummary() { return interestSummary; }
    public void setInterestSummary(String v) { this.interestSummary = v; }
    public Short getCurrentScore() { return currentScore; }
    public Map<String, Object> getScoreReason() { return scoreReason; }
    public Instant getScoreUpdatedAt() { return scoreUpdatedAt; }
    public UUID getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(UUID v) { this.ownerUserId = v; }
    public Instant getConvertedAt() { return convertedAt; }
    public void setConvertedAt(Instant v) { this.convertedAt = v; }
    public String getDisqualifiedReason() { return disqualifiedReason; }
    public void setDisqualifiedReason(String v) { this.disqualifiedReason = v; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
