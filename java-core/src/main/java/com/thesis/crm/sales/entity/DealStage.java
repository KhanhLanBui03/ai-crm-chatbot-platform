package com.thesis.crm.sales.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;
import org.hibernate.annotations.Immutable;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * {@code sales.deal_stages} — giai đoạn của phễu (UC034; V108, V133). Chỉ đọc — xem {@link Pipeline}.
 *
 * <p>{@code required_fields} là mảng {@code text[]} tên trường deal bắt buộc phải có trước khi vào giai
 * đoạn này (vd. "Đã báo giá" đòi {@code amount}).
 */
@Entity
@Immutable
@Table(name = "deal_stages", schema = "sales")
public class DealStage {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "pipeline_id", nullable = false)
    private UUID pipelineId;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false)
    private short position;

    private Short probability;

    @Column(name = "is_won", nullable = false)
    private boolean won;

    @Column(name = "is_lost", nullable = false)
    private boolean lost;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "required_fields", nullable = false)
    private String[] requiredFields;

    protected DealStage() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getPipelineId() { return pipelineId; }
    public String getName() { return name; }
    public short getPosition() { return position; }
    public Short getProbability() { return probability; }
    public boolean isWon() { return won; }
    public boolean isLost() { return lost; }
    public String[] getRequiredFields() { return requiredFields; }
}
