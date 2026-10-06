package com.thesis.crm.common.audit;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * Ghi {@code platform.audit_logs} (V104) — bảng chỉ-ghi-thêm: {@code crm_app} có INSERT nhưng bị
 * REVOKE UPDATE/DELETE (V111).
 *
 * <p>Gọi TRONG transaction nghiệp vụ, sau {@code TenantTransactionScope.apply()}: thao tác rollback
 * thì dòng kiểm toán rollback theo — không có nhật ký cho việc không xảy ra, và không có việc xảy ra
 * mà thiếu nhật ký.
 *
 * <p><b>Không chép dữ liệu cá nhân vào {@code before_data/after_data}</b> (NĐ 13/2023): nhật ký kiểm
 * toán sống lâu hơn dữ liệu khách (UC041 xoá khách nhưng giữ nhật ký) — chỉ ghi trường cần chứng minh.
 */
@Component
public class AuditLogWriter {

    private final JdbcTemplate jdbc;
    private final ObjectMapper json;

    public AuditLogWriter(JdbcTemplate jdbc, ObjectMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    /** Hành động do người dùng đã đăng nhập thực hiện. */
    public void recordUserAction(
            UUID tenantId, UUID actorUserId, String action, String entityType, UUID entityId,
            Map<String, ?> afterData) {
        if (!TransactionSynchronizationManager.isActualTransactionActive()) {
            throw new IllegalStateException("AuditLogWriter phải gọi bên trong @Transactional.");
        }
        if (actorUserId == null) {
            throw new IllegalStateException("Hành động của người dùng phải biết người dùng là ai (ck_audit_actor).");
        }
        jdbc.update("""
                INSERT INTO platform.audit_logs
                    (tenant_id, actor_type, actor_user_id, action, entity_type, entity_id, after_data)
                VALUES (?, 'USER', ?, ?, ?, ?, CAST(? AS jsonb))
                """,
                tenantId, actorUserId, action, entityType, entityId, toJson(afterData));
    }

    /**
     * Sự kiện hệ thống tự ghi nhận, không có người dùng đăng nhập — vd. widget bị nhúng trên tên miền
     * lạ (UC009 10.2). {@code actor_type = 'SYSTEM'} nên không cần {@code actor_user_id}.
     */
    public void recordSystemAction(
            UUID tenantId, String action, String entityType, UUID entityId, String severity,
            Map<String, ?> afterData) {
        if (!TransactionSynchronizationManager.isActualTransactionActive()) {
            throw new IllegalStateException("AuditLogWriter phải gọi bên trong @Transactional.");
        }
        jdbc.update("""
                INSERT INTO platform.audit_logs
                    (tenant_id, actor_type, action, entity_type, entity_id, severity, after_data)
                VALUES (?, 'SYSTEM', ?, ?, ?, ?, CAST(? AS jsonb))
                """,
                tenantId, action, entityType, entityId, severity, toJson(afterData));
    }

    private String toJson(Map<String, ?> data) {
        try {
            return data == null ? null : json.writeValueAsString(data);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Không chuyển được dữ liệu kiểm toán sang JSON", e);
        }
    }
}
