package com.thesis.crm.sales.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;
import org.hibernate.annotations.Immutable;

/**
 * {@code sales.pipelines} — phễu bán hàng (UC034; V108, V133). Chỉ đọc: phễu mặc định 5 giai đoạn do
 * trigger {@code trg_tenant_tao_pheu} (V133) tạo khi có doanh nghiệp mới, ứng dụng không sửa phễu.
 */
@Entity
@Immutable
@Table(name = "pipelines", schema = "sales")
public class Pipeline {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(nullable = false, length = 150)
    private String name;

    @Column(name = "is_default", nullable = false)
    private boolean isDefault;

    @Column(name = "is_active", nullable = false)
    private boolean isActive;

    protected Pipeline() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public String getName() { return name; }
    public boolean isDefault() { return isDefault; }
    public boolean isActive() { return isActive; }
}
