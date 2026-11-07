package com.thesis.crm.platform.audit;

import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.enums.AuditSeverity;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.audit.AuditLogDtos.AuditLogDto;
import com.thesis.crm.platform.entity.AuditLog;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.security.TenantTransactionScope;
import jakarta.persistence.EntityManager;
import jakarta.persistence.TypedQuery;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC040 — đọc nhật ký kiểm toán và "xem đầy đủ" dòng có dữ liệu cá nhân. Đọc qua Entity {@link AuditLog}
 * (JPQL), luôn lọc {@code tenantId} cùng RLS; chỉ quản trị viên doanh nghiệp.
 */
@Service
public class AuditLogService {

    /** Đặc tả UC040 luồng 6.2 + hợp đồng {@code minLength: 10} — "xem" hay "kiểm tra" không phải lý do. */
    static final int LY_DO_TOI_THIEU = 10;
    static final int CO_TRANG_TOI_DA = 100;

    private final EntityManager em;
    private final TenantTransactionScope scope;
    private final AuditLogWriter writer;

    public AuditLogService(EntityManager em, TenantTransactionScope scope, AuditLogWriter writer) {
        this.em = em;
        this.scope = scope;
        this.writer = writer;
    }

    public record Filter(String action, UUID actorId, AuditSeverity severity, String entityType, LocalDate from,
                         LocalDate to, int page, int size) {}

    @Transactional(readOnly = true)
    public PageResponse<AuditLogDto> list(UUID tenantId, boolean isAdmin, Filter f) {
        requireAdmin(isAdmin, "Chỉ quản trị viên doanh nghiệp được xem nhật ký kiểm toán.");
        scope.apply(tenantId);
        int size = Math.min(Math.max(f.size(), 1), CO_TRANG_TOI_DA);
        int page = Math.max(f.page(), 0);

        Map<String, Object> p = new HashMap<>();
        String where = where(tenantId, f, p);
        TypedQuery<AuditLog> q = em.createQuery(
                        "SELECT a FROM AuditLog a" + where + " ORDER BY a.createdAt DESC, a.id DESC", AuditLog.class)
                .setFirstResult(page * size)
                .setMaxResults(size);
        TypedQuery<Long> c = em.createQuery("SELECT count(a) FROM AuditLog a" + where, Long.class);
        p.forEach((k, v) -> {
            q.setParameter(k, v);
            c.setParameter(k, v);
        });
        return PageResponse.of(q.getResultStream().map(AuditLogService::masked).toList(), page, size,
                c.getSingleResult());
    }

    /**
     * Xem đầy đủ một dòng (UC040 bước 6–7): kiểm quyền → bắt lý do → giải mã → ghi thêm MỘT dòng nhật ký cho
     * chính lần xem. Dòng không có bản gốc mã hoá thì không có gì để mở — trả nguyên, không ghi thêm.
     */
    @Transactional
    public AuditLogDto reveal(UUID tenantId, UUID userId, boolean isAdmin, long logId, String reason) {
        requireAdmin(isAdmin, "Chỉ quản trị viên doanh nghiệp được xem đầy đủ dữ liệu cá nhân.");
        String lyDo = reason == null ? "" : reason.strip();
        if (lyDo.length() < LY_DO_TOI_THIEU) {
            throw new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "REASON_REQUIRED",
                    "Cần nêu lý do xem dữ liệu cá nhân (tối thiểu " + LY_DO_TOI_THIEU + " ký tự).");
        }
        scope.apply(tenantId);
        AuditLog log = em.createQuery("SELECT a FROM AuditLog a WHERE a.tenantId = :t AND a.id = :id", AuditLog.class)
                .setParameter("t", tenantId)
                .setParameter("id", logId)
                .getResultStream().findFirst()
                .orElseThrow(() -> new BusinessException(HttpStatus.NOT_FOUND, "NOT_FOUND",
                        "Không tìm thấy dòng nhật ký."));
        if (!log.isContainsPersonalData() || log.getPiiEncrypted() == null) {
            return masked(log);
        }
        Map<String, Object> goc = writer.decryptPersonalData(log);
        writer.recordReveal(tenantId, userId, log.getId(), lyDo);
        return dto(log, map(goc.get("before")), map(goc.get("after")), false);
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    private String where(UUID tenantId, Filter f, Map<String, Object> p) {
        StringBuilder w = new StringBuilder(" WHERE a.tenantId = :t");
        p.put("t", tenantId);
        if (f.action() != null && !f.action().isBlank()) {
            w.append(" AND a.action = :action");
            p.put("action", f.action().strip());
        }
        if (f.actorId() != null) {
            w.append(" AND a.actorUserId = :actor");
            p.put("actor", f.actorId());
        }
        if (f.severity() != null) {
            w.append(" AND a.severity = :severity");
            p.put("severity", f.severity());
        }
        if (f.entityType() != null && !f.entityType().isBlank()) {
            w.append(" AND a.entityType = :entityType");
            p.put("entityType", f.entityType().strip());
        }
        // Ngày lọc tính theo múi giờ của doanh nghiệp (hợp đồng TuNgay/DenNgay): [from 00:00, to+1 00:00)
        if (f.from() != null || f.to() != null) {
            ZoneId zone = zone(tenantId);
            if (f.from() != null) {
                w.append(" AND a.createdAt >= :from");
                p.put("from", f.from().atStartOfDay(zone).toInstant());
            }
            if (f.to() != null) {
                w.append(" AND a.createdAt < :to");
                p.put("to", f.to().plusDays(1).atStartOfDay(zone).toInstant());
            }
        }
        return w.toString();
    }

    private ZoneId zone(UUID tenantId) {
        Tenant t = em.find(Tenant.class, tenantId);
        try {
            return ZoneId.of(t == null || t.getTimezone() == null ? "Asia/Ho_Chi_Minh" : t.getTimezone());
        } catch (Exception e) {
            return ZoneId.of("Asia/Ho_Chi_Minh");
        }
    }

    private static void requireAdmin(boolean isAdmin, String msg) {
        if (!isAdmin) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN", msg);
        }
    }

    /** Dạng mặc định: dòng có bản gốc mã hoá thì {@code before/after} là bản đã che. */
    private static AuditLogDto masked(AuditLog a) {
        return dto(a, a.getBeforeData(), a.getAfterData(), a.isContainsPersonalData() && a.getPiiEncrypted() != null);
    }

    private static AuditLogDto dto(AuditLog a, Map<String, Object> before, Map<String, Object> after, boolean masked) {
        return new AuditLogDto(a.getId(), a.getActorType(), a.getActorUserId(), a.getActorEmail(), a.getAction(),
                a.getEntityType(), a.getEntityId(), before, after, a.getReason(), a.getSeverity(),
                a.isContainsPersonalData(), masked, a.getIpAddress() == null ? null : a.getIpAddress().getHostAddress(),
                a.getRequestId(), a.getCreatedAt());
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object o) {
        return o instanceof Map<?, ?> m ? (Map<String, Object>) m : null;
    }
}
