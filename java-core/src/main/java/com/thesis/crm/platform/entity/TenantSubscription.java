package com.thesis.crm.platform.entity;

import com.thesis.crm.common.enums.SubscriptionStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/**
 * Thuê bao theo chu kỳ — {@code platform.tenant_subscriptions} (V102).
 *
 * <p>Mới khai những cột UC018 cần để tìm chu kỳ đang hiệu lực; {@code ddl-auto: validate} chỉ
 * kiểm cột ĐÃ khai. UC005 (đổi gói) sẽ bổ sung phần còn lại cùng setter — ở đây chỉ đọc.
 */
@Entity
@Table(name = "tenant_subscriptions", schema = "platform")
public class TenantSubscription {

    @Id
    @Column(name = "id", nullable = false)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "plan_id", nullable = false)
    private UUID planId;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 30)
    private SubscriptionStatus status;

    @Column(name = "period_start", nullable = false)
    private Instant periodStart;

    /** Mốc kết thúc KHÔNG thuộc chu kỳ: chu kỳ là {@code [period_start, period_end)}. */
    @Column(name = "period_end", nullable = false)
    private Instant periodEnd;

    protected TenantSubscription() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() {
        return id;
    }

    public UUID getTenantId() {
        return tenantId;
    }

    public UUID getPlanId() {
        return planId;
    }

    public SubscriptionStatus getStatus() {
        return status;
    }

    public Instant getPeriodStart() {
        return periodStart;
    }

    public Instant getPeriodEnd() {
        return periodEnd;
    }
}
