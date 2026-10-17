package com.thesis.crm.platform.entity;

import com.thesis.crm.common.enums.ActorType;
import com.thesis.crm.common.enums.AuditSeverity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.net.InetAddress;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.Immutable;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * {@code platform.audit_logs} — nhật ký kiểm toán (V104, UC040).
 *
 * <p><b>Chỉ thêm, không sửa:</b> {@link Immutable} khiến Hibernate bỏ qua mọi thay đổi trên bản ghi đã
 * nạp — nhật ký sửa được thì không còn là bằng chứng. Ghi bằng constructor rồi {@code save()} một lần.
 *
 * <p>{@code before_data} / {@code after_data} KHÔNG chứa dữ liệu cá nhân của khách (tên, SĐT, nội dung
 * tin nhắn) — chỉ id, mã trạng thái, số đếm. Nhật ký giữ lâu hơn dữ liệu gốc; chép PII vào đây là để
 * nó sống sót qua yêu cầu xoá (UC041).
 *
 * <p>Ràng buộc {@code ck_audit_actor}: {@link ActorType#USER} / {@link ActorType#PLATFORM_ADMIN} bắt
 * buộc có {@code actorUserId} — constructor ép điều đó.
 */
@Entity
@Immutable
@Table(name = "audit_logs", schema = "platform")
public class AuditLog {

    /** Cột {@code GENERATED ALWAYS AS IDENTITY} — CSDL sinh, ứng dụng không bao giờ ghi. */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Enumerated(EnumType.STRING)
    @Column(name = "actor_type", nullable = false, length = 20)
    private ActorType actorType;

    @Column(name = "actor_user_id")
    private UUID actorUserId;

    /** Mã hành động viết hoa, ví dụ {@code LEAD_CREATED}, {@code CONVERSATION_ASSIGNED}. */
    @Column(nullable = false, length = 60)
    private String action;

    @Column(name = "entity_type", nullable = false, length = 50)
    private String entityType;

    @Column(name = "entity_id")
    private UUID entityId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "before_data")
    private Map<String, Object> beforeData;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "after_data")
    private Map<String, Object> afterData;

    @JdbcTypeCode(SqlTypes.INET)
    @Column(name = "ip_address")
    private InetAddress ipAddress;

    @Column(name = "user_agent")
    private String userAgent;

    @Column(name = "request_id", length = 64)
    private String requestId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AuditSeverity severity = AuditSeverity.INFO;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected AuditLog() {
        // JPA yêu cầu constructor không tham số
    }

    public AuditLog(UUID tenantId, ActorType actorType, UUID actorUserId, String action,
            String entityType, UUID entityId, AuditSeverity severity) {
        boolean canNguoi = actorType == ActorType.USER || actorType == ActorType.PLATFORM_ADMIN;
        if (canNguoi && actorUserId == null) {
            throw new IllegalArgumentException(actorType + " bắt buộc có actorUserId.");
        }
        this.tenantId = tenantId;
        this.actorType = actorType;
        this.actorUserId = actorUserId;
        this.action = action;
        this.entityType = entityType;
        this.entityId = entityId;
        this.severity = severity == null ? AuditSeverity.INFO : severity;
    }

    /** Gắn dữ liệu trước/sau — gọi TRƯỚC khi lưu; sau khi lưu bản ghi không đổi được nữa. */
    public AuditLog withData(Map<String, Object> before, Map<String, Object> after) {
        this.beforeData = before;
        this.afterData = after;
        return this;
    }

    /** Gắn ngữ cảnh request — gọi TRƯỚC khi lưu. */
    public AuditLog withRequest(InetAddress ip, String userAgent, String requestId) {
        this.ipAddress = ip;
        this.userAgent = userAgent;
        this.requestId = requestId;
        return this;
    }

    public Long getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public ActorType getActorType() { return actorType; }
    public UUID getActorUserId() { return actorUserId; }
    public String getAction() { return action; }
    public String getEntityType() { return entityType; }
    public UUID getEntityId() { return entityId; }
    public Map<String, Object> getBeforeData() { return beforeData; }
    public Map<String, Object> getAfterData() { return afterData; }
    public InetAddress getIpAddress() { return ipAddress; }
    public String getUserAgent() { return userAgent; }
    public String getRequestId() { return requestId; }
    public AuditSeverity getSeverity() { return severity; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
