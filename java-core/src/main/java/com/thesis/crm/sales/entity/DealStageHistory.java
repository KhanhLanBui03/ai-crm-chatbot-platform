package com.thesis.crm.sales.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.Immutable;

/**
 * {@code sales.deal_stage_history} — mỗi lần deal đổi giai đoạn (UC034; V133). Chỉ thêm, không sửa.
 *
 * <p>{@code from_stage_id = null} là dòng tạo deal. {@code duration_seconds} là thời gian deal nằm ở giai
 * đoạn TRƯỚC — nguồn của thống kê "deal kẹt bao lâu ở mỗi cột" (UC036).
 */
@Entity
@Immutable
@Table(name = "deal_stage_history", schema = "sales")
public class DealStageHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "deal_id", nullable = false)
    private UUID dealId;

    @Column(name = "from_stage_id")
    private UUID fromStageId;

    @Column(name = "to_stage_id", nullable = false)
    private UUID toStageId;

    @Column(name = "duration_seconds")
    private Long durationSeconds;

    @Column(name = "changed_by")
    private UUID changedBy;

    @Column(name = "changed_at", nullable = false)
    private Instant changedAt;

    protected DealStageHistory() {
        // JPA yêu cầu constructor không tham số
    }

    public DealStageHistory(UUID tenantId, UUID dealId, UUID fromStageId, UUID toStageId, Long durationSeconds,
            UUID changedBy, Instant changedAt) {
        this.tenantId = tenantId;
        this.dealId = dealId;
        this.fromStageId = fromStageId;
        this.toStageId = toStageId;
        this.durationSeconds = durationSeconds;
        this.changedBy = changedBy;
        this.changedAt = changedAt;
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getDealId() { return dealId; }
    public UUID getFromStageId() { return fromStageId; }
    public UUID getToStageId() { return toStageId; }
    public Long getDurationSeconds() { return durationSeconds; }
    public UUID getChangedBy() { return changedBy; }
    public Instant getChangedAt() { return changedAt; }
}
