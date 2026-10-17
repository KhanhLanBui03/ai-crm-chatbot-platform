package com.thesis.crm.engagement.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/**
 * {@code engagement.channel_identities} — một khách trên một kênh (mã khách của widget, ID Zalo…; V106).
 * Duy nhất theo {@code (tenant_id, channel_id, external_user_id)}.
 *
 * <p>Không có hàm sửa trên Entity: tạo mới cần {@code ON CONFLICT DO NOTHING} (hai tin của cùng một khách gửi gần
 * như cùng lúc), còn gắn khách / cập nhật lần cuối thấy đi bằng {@code UPDATE} JPQL ở
 * {@code WidgetRepository} — không nạp rồi sửa.
 */
@Entity
@Table(name = "channel_identities", schema = "engagement")
public class ChannelIdentity {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "channel_id", nullable = false)
    private UUID channelId;

    @Column(name = "contact_id")
    private UUID contactId;

    @Column(name = "external_user_id", nullable = false, length = 255)
    private String externalUserId;

    @Column(name = "display_name", length = 200)
    private String displayName;

    @Column(name = "first_seen_at", nullable = false)
    private Instant firstSeenAt;

    @Column(name = "last_seen_at", nullable = false)
    private Instant lastSeenAt;

    protected ChannelIdentity() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getChannelId() { return channelId; }
    public UUID getContactId() { return contactId; }
    public String getExternalUserId() { return externalUserId; }
    public String getDisplayName() { return displayName; }
    public Instant getFirstSeenAt() { return firstSeenAt; }
    public Instant getLastSeenAt() { return lastSeenAt; }
}
