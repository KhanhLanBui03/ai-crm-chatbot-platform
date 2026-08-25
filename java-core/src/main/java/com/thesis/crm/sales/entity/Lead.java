package com.thesis.crm.sales.entity;

import com.thesis.crm.common.enums.LeadSource;
import com.thesis.crm.common.enums.LeadStatus;
import com.thesis.crm.common.enums.Level;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * MẪU — entity chuẩn của java-core. Copy cấu trúc này cho các entity khác.
 *
 * <p>Ánh xạ bảng {@code sales.leads} do migration V108 tạo. {@code ddl-auto: validate} nên mọi
 * cột khai ở đây phải tồn tại thật với đúng kiểu — sai một cột là ứng dụng không khởi động
 * được. Chiều ngược lại thì không bắt buộc: bảng có cột mà entity không khai vẫn hợp lệ, và
 * {@code score_reason jsonb} cố ý để ngoài vì nó chỉ phục vụ màn giải thích điểm.
 *
 * <p>Bốn quy tắc bắt buộc với mọi entity nghiệp vụ:
 *
 * <ol>
 *   <li>Có cột {@code tenant_id}. Không có thì RLS không lọc được (ADR-0001).
 *   <li>Khai báo {@code schema} tường minh — bốn schema của Track A tách theo bounded context.
 *   <li>KHÔNG tự lọc {@code tenant_id} trong câu truy vấn ở tầng repository. Việc đó do RLS
 *       lo, dựa trên biến phiên {@code app.tenant_id} mà {@code security/} đặt cho mỗi
 *       transaction. Lọc ở tầng ứng dụng là lớp phòng thủ thứ hai, không phải lớp thứ nhất.
 *   <li>Enum khai {@code EnumType.STRING}. Dùng {@code ORDINAL} thì chèn một giá trị vào giữa
 *       danh sách sẽ dịch chuyển toàn bộ dữ liệu cũ, âm thầm và không thể phát hiện.
 * </ol>
 *
 * <p><b>Ngoại lệ liên làn duy nhất của cả dự án nằm ở entity này:</b> cột
 * {@code current_score} do Track B tính, nhưng ghi qua API {@code PUT
 * /internal/leads/{id}/score} chứ không nối thẳng cơ sở dữ liệu (ADR-0002).
 */
@Entity
@Table(name = "leads", schema = "sales")
public class Lead {

    @Id
    @Column(name = "id", nullable = false)
    private UUID id;

    /** Khoá cô lập đa khách thuê. RLS policy so cột này với {@code platform.current_tenant()}. */
    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    /** Khách hàng trong danh bạ. Cơ hội tiềm năng luôn gắn với một người cụ thể. */
    @Column(name = "contact_id", nullable = false)
    private UUID contactId;

    /**
     * Hội thoại đã sinh ra cơ hội này — thứ cho phép truy ngược từ một con số doanh thu về đúng
     * cuộc trò chuyện. Thành {@code null} khi hội thoại bị xoá theo yêu cầu xoá dữ liệu cá nhân
     * (UC041): cơ hội vẫn còn, chỉ mất liên kết.
     */
    @Column(name = "source_conversation_id")
    private UUID sourceConversationId;

    @Enumerated(EnumType.STRING)
    @Column(name = "source", nullable = false, length = 30)
    private LeadSource source;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 30)
    private LeadStatus status;

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
    @Column(name = "urgency", length = 10)
    private Level urgency;

    @Column(name = "interest_summary")
    private String interestSummary;

    /** 0–100. Track B ghi qua API nội bộ, không ghi thẳng bảng. */
    @Column(name = "current_score")
    private Short currentScore;

    @Column(name = "score_updated_at")
    private Instant scoreUpdatedAt;

    @Column(name = "owner_user_id")
    private UUID ownerUserId;

    @Column(name = "converted_at")
    private Instant convertedAt;

    @Column(name = "disqualified_reason", length = 200)
    private String disqualifiedReason;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected Lead() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public UUID getTenantId() {
        return tenantId;
    }

    public void setTenantId(UUID tenantId) {
        this.tenantId = tenantId;
    }

    public UUID getContactId() {
        return contactId;
    }

    public void setContactId(UUID contactId) {
        this.contactId = contactId;
    }

    public UUID getSourceConversationId() {
        return sourceConversationId;
    }

    public void setSourceConversationId(UUID sourceConversationId) {
        this.sourceConversationId = sourceConversationId;
    }

    public LeadSource getSource() {
        return source;
    }

    public void setSource(LeadSource source) {
        this.source = source;
    }

    public LeadStatus getStatus() {
        return status;
    }

    public void setStatus(LeadStatus status) {
        this.status = status;
    }

    public String getInterestedProduct() {
        return interestedProduct;
    }

    public void setInterestedProduct(String interestedProduct) {
        this.interestedProduct = interestedProduct;
    }

    public BigDecimal getBudgetMin() {
        return budgetMin;
    }

    public void setBudgetMin(BigDecimal budgetMin) {
        this.budgetMin = budgetMin;
    }

    public BigDecimal getBudgetMax() {
        return budgetMax;
    }

    public void setBudgetMax(BigDecimal budgetMax) {
        this.budgetMax = budgetMax;
    }

    public Level getBudgetConfidence() {
        return budgetConfidence;
    }

    public void setBudgetConfidence(Level budgetConfidence) {
        this.budgetConfidence = budgetConfidence;
    }

    public Level getUrgency() {
        return urgency;
    }

    public void setUrgency(Level urgency) {
        this.urgency = urgency;
    }

    public String getInterestSummary() {
        return interestSummary;
    }

    public void setInterestSummary(String interestSummary) {
        this.interestSummary = interestSummary;
    }

    public Short getCurrentScore() {
        return currentScore;
    }

    public void setCurrentScore(Short currentScore) {
        this.currentScore = currentScore;
    }

    public Instant getScoreUpdatedAt() {
        return scoreUpdatedAt;
    }

    public void setScoreUpdatedAt(Instant scoreUpdatedAt) {
        this.scoreUpdatedAt = scoreUpdatedAt;
    }

    public UUID getOwnerUserId() {
        return ownerUserId;
    }

    public void setOwnerUserId(UUID ownerUserId) {
        this.ownerUserId = ownerUserId;
    }

    public Instant getConvertedAt() {
        return convertedAt;
    }

    public void setConvertedAt(Instant convertedAt) {
        this.convertedAt = convertedAt;
    }

    public String getDisqualifiedReason() {
        return disqualifiedReason;
    }

    public void setDisqualifiedReason(String disqualifiedReason) {
        this.disqualifiedReason = disqualifiedReason;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }
}
