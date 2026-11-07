package com.thesis.crm.platform.audit;

import com.thesis.crm.common.enums.ActorType;
import com.thesis.crm.common.enums.AuditSeverity;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/** Hợp đồng UC040 — {@code BanGhiKiemToan} trong {@code docs/openapi/dashboard-api.yaml}. */
public final class AuditLogDtos {

    private AuditLogDtos() {
    }

    /**
     * Một dòng nhật ký. {@code masked = true}: {@code before/after} đang là bản đã che, xem bản gốc phải gọi
     * {@code /reveal} kèm lý do.
     */
    public record AuditLogDto(
            long id, ActorType actorType, UUID actorId, String actorEmail, String action, String entityType,
            UUID entityId, Map<String, Object> before, Map<String, Object> after, String reason,
            AuditSeverity severity, boolean containsPersonalData, boolean masked, String ipAddress,
            String traceId, Instant occurredAt) {}

    public record RevealRequest(String reason) {}
}
