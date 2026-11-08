package com.thesis.crm.platform.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

/**
 * Mức tiêu thụ một chỉ số trong một chu kỳ — {@code platform.usage_records} (V102, V128).
 *
 * <p>{@code quotaValue} là ẢNH CHỤP của gói lúc mở chu kỳ, không đọc qua {@code plan_id}: đổi gói
 * giữa chừng mà đọc qua khoá ngoại thì báo cáo chu kỳ cũ sai ngay (ERD mục 5.7).
 *
 * <p>{@code STORAGE_MB} tính bằng BYTE ở cả {@code usedValue} lẫn {@code quotaValue}, dù tên là MB
 * (ADR-0023 (c)).
 */
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

    /** Lần đầu chạm 80% trong chu kỳ (V128). Ghi một lần, không ghi đè. */
    @Column(name = "warned_at")
    private Instant warnedAt;

    /** Lần đầu chạm 100% trong chu kỳ (V128). Có giá trị thì {@code warnedAt} cũng phải có. */
    @Column(name = "blocked_at")
    private Instant blockedAt;

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

    public Instant getWarnedAt() { return warnedAt; }
    public void setWarnedAt(Instant warnedAt) { this.warnedAt = warnedAt; }

    public Instant getBlockedAt() { return blockedAt; }
    public void setBlockedAt(Instant blockedAt) { this.blockedAt = blockedAt; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }

    /** UC006 "Tham số và ngưỡng": cảnh báo 80%, chặn 100%. */
    public static final int NGUONG_CANH_BAO_PHAN_TRAM = 80;

    /**
     * Cộng mức dùng rồi ghi mốc chạm 80% / 100% nếu vừa chạm (V128). MỌI chỗ cộng tiêu thụ đi qua đây — cộng
     * bằng câu UPDATE thẳng là mất mốc: màn hạn mức không bao giờ biết đã chạm ngưỡng lúc nào.
     */
    public void cong(long soLuong, Instant luc) {
        usedValue += soLuong;
        lastCalculatedAt = luc;
        ghiMocTheoMucDung(luc);
    }

    /**
     * Ghi mốc theo mức dùng HIỆN TẠI. Thứ tự 80% rồi 100% là bắt buộc: ràng buộc {@code ck_usage_moc_theo_thu_tu}
     * (V128) từ chối dòng có {@code blocked_at} mà thiếu {@code warned_at}. Nhân chéo thay vì chia để khỏi sai
     * số dấu phẩy động ở đúng ngưỡng. Mỗi mốc ghi MỘT LẦN mỗi chu kỳ — không ghi đè.
     */
    public void ghiMocTheoMucDung(Instant luc) {
        if (warnedAt == null && usedValue * 100 >= quotaValue * NGUONG_CANH_BAO_PHAN_TRAM) {
            warnedAt = luc;
        }
        if (blockedAt == null && usedValue >= quotaValue) {
            blockedAt = luc;
        }
    }

    /** Đã hết hạn mức của chu kỳ — dùng để quyết định tác tử còn trả lời tự động hay không. */
    public boolean daHet() {
        return usedValue >= quotaValue;
    }
}
