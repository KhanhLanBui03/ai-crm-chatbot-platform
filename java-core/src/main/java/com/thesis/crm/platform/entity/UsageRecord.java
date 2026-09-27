package com.thesis.crm.platform.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "usage_records", schema = "platform")
public class UsageRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "subscription_id", nullable = false)
    private UUID subscriptionId;

    @Column(nullable = false, length = 30)
    private String metric;

    @Column(name = "used_value", nullable = false)
    private long usedValue = 0;

    @Column(name = "quota_value", nullable = false)
    private long quotaValue;

    @Column(name = "last_calculated_at")
    private Instant lastCalculatedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    public UsageRecord() {}

    public UsageRecord(UUID tenantId, UUID subscriptionId, String metric, long quotaValue) {
        this.tenantId = tenantId;
        this.subscriptionId = subscriptionId;
        this.metric = metric;
        this.quotaValue = quotaValue;
        this.usedValue = 0;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public UUID getTenantId() { return tenantId; }
    public void setTenantId(UUID tenantId) { this.tenantId = tenantId; }

    public UUID getSubscriptionId() { return subscriptionId; }
    public void setSubscriptionId(UUID subscriptionId) { this.subscriptionId = subscriptionId; }

    public String getMetric() { return metric; }
    public void setMetric(String metric) { this.metric = metric; }

    public long getUsedValue() { return usedValue; }
    public void setUsedValue(long usedValue) { this.usedValue = usedValue; }

    public long getQuotaValue() { return quotaValue; }
    public void setQuotaValue(long quotaValue) { this.quotaValue = quotaValue; }

    public Instant getLastCalculatedAt() { return lastCalculatedAt; }
    public void setLastCalculatedAt(Instant lastCalculatedAt) { this.lastCalculatedAt = lastCalculatedAt; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
