package com.thesis.crm.engagement.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.Immutable;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * {@code engagement.channels} — kênh chat của doanh nghiệp (V106, V127). Chỉ đọc ở đây.
 *
 * <p>Cố ý KHÔNG map các cột bí mật ({@code credential_encrypted}, {@code webhook_secret_encrypted},
 * {@code credential_key_id}): Entity được nạp ở nhiều nơi (hộp thư, widget) — bí mật không có lý do gì
 * nằm trong bộ nhớ của các luồng đó. Cấu hình widget ghi ở {@code WidgetConfigService}.
 */
@Entity
@Immutable
@Table(name = "channels", schema = "engagement")
public class Channel {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    /** {@code WEB_WIDGET | ZALO | FACEBOOK}. */
    @Column(nullable = false, length = 30)
    private String type;

    @Column(nullable = false, length = 150)
    private String name;

    /** Khoá công khai {@code wk_...} — chỉ kênh WEB_WIDGET có. */
    @Column(name = "widget_key", length = 64)
    private String widgetKey;

    /** {@code DISCONNECTED | PENDING_VERIFY | ACTIVE | ERROR}. */
    @Column(nullable = false, length = 30)
    private String status;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false)
    private Map<String, Object> config;

    protected Channel() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public String getType() { return type; }
    public String getName() { return name; }
    public String getWidgetKey() { return widgetKey; }
    public String getStatus() { return status; }
    public Map<String, Object> getConfig() { return config; }
}
