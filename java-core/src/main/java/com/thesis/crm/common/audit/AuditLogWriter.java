package com.thesis.crm.common.audit;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.enums.ActorType;
import com.thesis.crm.common.enums.AuditSeverity;
import com.thesis.crm.platform.entity.AuditLog;
import com.thesis.crm.platform.repository.AuditLogRepository;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * Ghi {@code platform.audit_logs} (V104) qua {@link AuditLogRepository} — bảng chỉ-ghi-thêm:
 * {@code crm_app} có INSERT nhưng bị REVOKE UPDATE/DELETE (V111), Entity {@link AuditLog} là
 * {@code @Immutable}.
 *
 * <p>Gọi TRONG transaction nghiệp vụ, sau {@code TenantTransactionScope.apply()}: thao tác rollback
 * thì dòng kiểm toán rollback theo — không có nhật ký cho việc không xảy ra, và không có việc xảy ra
 * mà thiếu nhật ký. JPA và {@code JdbcTemplate} dùng chung kết nối của transaction
 * ({@code JpaTransactionManager}), nên biến RLS đã đặt vẫn còn hiệu lực ở đây.
 *
 * <p><b>Không chép dữ liệu cá nhân vào {@code before_data/after_data}</b> (NĐ 13/2023): nhật ký kiểm
 * toán sống lâu hơn dữ liệu khách (UC041 xoá khách nhưng giữ nhật ký) — chỉ ghi trường cần chứng minh.
 */
@Component
public class AuditLogWriter {

    private static final TypeReference<Map<String, Object>> MAP = new TypeReference<>() {};

    private final AuditLogRepository repo;
    private final ObjectMapper json;

    public AuditLogWriter(AuditLogRepository repo, ObjectMapper json) {
        this.repo = repo;
        this.json = json;
    }

    /** Hành động do người dùng đã đăng nhập thực hiện. */
    public void recordUserAction(
            UUID tenantId, UUID actorUserId, String action, String entityType, UUID entityId,
            Map<String, ?> afterData) {
        requireTransaction();
        if (actorUserId == null) {
            throw new IllegalStateException("Hành động của người dùng phải biết người dùng là ai (ck_audit_actor).");
        }
        repo.save(new AuditLog(tenantId, ActorType.USER, actorUserId, action, entityType, entityId, AuditSeverity.INFO)
                .withData(null, plain(afterData)));
    }

    /**
     * Sự kiện hệ thống tự ghi nhận, không có người dùng đăng nhập — vd. widget bị nhúng trên tên miền
     * lạ (UC009 10.2). {@code actor_type = 'SYSTEM'} nên không cần {@code actor_user_id}.
     *
     * @param severity {@code INFO | WARNING | CRITICAL}; {@code null} là {@code INFO}
     */
    public void recordSystemAction(
            UUID tenantId, String action, String entityType, UUID entityId, String severity,
            Map<String, ?> afterData) {
        requireTransaction();
        AuditSeverity muc = severity == null ? AuditSeverity.INFO : AuditSeverity.valueOf(severity);
        repo.save(new AuditLog(tenantId, ActorType.SYSTEM, null, action, entityType, entityId, muc)
                .withData(null, plain(afterData)));
    }

    private static void requireTransaction() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()) {
            throw new IllegalStateException("AuditLogWriter phải gọi bên trong @Transactional.");
        }
    }

    /**
     * Chuyển qua {@link ObjectMapper} của Spring TRƯỚC khi giao cho Hibernate: Hibernate ghi jsonb bằng bộ
     * Jackson riêng, cấu hình khác — ngày giờ có thể ra số thay vì chuỗi ISO. Đi qua mapper của Spring thì
     * giá trị đã là chuỗi/số/bool thuần, dạng JSON giống hệt bản ghi cũ. Giữ nguyên giá trị {@code null}.
     */
    private Map<String, Object> plain(Map<String, ?> data) {
        return data == null ? null : json.convertValue(data, MAP);
    }
}
