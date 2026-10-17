package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.AuditLog;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * Ghi và đọc {@link AuditLog}. Bản ghi {@code @Immutable}: {@code save()} chỉ có tác dụng với bản ghi
 * MỚI; sửa rồi lưu lại một dòng cũ thì Hibernate lặng lẽ bỏ qua — đúng ý.
 */
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {

    List<AuditLog> findByTenantIdAndEntityTypeAndEntityIdOrderByCreatedAtAsc(
            UUID tenantId, String entityType, UUID entityId);
}
