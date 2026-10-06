package com.thesis.crm.engagement.assignment;

import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.engagement.assignment.AssignmentRepository.Overdue;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Job quá hạn của hàng chờ — mỗi phút một lần:
 * <ul>
 *   <li><b>UC014 7.1</b>: chờ chưa ai nhận quá 5 phút → nâng ưu tiên (NORMAL→HIGH, quá 15 phút → URGENT),
 *       ghi cảnh báo, thử giao lại (có thể đã có người vào trực);</li>
 *   <li><b>UC015 6.2</b>: đã giao quá 5 phút mà người được giao chưa trả lời và đã ngoại tuyến → trả về
 *       hàng chờ rồi giao người khác.</li>
 * </ul>
 * Job không có ngữ cảnh tenant: lấy danh sách doanh nghiệp qua hàm SECURITY DEFINER (chỉ trả ID), rồi
 * mỗi doanh nghiệp một transaction có {@code app.tenant_id} — RLS vẫn áp như mọi truy vấn khác.
 */
@Component
public class HandoffWatchdog {

    private static final Logger log = LoggerFactory.getLogger(HandoffWatchdog.class);
    static final int URGENT_MINUTES = 15;

    private final AssignmentRepository repo;
    private final AssignmentService assignment;
    private final TenantTransactionScope scope;
    private final AuditLogWriter audit;
    private final TransactionTemplate tx;
    private final boolean enabled;

    public HandoffWatchdog(AssignmentRepository repo, AssignmentService assignment, TenantTransactionScope scope,
                           AuditLogWriter audit, TransactionTemplate tx,
                           @Value("${inbox.watchdog.enabled:true}") boolean enabled) {
        this.repo = repo;
        this.assignment = assignment;
        this.scope = scope;
        this.audit = audit;
        this.tx = tx;
        this.enabled = enabled;
    }

    @Scheduled(fixedDelay = 60_000, initialDelay = 60_000)
    public void scheduled() {
        if (!enabled) {
            return;   // test tắt lịch và gọi runOnce() trực tiếp để kết quả xác định
        }
        try {
            runOnce(Instant.now());
        } catch (RuntimeException e) {
            log.warn("Job quá hạn hàng chờ lỗi, lần sau chạy lại: {}", e.toString());
        }
    }

    public void runOnce(Instant now) {
        for (UUID tenantId : repo.tenantsWithOverdue(AssignmentService.OVERDUE_MINUTES)) {
            tx.executeWithoutResult(st -> {
                scope.apply(tenantId);
                escalate(tenantId, now);
                releaseStale(tenantId);
            });
        }
    }

    private void escalate(UUID tenantId, Instant now) {
        for (Overdue o : repo.overdueWaiting(tenantId, AssignmentService.OVERDUE_MINUTES)) {
            long minutes = Duration.between(o.since(), now).toMinutes();
            String target = minutes >= URGENT_MINUTES ? "URGENT" : "HIGH";
            if (rank(target) > rank(o.priority())) {
                repo.setPriority(tenantId, o.conversationId(), target);
                Map<String, Object> data = new LinkedHashMap<>();
                data.put("from", o.priority());
                data.put("to", target);
                data.put("waitingMinutes", minutes);
                audit.recordSystemAction(tenantId, "CONVERSATION_ESCALATED", "CONVERSATION", o.conversationId(),
                        "WARNING", data);
            }
            assignment.autoAssign(tenantId, o.conversationId(), null);
        }
    }

    private void releaseStale(UUID tenantId) {
        for (Overdue o : repo.staleAssigned(tenantId, AssignmentService.OVERDUE_MINUTES)) {
            assignment.unassign(tenantId, o.conversationId());
            audit.recordSystemAction(tenantId, "CONVERSATION_AUTO_RELEASED", "CONVERSATION", o.conversationId(),
                    "WARNING", Map.of("previousAssigneeUserId", o.assignedUserId().toString()));
            assignment.autoAssign(tenantId, o.conversationId(), o.assignedUserId());
        }
    }

    private static int rank(String p) {
        return switch (p == null ? "NORMAL" : p) {
            case "LOW" -> 0;
            case "HIGH" -> 2;
            case "URGENT" -> 3;
            default -> 1;
        };
    }
}
