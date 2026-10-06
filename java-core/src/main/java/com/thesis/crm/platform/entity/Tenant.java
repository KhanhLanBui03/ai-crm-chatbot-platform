package com.thesis.crm.platform.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "tenants", schema = "platform")
public class Tenant {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 200)
    private String name;

    @Column(nullable = false, length = 64, unique = true)
    private String slug;

    @Column(length = 100)
    private String industry;

    @Column(name = "contact_email", nullable = false, length = 255)
    private String contactEmail;

    @Column(length = 20)
    private String phone;

    @Column(nullable = false, length = 64)
    private String timezone = "Asia/Ho_Chi_Minh";

    @Column(nullable = false, length = 10)
    private String locale = "vi-VN";

    @Column(nullable = false, columnDefinition = "jsonb")
    @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.JSON)
    private String businessHours = "{}";

    @Column(name = "ai_tone", nullable = false, length = 30)
    private String aiTone = "FRIENDLY";

    @Column(name = "lead_score_threshold", nullable = false)
    private short leadScoreThreshold = 70;

    @Column(name = "auto_lead_creation", nullable = false)
    private boolean autoLeadCreation = true;

    @Column(name = "assignment_mode", nullable = false, length = 20)
    private String assignmentMode = "LEAST_BUSY";

    @Column(name = "assignment_config", nullable = false, columnDefinition = "jsonb")
    @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.JSON)
    private String assignmentConfig = "{}";

    @Column(nullable = false, length = 30)
    private String status = "TRIAL";

    @Column(name = "suspended_reason")
    private String suspendedReason;

    @Column(name = "suspended_at")
    private Instant suspendedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    public Tenant() {}

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getSlug() { return slug; }
    public void setSlug(String slug) { this.slug = slug; }

    public String getIndustry() { return industry; }
    public void setIndustry(String industry) { this.industry = industry; }

    public String getContactEmail() { return contactEmail; }
    public void setContactEmail(String contactEmail) { this.contactEmail = contactEmail; }

    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }

    public String getTimezone() { return timezone; }
    public void setTimezone(String timezone) { this.timezone = timezone; }

    public String getLocale() { return locale; }
    public void setLocale(String locale) { this.locale = locale; }

    public String getBusinessHours() { return businessHours; }
    public void setBusinessHours(String businessHours) { this.businessHours = businessHours; }

    public String getAiTone() { return aiTone; }
    public void setAiTone(String aiTone) { this.aiTone = aiTone; }

    public short getLeadScoreThreshold() { return leadScoreThreshold; }
    public void setLeadScoreThreshold(short leadScoreThreshold) { this.leadScoreThreshold = leadScoreThreshold; }

    public boolean isAutoLeadCreation() { return autoLeadCreation; }
    public void setAutoLeadCreation(boolean autoLeadCreation) { this.autoLeadCreation = autoLeadCreation; }

    public String getAssignmentMode() { return assignmentMode; }
    public void setAssignmentMode(String assignmentMode) { this.assignmentMode = assignmentMode; }

    public String getAssignmentConfig() { return assignmentConfig; }
    public void setAssignmentConfig(String assignmentConfig) { this.assignmentConfig = assignmentConfig; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getSuspendedReason() { return suspendedReason; }
    public void setSuspendedReason(String suspendedReason) { this.suspendedReason = suspendedReason; }

    public Instant getSuspendedAt() { return suspendedAt; }
    public void setSuspendedAt(Instant suspendedAt) { this.suspendedAt = suspendedAt; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
