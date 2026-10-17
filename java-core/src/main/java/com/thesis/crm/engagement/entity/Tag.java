package com.thesis.crm.engagement.entity;

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
 * {@code engagement.tags} — thẻ phân loại khách (UC017; V105, V125).
 *
 * <p>{@code usage_count} do trigger {@code trg_contact_tags_count} (V125) cộng/trừ khi gắn/gỡ — chỉ đọc
 * ở đây. Tên là duy nhất trong doanh nghiệp sau khi bỏ dấu và viết thường (chỉ mục
 * {@code uq_tags_tenant_name} trên {@code engagement.fold_vi(btrim(name))}).
 */
@Entity
@DynamicUpdate
@Table(name = "tags", schema = "engagement")
public class Tag {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(nullable = false, length = 7)
    private String color;

    private String description;

    @Column(name = "usage_count", nullable = false, insertable = false, updatable = false)
    private int usageCount;

    @Column(name = "created_by", updatable = false)
    private UUID createdBy;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    /** Trigger {@code trg_touch_updated_at} tự đặt mỗi lần UPDATE. */
    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt = Instant.now();

    protected Tag() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public String getName() { return name; }
    public String getColor() { return color; }
    public String getDescription() { return description; }
    public int getUsageCount() { return usageCount; }
    public UUID getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
}
