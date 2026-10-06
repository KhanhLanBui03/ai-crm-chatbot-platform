package com.thesis.crm.engagement.inbox;

import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * SQL của hộp thư (UC012/UC013). Mọi câu có {@code tenant_id = :t} tường minh — lớp thứ hai cạnh
 * RLS, như các repository UC016/UC017. Gọi trong transaction đã {@code TenantTransactionScope.apply()}.
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

    private static final String CONV_SELECT = """
            SELECT c.id, c.contact_id, coalesce(k.full_name, 'Khách chưa có tên') AS contact_name,
                   ch.type AS channel_type, c.status, c.assigned_user_id, u.full_name AS assigned_name,
                   c.priority, coalesce(c.last_message_at, c.created_at) AS last_at,
                   c.last_message_preview, c.message_count, c.unread_count, c.created_at,
                   c.first_agent_response_at, c.resolved_at, c.closed_reason
            FROM engagement.conversations c
            JOIN engagement.channels ch ON ch.id = c.channel_id AND ch.tenant_id = c.tenant_id
            LEFT JOIN engagement.contacts k ON k.id = c.contact_id AND k.tenant_id = c.tenant_id
            LEFT JOIN platform.users u ON u.id = c.assigned_user_id AND u.tenant_id = c.tenant_id
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public InboxRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    public List<ConvRow> search(UUID tenantId, Filter f) {
        MapSqlParameterSource p = params(tenantId, f);
        p.addValue("lim", f.size()).addValue("off", (long) f.page() * f.size());
        return jdbc.query(CONV_SELECT + where(f, p)
                + " ORDER BY coalesce(c.last_message_at, c.created_at) DESC, c.id LIMIT :lim OFFSET :off",
                p, InboxRepository::mapConv);
    }

    public long count(UUID tenantId, Filter f) {
        MapSqlParameterSource p = params(tenantId, f);
        Long n = jdbc.queryForObject("""
                SELECT count(*) FROM engagement.conversations c
                JOIN engagement.channels ch ON ch.id = c.channel_id AND ch.tenant_id = c.tenant_id
                LEFT JOIN engagement.contacts k ON k.id = c.contact_id AND k.tenant_id = c.tenant_id
                """ + where(f, p), p, Long.class);
        return n == null ? 0 : n;
    }

    private static MapSqlParameterSource params(UUID tenantId, Filter f) {
        return new MapSqlParameterSource("t", tenantId);
    }

    /** Điều kiện lọc. {@code mine} dùng userId trong JWT do service truyền — không nhận từ phía gọi. */
    private static String where(Filter f, MapSqlParameterSource p) {
        StringBuilder w = new StringBuilder(" WHERE c.tenant_id = :t");
        if ("mine".equals(f.scope())) {
            w.append(" AND c.assigned_user_id = :me");
            p.addValue("me", f.currentUserId());
        } else if ("unassigned".equals(f.scope())) {
            w.append(" AND c.assigned_user_id IS NULL");
        }
        if (f.statuses() != null && !f.statuses().isEmpty()) {
            w.append(" AND c.status IN (:st)");
            p.addValue("st", f.statuses());
        }
        if (f.channelType() != null) {
            w.append(" AND ch.type = :ct");
            p.addValue("ct", f.channelType());
        }
        if (f.tagId() != null) {
            w.append(" ").append("""
                     AND EXISTS (SELECT 1 FROM engagement.contact_tags x
                                 WHERE x.tenant_id = c.tenant_id AND x.contact_id = c.contact_id AND x.tag_id = :tag)""");
            p.addValue("tag", f.tagId());
        }
        if (f.keyword() != null && !f.keyword().isBlank()) {
            // Không dấu, giống ô tìm của danh bạ (engagement.fold_vi, V124)
            w.append(" ").append("""
                     AND engagement.fold_vi(coalesce(k.full_name, '') || ' ' || coalesce(c.last_message_preview, ''))
                         LIKE '%' || engagement.fold_vi(:kw) || '%'""");
            p.addValue("kw", f.keyword().strip());
        }
        return w.toString();
    }

    public Optional<ConvRow> find(UUID tenantId, UUID conversationId) {
        return jdbc.query(CONV_SELECT + " WHERE c.tenant_id = :t AND c.id = :c",
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId), InboxRepository::mapConv)
                .stream().findFirst();
    }

    /** Khoá dòng hội thoại: hai nhân viên cùng bấm "Nhận" / cùng gửi tin đầu thì một người thắng. */
    public Optional<ConvRow> lock(UUID tenantId, UUID conversationId) {
        jdbc.query("SELECT 1 FROM engagement.conversations WHERE tenant_id = :t AND id = :c FOR UPDATE",
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId), rs -> { });
        return find(tenantId, conversationId);
    }

    /** Thẻ của nhiều khách một lần — tránh N+1 khi dựng trang hộp thư. */
    public Map<UUID, List<TagDto>> tagsOf(UUID tenantId, Collection<UUID> contactIds) {
        Map<UUID, List<TagDto>> out = new HashMap<>();
        if (contactIds.isEmpty()) {
            return out;
        }
        jdbc.query("""
                SELECT ct.contact_id, t.id, t.name, t.color, t.usage_count
                FROM engagement.contact_tags ct
                JOIN engagement.tags t ON t.id = ct.tag_id AND t.tenant_id = ct.tenant_id
                WHERE ct.tenant_id = :t AND ct.contact_id IN (:ids)
                ORDER BY t.name
                """,
                new MapSqlParameterSource("t", tenantId).addValue("ids", contactIds),
                rs -> {
                    out.computeIfAbsent(rs.getObject("contact_id", UUID.class), k -> new ArrayList<>())
                            .add(new TagDto(rs.getObject("id", UUID.class), rs.getString("name"),
                                    rs.getString("color"), rs.getInt("usage_count")));
                });
        return out;
    }

    /**
     * Trang tin mới nhất (lấy {@code limit + 1} để biết còn tin cũ hơn không), trả theo thời gian
     * TĂNG dần. Con trỏ là {@code sent_at} — thứ tự hiển thị của hội thoại.
     */
    public List<MsgRow> messages(UUID tenantId, UUID conversationId, Instant before, int limitPlusOne) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId).addValue("c", conversationId)
                .addValue("lim", limitPlusOne);
        String cond = "";
        if (before != null) {
            cond = " AND m.sent_at < :before";
            p.addValue("before", Timestamp.from(before));
        }
        return jdbc.query("""
                SELECT m.id, m.sender_type, m.sender_user_id, u.full_name AS sender_name, m.content,
                       m.content_type, m.delivery_status, m.attachments::text AS attachments,
                       m.ai_interaction_id, m.metadata::text AS metadata, m.created_at, m.sent_at
                FROM engagement.messages m
                LEFT JOIN platform.users u ON u.id = m.sender_user_id AND u.tenant_id = m.tenant_id
                WHERE m.tenant_id = :t AND m.conversation_id = :c""" + cond + """
                 ORDER BY m.sent_at DESC, m.id DESC LIMIT :lim
                """, p, InboxRepository::mapMsg);
    }

    /**
     * Hội thoại bị chuyển cho người VÌ HẾT HẠN MỨC và hạn mức hội thoại của thuê bao hiện hành vẫn
     * đang hết — trả lại cho AI lúc này là lách hạn mức (widget chỉ kiểm hạn mức khi mở hội thoại mới).
     */
    public boolean blockedByQuota(UUID tenantId, UUID conversationId) {
        Boolean b = jdbc.queryForObject("""
                SELECT c.handover_reason = 'QUOTA_EXCEEDED' AND EXISTS (
                         SELECT 1 FROM platform.usage_records u
                         JOIN platform.tenant_subscriptions s ON s.id = u.subscription_id AND s.tenant_id = u.tenant_id
                         WHERE u.tenant_id = c.tenant_id AND u.metric = 'CONVERSATION'
                           AND s.status IN ('TRIALING','ACTIVE','PAST_DUE') AND u.used_value >= u.quota_value)
                FROM engagement.conversations c WHERE c.tenant_id = :t AND c.id = :c
                """, new MapSqlParameterSource("t", tenantId).addValue("c", conversationId), Boolean.class);
        return Boolean.TRUE.equals(b);
    }

    /** Người dùng còn hoạt động của doanh nghiệp — đích hợp lệ khi phân công. */
    public Optional<String> activeUserName(UUID tenantId, UUID userId) {
        return jdbc.query("""
                SELECT full_name FROM platform.users WHERE tenant_id = :t AND id = :u AND status = 'ACTIVE'
                """, new MapSqlParameterSource("t", tenantId).addValue("u", userId), (rs, i) -> rs.getString(1))
                .stream().findFirst();
    }

    // ── ghi ─────────────────────────────────────────────────────────────────────

    public MsgRow insertMessage(UUID tenantId, UUID conversationId, String senderType, UUID senderUserId,
                                String content, String deliveryStatus) {
        UUID id = jdbc.queryForObject("""
                INSERT INTO engagement.messages
                    (tenant_id, conversation_id, sender_type, sender_user_id, direction, content,
                     delivery_status, sent_at)
                VALUES (:t, :c, :s, :u, 'OUTBOUND', :content, :d, clock_timestamp())
                RETURNING id
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("s", senderType)
                        .addValue("u", senderUserId).addValue("content", content).addValue("d", deliveryStatus),
                UUID.class);
        return jdbc.query("""
                SELECT m.id, m.sender_type, m.sender_user_id, u.full_name AS sender_name, m.content,
                       m.content_type, m.delivery_status, m.attachments::text AS attachments,
                       m.ai_interaction_id, m.metadata::text AS metadata, m.created_at, m.sent_at
                FROM engagement.messages m
                LEFT JOIN platform.users u ON u.id = m.sender_user_id AND u.tenant_id = m.tenant_id
                WHERE m.tenant_id = :t AND m.id = :id
                """, new MapSqlParameterSource("t", tenantId).addValue("id", id), InboxRepository::mapMsg).get(0);
    }

    /** Giao cho một nhân viên → AGENT_HANDLING (AI ngừng tự trả lời). */
    public void assign(UUID tenantId, UUID conversationId, UUID userId) {
        jdbc.update("""
                UPDATE engagement.conversations
                SET assigned_user_id = :u, assigned_at = now(), status = 'AGENT_HANDLING',
                    queued_at = NULL, priority = 'NORMAL', updated_at = now()
                WHERE tenant_id = :t AND id = :c
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("u", userId));
    }

    /** Trả lại cho AI: bỏ người phụ trách. handover_at/reason giữ làm lịch sử (ck_conv_handover). */
    public void returnToBot(UUID tenantId, UUID conversationId) {
        jdbc.update("""
                UPDATE engagement.conversations
                SET status = 'BOT_HANDLING', assigned_user_id = NULL, assigned_at = NULL, queued_at = NULL,
                    priority = 'NORMAL', updated_at = now()
                WHERE tenant_id = :t AND id = :c
                """, new MapSqlParameterSource("t", tenantId).addValue("c", conversationId));
    }

    /** Nhân viên chủ động lấy hội thoại khỏi AI → hàng chờ nhân viên. */
    public void handoffToAgent(UUID tenantId, UUID conversationId, String reason) {
        jdbc.update("""
                UPDATE engagement.conversations
                SET status = 'PENDING_AGENT', handover_at = now(), handover_reason = :r, queued_at = now(),
                    updated_at = now()
                WHERE tenant_id = :t AND id = :c
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("r", reason));
    }

    public void close(UUID tenantId, UUID conversationId, String status, String reason) {
        jdbc.update("""
                UPDATE engagement.conversations
                SET status = :s, closed_reason = :r,
                    resolved_at = CASE WHEN :s = 'RESOLVED' THEN now() ELSE resolved_at END,
                    updated_at = now()
                WHERE tenant_id = :t AND id = :c
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("s", status)
                        .addValue("r", reason));
    }

    public void markRead(UUID tenantId, UUID conversationId) {
        jdbc.update("UPDATE engagement.conversations SET unread_count = 0 WHERE tenant_id = :t AND id = :c",
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId));
    }

    // ── ánh xạ ──────────────────────────────────────────────────────────────────

    private static ConvRow mapConv(ResultSet rs, int i) throws SQLException {
        return new ConvRow(rs.getObject("id", UUID.class), rs.getObject("contact_id", UUID.class),
                rs.getString("contact_name"), rs.getString("channel_type"), rs.getString("status"),
                rs.getObject("assigned_user_id", UUID.class), rs.getString("assigned_name"),
                rs.getString("priority"), ts(rs, "last_at"), rs.getString("last_message_preview"),
                rs.getInt("message_count"), rs.getInt("unread_count"), ts(rs, "created_at"),
                ts(rs, "first_agent_response_at"), ts(rs, "resolved_at"), rs.getString("closed_reason"));
    }

    private static MsgRow mapMsg(ResultSet rs, int i) throws SQLException {
        return new MsgRow(rs.getObject("id", UUID.class), rs.getString("sender_type"),
                rs.getObject("sender_user_id", UUID.class), rs.getString("sender_name"), rs.getString("content"),
                rs.getString("content_type"), rs.getString("delivery_status"), rs.getString("attachments"),
                rs.getObject("ai_interaction_id", UUID.class), rs.getString("metadata"),
                ts(rs, "created_at"), ts(rs, "sent_at"));
    }

    private static Instant ts(ResultSet rs, String col) throws SQLException {
        Timestamp t = rs.getTimestamp(col);
        return t == null ? null : t.toInstant();
    }
}
