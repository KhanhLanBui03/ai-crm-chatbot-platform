package com.thesis.crm.engagement.inbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.enums.ConversationStatus;
import com.thesis.crm.common.enums.SenderType;
import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import com.thesis.crm.engagement.entity.Message;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import jakarta.persistence.Query;
import jakarta.persistence.TypedQuery;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * Truy cập dữ liệu hộp thư (UC012/UC013) qua Entity {@code Conversation}, {@link Message}, {@code Channel}
 * (JPA). Mọi truy vấn lọc {@code tenantId} tường minh — lớp thứ hai cạnh RLS. Gọi trong transaction đã
 * {@code TenantTransactionScope.apply()}.
 *
 * <p><b>Đọc bằng phép chiếu, ghi bằng {@code UPDATE} JPQL — không nạp Entity hội thoại rồi sửa.</b> Hội
 * thoại có cột do trigger cập nhật mỗi khi có tin mới (số tin, tin cuối…), và widget/phân công vẫn sửa
 * bảng này bằng SQL ở nơi khác. Một Entity đã nạp vào bộ nhớ sẽ giữ bản CŨ: đọc lại trả số sai, còn sửa
 * rồi so với bản cũ có thể bỏ sót thay đổi. Phép chiếu và {@code UPDATE} đi thẳng xuống CSDL nên luôn đúng.
 *
 * <p>Giữ nguyên chữ ký các hàm từ bản SQL tay, nên {@code InboxService} không phải đổi.
 */
@Repository
public class InboxRepository {

    /** Dòng hội thoại thô — service tự gắn thẻ và đổi sang DTO. */
    public record ConvRow(
            UUID id, UUID contactId, String contactName, String channelType, String status,
            UUID assignedUserId, String assignedUserName, String priority, Instant lastMessageAt,
            String preview, int messageCount, int unreadCount, Instant startedAt,
            Instant firstAgentResponseAt, Instant resolvedAt, String closedReason) {}

    public record MsgRow(
            UUID id, String senderType, UUID senderUserId, String senderName, String content,
            String contentType, String deliveryStatus, String attachmentsJson, UUID aiInteractionId,
            String metadataJson, Instant createdAt, Instant sentAt) {}

    public record Filter(String scope, UUID currentUserId, List<String> statuses, String channelType,
                         UUID tagId, String keyword, int page, int size) {}

    private static final String CONV_FROM = """
            FROM Conversation c
            JOIN Channel ch ON ch.id = c.channelId AND ch.tenantId = c.tenantId
            LEFT JOIN Contact k ON k.id = c.contactId AND k.tenantId = c.tenantId
            LEFT JOIN User u ON u.id = c.assignedUserId AND u.tenantId = c.tenantId
            """;

    private static final String CONV_SELECT = """
            SELECT c.id, c.contactId, coalesce(k.fullName, 'Khách chưa có tên'), ch.type, c.status,
                   c.assignedUserId, u.fullName, c.priority, coalesce(c.lastMessageAt, c.createdAt),
                   c.lastMessagePreview, c.messageCount, c.unreadCount, c.createdAt,
                   c.firstAgentResponseAt, c.resolvedAt, c.closedReason
            """ + CONV_FROM;

    private static final String MSG_SELECT = """
            SELECT m, u.fullName
            FROM Message m
            LEFT JOIN User u ON u.id = m.senderUserId AND u.tenantId = m.tenantId
            """;

    private final EntityManager em;
    private final ObjectMapper json;

