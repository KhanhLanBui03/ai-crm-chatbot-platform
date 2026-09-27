package com.thesis.crm.platform.entity;

import com.thesis.crm.common.enums.UsageMetric;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/**
 * Mức tiêu thụ một chỉ số trong một chu kỳ — {@code platform.usage_records} (V102, V116).
 *
 * <p>{@code quotaValue} là ẢNH CHỤP của gói lúc mở chu kỳ, không đọc qua {@code plan_id}: đổi gói
 * giữa chừng mà đọc qua khoá ngoại thì báo cáo chu kỳ cũ sai ngay (ERD mục 5.7).
 *
 * <p>Dòng mới chỉ sinh bằng câu {@code INSERT … ON CONFLICT} ở {@code UsageRecordRepository} —
 * không {@code persist} từ Java — nên {@code created_at}/{@code updated_at} để CSDL tự lo
 * (DEFAULT và trigger {@code trg_touch_updated_at}), Hibernate không ghi hai cột đó.
 */
@Entity
@Table(name = "usage_records", schema = "platform")
public class UsageRecord {

    @Id
    @Column(name = "id", nullable = false)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "subscription_id", nullable = false, updatable = false)
    private UUID subscriptionId;

    @Enumerated(EnumType.STRING)
    @Column(name = "metric", nullable = false, length = 30, updatable = false)
    private UsageMetric metric;

    @Column(name = "used_value", nullable = false)
    private long usedValue;

    @Column(name = "quota_value", nullable = false)
    private long quotaValue;

    @Column(name = "last_calculated_at")
    private Instant lastCalculatedAt;

    /** Lần đầu chạm 80% trong chu kỳ (V116). Ghi một lần, không ghi đè. */
    @Column(name = "warned_at")
    private Instant warnedAt;

    /** Lần đầu chạm 100% trong chu kỳ (V116). Có giá trị thì {@code warnedAt} cũng phải có. */
    @Column(name = "blocked_at")
    private Instant blockedAt;

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false, insertable = false, updatable = false)
    private Instant updatedAt;

    protected UsageRecord() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() {
        return id;
    }

    public UUID getTenantId() {
        return tenantId;
    }

    public UUID getSubscriptionId() {
        return subscriptionId;
    }

    public UsageMetric getMetric() {
        return metric;
    }

    public long getUsedValue() {
        return usedValue;
    }

    public void setUsedValue(long usedValue) {
        this.usedValue = usedValue;
    }

    public long getQuotaValue() {
        return quotaValue;
    }

    public Instant getLastCalculatedAt() {
        return lastCalculatedAt;
    }

    public void setLastCalculatedAt(Instant lastCalculatedAt) {
        this.lastCalculatedAt = lastCalculatedAt;
    }

    public Instant getWarnedAt() {
        return warnedAt;
    }

    public void setWarnedAt(Instant warnedAt) {
        this.warnedAt = warnedAt;
    }

    public Instant getBlockedAt() {
        return blockedAt;
    }

    public void setBlockedAt(Instant blockedAt) {
        this.blockedAt = blockedAt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
