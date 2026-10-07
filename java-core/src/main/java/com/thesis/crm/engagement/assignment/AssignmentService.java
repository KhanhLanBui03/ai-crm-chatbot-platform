package com.thesis.crm.engagement.assignment;

import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.engagement.assignment.AssignmentRepository.Assignee;
import com.thesis.crm.engagement.assignment.AssignmentRepository.HandoffEventRow;
import com.thesis.crm.engagement.assignment.AssignmentRepository.QueueStatus;
import com.thesis.crm.engagement.inbox.InboxRepository;
import com.thesis.crm.sales.activity.ActivityService;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * UC014 bước 3, 6 và UC015 2b — dùng CHUNG cho widget (AI chuyển giao) và hộp thư (nhân viên thao tác).
 *
 * <p>Mọi phương thức chạy TRONG transaction của bên gọi (đã {@code TenantTransactionScope.apply()}):
 * chuyển giao, ghi sự kiện và giao người phải cùng thành công hoặc cùng huỷ.
 */
@Service
public class AssignmentService {

    /** Ngưỡng "chờ quá lâu" — dùng chung cho job quá hạn và thanh cảnh báo của quản trị. */
    public static final int OVERDUE_MINUTES = 5;

    /** Hết hạn mức / AI lỗi không phải lỗi chất lượng của tác tử AI (UC014 2.1–2.2). */
    private static final Set<String> NOT_AI_FAULT = Set.of("QUOTA_EXCEEDED", "LLM_ERROR");

    private final AssignmentRepository repo;
    private final InboxRepository inbox;
    private final AuditLogWriter audit;
    private final ActivityService activities;

    public AssignmentService(AssignmentRepository repo, InboxRepository inbox, AuditLogWriter audit,
                             ActivityService activities) {
        this.repo = repo;
        this.inbox = inbox;
        this.audit = audit;
        this.activities = activities;
    }

    public void touchPresence(UUID tenantId, UUID userId) {
        requireTx();
        repo.touchPresence(tenantId, userId);
    }

    public boolean isOnline(UUID tenantId, UUID userId) {
        return repo.isOnline(tenantId, userId);
    }

    /**
     * Ghi một lần chuyển giao. {@code countsAgainstAiQuality} do máy chủ quyết — chỉ chuyển từ AI sang
     * người vì lý do thuộc về AI mới tính (hợp đồng {@code SuKienChuyenGiao}).
     */
    public HandoffEventRow recordHandoff(UUID tenantId, UUID conversationId, String direction, String reason,
                                         String triggeredBy, UUID actorUserId) {
        requireTx();
        boolean counts = "BOT_TO_AGENT".equals(direction) && !NOT_AI_FAULT.contains(reason);
        return repo.insertEvent(tenantId, conversationId, direction, reason, triggeredBy, actorUserId, counts);
    }

    /** Có người nhận hội thoại (tự nhận, được giao, tự động) → đóng sự kiện chờ đang mở. */
    public void accepted(UUID tenantId, UUID conversationId, UUID userId) {
        requireTx();
        acceptAndLog(tenantId, conversationId, userId);
    }

    /**
     * Đóng sự kiện chuyển giao đang chờ; nếu THẬT SỰ có sự kiện vừa được nhận (AI → nhân viên) thì ghi
     * đúng một hoạt động AUTO cho khách (UC035). Nhận lại hội thoại không qua AI thì không ghi gì.
     */
    private void acceptAndLog(UUID tenantId, UUID conversationId, UUID userId) {
        repo.acceptOpenEvent(tenantId, conversationId, userId)
                .ifPresent(reason -> activities.recordHandoffAccepted(tenantId, conversationId, userId, reason));
    }

    /**
     * UC014 b6 / UC015 2b — giao cho người phù hợp theo chế độ của doanh nghiệp. Rỗng = để hàng chờ chung
     * (chế độ thủ công, hoặc không ai đang trực).
     */
    public Optional<UUID> autoAssign(UUID tenantId, UUID conversationId, UUID excludeUserId) {
        requireTx();
        String mode = repo.assignmentMode(tenantId);
        if ("MANUAL".equals(mode)) {
            return Optional.empty();
        }
        repo.lockTenantAssignment(tenantId);
        Optional<UUID> picked = repo.pickCandidate(tenantId, mode, excludeUserId);
        picked.ifPresent(userId -> {
            inbox.assign(tenantId, conversationId, userId);
            acceptAndLog(tenantId, conversationId, userId);
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("assigneeUserId", userId.toString());
            data.put("via", "AUTO");
            data.put("mode", mode);
            audit.recordSystemAction(tenantId, "CONVERSATION_ASSIGNED", "CONVERSATION", conversationId, "INFO", data);
        });
        return picked;
    }

    public Optional<HandoffEventRow> event(UUID tenantId, UUID eventId) {
        return repo.event(tenantId, eventId);
    }

    public List<Assignee> assignees(UUID tenantId) {
        return repo.assignees(tenantId);
    }

    public QueueStatus queueStatus(UUID tenantId) {
        return repo.queueStatus(tenantId, OVERDUE_MINUTES);
    }

    /** Gỡ người phụ trách, đưa về hàng chờ (UC015 1a, 6.2). */
    public void unassign(UUID tenantId, UUID conversationId) {
        requireTx();
        repo.unassign(tenantId, conversationId);
    }

    private static void requireTx() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()) {
            throw new IllegalStateException("AssignmentService phải gọi bên trong transaction đã đặt tenant.");
        }
    }
}
