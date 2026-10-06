package com.thesis.crm.engagement.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/**
 * {@code engagement.contacts} — khách hàng (V105 + V124). Dùng cho GHI; các phép đọc danh sách
 * và hồ sơ đi qua {@code ContactQueryRepository} (SQL tường minh, lọc tenant ngay trong câu).
 */
@Entity
@Table(name = "contacts", schema = "engagement")
public class Contact {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "full_name", length = 200)
    private String fullName;

    @Column(length = 255)
    private String email;

    @Column(length = 20)
    private String phone;

    @Column(length = 200)
    private String company;

    @Column(name = "primary_channel", nullable = false, length = 30)
    private String primaryChannel;

    @Column(name = "owner_user_id")
    private UUID ownerUserId;

    @Column(nullable = false, length = 30)
    private String status = "ACTIVE";

    @Column(name = "merged_into_contact_id")
    private UUID mergedIntoContactId;

    @Column(name = "last_contacted_at")
    private Instant lastContactedAt;

    @Column(name = "consent_marketing", nullable = false)
    private boolean consentMarketing;

    @Column(name = "consent_granted", nullable = false)
    private boolean consentGranted;

    @Column(name = "consent_at")
    private Instant consentAt;

    @Column(name = "consent_source", length = 20)
    private String consentSource;

    @Column(name = "search_text", nullable = false)
    private String searchText = "";

    @Column(name = "anonymized_at")
    private Instant anonymizedAt;

    @Column(name = "deleted_at")
    private Instant deletedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public void setTenantId(UUID tenantId) { this.tenantId = tenantId; }
    public String getFullName() { return fullName; }
    public void setFullName(String fullName) { this.fullName = fullName; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }
    public String getCompany() { return company; }
    public void setCompany(String company) { this.company = company; }
    public String getPrimaryChannel() { return primaryChannel; }
    public void setPrimaryChannel(String primaryChannel) { this.primaryChannel = primaryChannel; }
    public UUID getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(UUID ownerUserId) { this.ownerUserId = ownerUserId; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public UUID getMergedIntoContactId() { return mergedIntoContactId; }
    public Instant getLastContactedAt() { return lastContactedAt; }
    public void setLastContactedAt(Instant lastContactedAt) { this.lastContactedAt = lastContactedAt; }
    public boolean isConsentMarketing() { return consentMarketing; }
    public boolean isConsentGranted() { return consentGranted; }
    public Instant getConsentAt() { return consentAt; }
    public String getConsentSource() { return consentSource; }
    public String getSearchText() { return searchText; }
    public void setSearchText(String searchText) { this.searchText = searchText; }
    public Instant getAnonymizedAt() { return anonymizedAt; }
    public Instant getDeletedAt() { return deletedAt; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    /**
     * Đồng ý xử lý dữ liệu (NĐ 13): bật thì ghi thời điểm + nguồn, tắt thì xoá cả hai —
     * khớp ràng buộc {@code ck_contacts_consent} (V124).
     */
    public void setConsent(boolean granted, String source, Instant at) {
        this.consentGranted = granted;
        this.consentAt = granted ? at : null;
        this.consentSource = granted ? source : null;
    }
}