    public InboxRepository(EntityManager em, ObjectMapper json) {
        this.em = em;
        this.json = json;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    public List<ConvRow> search(UUID tenantId, Filter f) {
        Map<String, Object> p = new HashMap<>();
        TypedQuery<Object[]> q = em.createQuery(CONV_SELECT + where(tenantId, f, p)
                        + " ORDER BY coalesce(c.lastMessageAt, c.createdAt) DESC, c.id", Object[].class)
                .setFirstResult(f.page() * f.size())
                .setMaxResults(f.size());
        p.forEach(q::setParameter);
        return q.getResultStream().map(InboxRepository::mapConv).toList();
    }

    public long count(UUID tenantId, Filter f) {
        Map<String, Object> p = new HashMap<>();
        TypedQuery<Long> q = em.createQuery("""
                SELECT count(c) FROM Conversation c
                JOIN Channel ch ON ch.id = c.channelId AND ch.tenantId = c.tenantId
                LEFT JOIN Contact k ON k.id = c.contactId AND k.tenantId = c.tenantId
                """ + where(tenantId, f, p), Long.class);
        p.forEach(q::setParameter);
        return q.getSingleResult();
    }

    /** Điều kiện lọc. {@code mine} dùng userId trong JWT do service truyền — không nhận từ phía gọi. */
    private static String where(UUID tenantId, Filter f, Map<String, Object> p) {
        StringBuilder w = new StringBuilder(" WHERE c.tenantId = :t");
        p.put("t", tenantId);
        if ("mine".equals(f.scope())) {
            w.append(" AND c.assignedUserId = :me");
            p.put("me", f.currentUserId());
        } else if ("unassigned".equals(f.scope())) {
            w.append(" AND c.assignedUserId IS NULL");
        }
        if (f.statuses() != null && !f.statuses().isEmpty()) {
            w.append(" AND c.status IN :st");
            p.put("st", f.statuses().stream().map(ConversationStatus::valueOf).toList());
        }
        if (f.channelType() != null) {
            w.append(" AND ch.type = :ct");
            p.put("ct", f.channelType());
        }
        if (f.tagId() != null) {
            w.append(" AND EXISTS (SELECT 1 FROM ContactTag x")
                    .append(" WHERE x.tenantId = c.tenantId AND x.contactId = c.contactId AND x.tagId = :tag)");
            p.put("tag", f.tagId());
        }
        if (f.keyword() != null && !f.keyword().isBlank()) {
            // Không dấu, giống ô tìm của danh bạ (engagement.fold_vi, V124)
            // function() không biết kiểu trả về → ép về String thì LIKE mới chấp nhận
            w.append(" AND cast(function('engagement.fold_vi',")
                    .append(" concat(coalesce(k.fullName, ''), ' ', coalesce(c.lastMessagePreview, ''))) as String)")
                    .append(" LIKE concat('%', cast(function('engagement.fold_vi', :kw) as String), '%')");
            p.put("kw", f.keyword().strip());
        }
        return w.toString();
    }

    public Optional<ConvRow> find(UUID tenantId, UUID conversationId) {
        return em.createQuery(CONV_SELECT + " WHERE c.tenantId = :t AND c.id = :c", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("c", conversationId)
                .getResultStream().findFirst().map(InboxRepository::mapConv);
    }

    /** Khoá dòng hội thoại: hai nhân viên cùng bấm "Nhận" / cùng gửi tin đầu thì một người thắng. */
    public Optional<ConvRow> lock(UUID tenantId, UUID conversationId) {
        em.createQuery("SELECT c FROM Conversation c WHERE c.tenantId = :t AND c.id = :c")
                .setParameter("t", tenantId)
                .setParameter("c", conversationId)
                .setLockMode(LockModeType.PESSIMISTIC_WRITE)
                .getResultList();
        return find(tenantId, conversationId);
    }

    /** Thẻ của nhiều khách một lần — tránh N+1 khi dựng trang hộp thư. */
    public Map<UUID, List<TagDto>> tagsOf(UUID tenantId, Collection<UUID> contactIds) {
        Map<UUID, List<TagDto>> out = new HashMap<>();
        if (contactIds.isEmpty()) {
            return out;
        }
        em.createQuery("""
                SELECT ct.contactId, t.id, t.name, t.color, t.usageCount
                FROM ContactTag ct
                JOIN Tag t ON t.id = ct.tagId AND t.tenantId = ct.tenantId
                WHERE ct.tenantId = :t AND ct.contactId IN :ids
                ORDER BY t.name""", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("ids", contactIds)
                .getResultStream()
                .forEach(r -> out.computeIfAbsent((UUID) r[0], k -> new ArrayList<>())
                        .add(new TagDto((UUID) r[1], (String) r[2], (String) r[3], ((Number) r[4]).intValue())));
        return out;
    }

    /**
     * Trang tin mới nhất (lấy {@code limit + 1} để biết còn tin cũ hơn không), trả theo thời gian
     * TĂNG dần ở service. Con trỏ là {@code sent_at} — thứ tự hiển thị của hội thoại.
     */
    public List<MsgRow> messages(UUID tenantId, UUID conversationId, Instant before, int limitPlusOne) {
        TypedQuery<Object[]> q = em.createQuery(MSG_SELECT
                        + " WHERE m.tenantId = :t AND m.conversationId = :c"
                        + (before != null ? " AND m.sentAt < :before" : "")
                        + " ORDER BY m.sentAt DESC, m.id DESC", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("c", conversationId)
                .setMaxResults(limitPlusOne);
        if (before != null) {
            q.setParameter("before", before);
        }
        return q.getResultStream().map(this::mapMsg).toList();
    }

    /**
     * Hội thoại bị chuyển cho người VÌ HẾT HẠN MỨC và hạn mức hội thoại của thuê bao hiện hành vẫn
     * đang hết — trả lại cho AI lúc này là lách hạn mức (widget chỉ kiểm hạn mức khi mở hội thoại mới).
     */
    public boolean blockedByQuota(UUID tenantId, UUID conversationId) {
        List<String> lyDo = em.createQuery(
                        "SELECT c.handoverReason FROM Conversation c WHERE c.tenantId = :t AND c.id = :c", String.class)
                .setParameter("t", tenantId)
                .setParameter("c", conversationId)
                .getResultList();
        if (lyDo.isEmpty() || !"QUOTA_EXCEEDED".equals(lyDo.get(0))) {
            return false;
        }
        return em.createQuery("""
                SELECT count(u) FROM UsageRecord u, TenantSubscription s
                WHERE s.id = u.subscriptionId AND s.tenantId = u.tenantId AND u.tenantId = :t
                  AND u.metric = 'CONVERSATION' AND s.status IN ('TRIALING', 'ACTIVE', 'PAST_DUE')
                  AND u.usedValue >= u.quotaValue""", Long.class)
                .setParameter("t", tenantId)
                .getSingleResult() > 0;
    }

    /** Người dùng còn hoạt động của doanh nghiệp — đích hợp lệ khi phân công. */
    public Optional<String> activeUserName(UUID tenantId, UUID userId) {
        return em.createQuery(
                        "SELECT u.fullName FROM User u WHERE u.tenantId = :t AND u.id = :u AND u.status = 'ACTIVE'",
                        String.class)
                .setParameter("t", tenantId)
                .setParameter("u", userId)
                .getResultStream().findFirst();
    }

    // ── ghi ─────────────────────────────────────────────────────────────────────

    /**
     * Tin nhân viên/hệ thống gửi đi. {@code sent_at} lấy giờ thật lúc ghi (như {@code clock_timestamp()}
     * trước đây), không phải mốc đầu transaction — hai tin trong cùng một request vẫn đúng thứ tự.
     */
    public MsgRow insertMessage(UUID tenantId, UUID conversationId, String senderType, UUID senderUserId,
                                String content, String deliveryStatus) {
        Message m = new Message(tenantId, conversationId, SenderType.valueOf(senderType), senderUserId,
                "OUTBOUND", content);
        m.setDeliveryStatus(deliveryStatus);
        m.setSentAt(Instant.now());
        em.persist(m);
        em.flush(); // trigger cộng số tin của hội thoại chạy ngay tại đây
        return em.createQuery(MSG_SELECT + " WHERE m.tenantId = :t AND m.id = :id", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("id", m.getId())
                .getResultStream().findFirst().map(this::mapMsg).orElseThrow();
    }

    /** Giao cho một nhân viên → AGENT_HANDLING (AI ngừng tự trả lời). */
    public void assign(UUID tenantId, UUID conversationId, UUID userId) {
        update("""
                UPDATE Conversation c
                SET c.assignedUserId = :u, c.assignedAt = current_timestamp, c.status = :st,
                    c.queuedAt = NULL, c.priority = 'NORMAL'
                WHERE c.tenantId = :t AND c.id = :c""", tenantId, conversationId)
                .setParameter("u", userId)
                .setParameter("st", ConversationStatus.AGENT_HANDLING)
                .executeUpdate();
    }

    /** Trả lại cho AI: bỏ người phụ trách. handover_at/reason giữ làm lịch sử (ck_conv_handover). */
    public void returnToBot(UUID tenantId, UUID conversationId) {
        update("""
                UPDATE Conversation c
                SET c.status = :st, c.assignedUserId = NULL, c.assignedAt = NULL, c.queuedAt = NULL,
                    c.priority = 'NORMAL'
                WHERE c.tenantId = :t AND c.id = :c""", tenantId, conversationId)
                .setParameter("st", ConversationStatus.BOT_HANDLING)
                .executeUpdate();
    }

    /** Nhân viên chủ động lấy hội thoại khỏi AI → hàng chờ nhân viên. */
    public void handoffToAgent(UUID tenantId, UUID conversationId, String reason) {
        update("""
                UPDATE Conversation c
                SET c.status = :st, c.handoverAt = current_timestamp, c.handoverReason = :r,
                    c.queuedAt = current_timestamp
                WHERE c.tenantId = :t AND c.id = :c""", tenantId, conversationId)
                .setParameter("st", ConversationStatus.PENDING_AGENT)
                .setParameter("r", reason)
                .executeUpdate();
    }

    public void close(UUID tenantId, UUID conversationId, String status, String reason) {
        ConversationStatus st = ConversationStatus.valueOf(status);
        update("""
                UPDATE Conversation c
                SET c.status = :st, c.closedReason = :r,
                    c.resolvedAt = CASE WHEN :resolved = true THEN current_timestamp ELSE c.resolvedAt END
                WHERE c.tenantId = :t AND c.id = :c""", tenantId, conversationId)
                .setParameter("st", st)
                .setParameter("r", reason)
                .setParameter("resolved", st == ConversationStatus.RESOLVED)
                .executeUpdate();
    }

    public void markRead(UUID tenantId, UUID conversationId) {
        update("UPDATE Conversation c SET c.unreadCount = 0 WHERE c.tenantId = :t AND c.id = :c",
                tenantId, conversationId)
                .executeUpdate();
    }

    // ── ánh xạ ──────────────────────────────────────────────────────────────────

    /** {@code updated_at} do trigger {@code trg_touch_updated_at} đặt — các câu UPDATE không cần ghi. */
    private Query update(String jpql, UUID tenantId, UUID conversationId) {
        return em.createQuery(jpql)
                .setParameter("t", tenantId)
                .setParameter("c", conversationId);
    }

    private static ConvRow mapConv(Object[] r) {
        return new ConvRow((UUID) r[0], (UUID) r[1], (String) r[2], (String) r[3],
                ((ConversationStatus) r[4]).name(), (UUID) r[5], (String) r[6], (String) r[7], (Instant) r[8],
                (String) r[9], (Integer) r[10], (Integer) r[11], (Instant) r[12], (Instant) r[13],
                (Instant) r[14], (String) r[15]);
    }

    private MsgRow mapMsg(Object[] r) {
        Message m = (Message) r[0];
        return new MsgRow(m.getId(), m.getSenderType().name(), m.getSenderUserId(), (String) r[1], m.getContent(),
                m.getContentType(), m.getDeliveryStatus(), toJson(m.getAttachments()), m.getAiInteractionId(),
                toJson(m.getMetadata()), m.getCreatedAt(), m.getSentAt());
    }

    /** Service đọc lại hai cột JSON bằng {@code readJson} — giữ dạng chuỗi như bản SQL ({@code ::text}). */
    private String toJson(Object value) {
        try {
            return json.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Không chuyển được JSON của tin nhắn", e);
        }
    }
}
