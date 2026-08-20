package com.thesis.crm.sales.entity;

import com.thesis.crm.common.enums.LeadStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/**
 * MẪU — entity chuẩn của java-core. Copy cấu trúc này cho các entity khác.
 *
 * <p>Ba quy tắc bắt buộc với mọi entity nghiệp vụ:
 *
 * <ol>
 *   <li>Có cột {@code tenant_id}. Không có thì RLS không lọc được (ADR-0001).
 *   <li>Khai báo {@code schema} tường minh — bốn schema của Track A tách theo bounded context.
 *   <li>KHÔNG tự lọc {@code tenant_id} trong câu truy vấn ở tầng repository. Việc đó do RLS
 *       lo, dựa trên biến phiên {@code app.tenant_id} mà {@code security/} đặt cho mỗi
 *       transaction. Lọc ở tầng ứng dụng là lớp phòng thủ thứ hai, không phải lớp thứ nhất.
 * </ol>
 */
@Entity
@Table(name = "leads", schema = "sales")
public class Lead {

    @Id
    @Column(name = "id", nullable = false)
    private UUID id;

    /** Khoá cô lập đa khách thuê. RLS policy so cột này với {@code app.tenant_id}. */
    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "full_name", nullable = false, length = 200)
    private String fullName;

    @Column(name = "phone", length = 30)
    private String phone;

    @Column(name = "email", length = 200)
    private String email;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 30)
    private LeadStatus status;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at")
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

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public LeadStatus getStatus() {
        return status;
    }

    public void setStatus(LeadStatus status) {
        this.status = status;
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
