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

    /** Chụp lại lúc ghi (V136) — vẫn đọc được "ai đã làm" sau khi người dùng bị xoá. */
    @Column(name = "actor_email", length = 255)
    private String actorEmail;

    /** Dòng có dữ liệu cá nhân: {@code before/after} là bản ĐÃ CHE, bản gốc nằm ở {@link #piiEncrypted}. */
    @Column(name = "contains_personal_data", nullable = false)
    private boolean containsPersonalData;

    /** Bản gốc phần trước/sau, mã hoá AES-GCM ở ứng dụng — CSDL không bao giờ thấy bản rõ (V136). */
    @Column(name = "pii_encrypted")
    private byte[] piiEncrypted;

    /** Mã khoá đã dùng để mã hoá — để xoay khoá mà dòng cũ vẫn giải mã được. */
    @Column(name = "pii_key_id", length = 64)
    private String piiKeyId;

    /** Lý do của chính hành động — bắt buộc với "xem đầy đủ" (UC040 luồng 6.2). */
    private String reason;

    /**
     * CSDL đặt bằng {@code now()} — thời điểm BẮT ĐẦU transaction, nên mọi dòng nhật ký của cùng một thao
     * tác có chung một mốc. Vì vậy trên bản ghi vừa {@code save()} hai trường này còn {@code null}; đọc lại
     * từ CSDL mới có giá trị.
     */
    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false, insertable = false, updatable = false)
    private Instant updatedAt;

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

    /** Email người làm, chụp lại lúc ghi — gọi TRƯỚC khi lưu. */
    public AuditLog withActorEmail(String email) {
        this.actorEmail = email;
        return this;
    }

    /** Lý do của hành động — gọi TRƯỚC khi lưu. */
    public AuditLog withReason(String reason) {
        this.reason = reason;
        return this;
    }

    /**
     * Dòng có dữ liệu cá nhân: {@code before/after} đã gắn là bản ĐÃ CHE, còn bản gốc mã hoá nằm ở
     * {@code encrypted}. {@code encrypted = null} (không mã hoá được) thì vẫn đánh dấu có dữ liệu cá nhân
     * nhưng không có gì để "xem đầy đủ" — UC040 luồng 2.1. Gọi TRƯỚC khi lưu.
     */
    public AuditLog withPersonalData(byte[] encrypted, String keyId) {
        this.containsPersonalData = true;
        this.piiEncrypted = encrypted;
        this.piiKeyId = encrypted == null ? null : keyId;
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
    public String getActorEmail() { return actorEmail; }
    public boolean isContainsPersonalData() { return containsPersonalData; }
    public byte[] getPiiEncrypted() { return piiEncrypted; }
    public String getPiiKeyId() { return piiKeyId; }
    public String getReason() { return reason; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
