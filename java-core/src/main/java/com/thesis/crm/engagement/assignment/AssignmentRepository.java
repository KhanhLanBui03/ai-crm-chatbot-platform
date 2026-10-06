package com.thesis.crm.engagement.assignment;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * SQL của UC014/UC015: trạng thái trực tuyến, chọn người nhận, sự kiện chuyển giao, hàng chờ quá hạn.
 * Mọi câu có {@code tenant_id = :t} tường minh cạnh RLS; gọi trong transaction đã đặt tenant.
 */
@Repository
public class AssignmentRepository {

    /** "Đang trực" = có hoạt động trên Hộp thư trong khoảng này. */
    static final String ONLINE_WINDOW = "interval '2 minutes'";

    public record Assignee(UUID userId, String fullName, String role, boolean online, int openCount) {}

    public record HandoffEventRow(UUID id, String direction, String reason, String triggeredBy,
                                  boolean countsAgainstAiQuality, UUID toUserId, Instant queuedAt,
                                  Instant acceptedAt, Instant occurredAt) {}

    public record QueueStatus(int waitingTotal, int waitingOverdue, int onlineAgents) {}

    public record Overdue(UUID conversationId, String priority, Instant since, UUID assignedUserId) {}

    private final NamedParameterJdbcTemplate jdbc;

    public AssignmentRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── trực tuyến ──────────────────────────────────────────────────────────────

    /** Ghi tối đa MỘT lần mỗi phút dù Hộp thư hỏi máy chủ mỗi 5 giây. */
    public void touchPresence(UUID tenantId, UUID userId) {
        jdbc.update("""
                INSERT INTO platform.user_presence (user_id, tenant_id, last_active_at)
                VALUES (:u, :t, now())
                ON CONFLICT (user_id) DO UPDATE SET last_active_at = now()
                WHERE platform.user_presence.last_active_at < now() - interval '1 minute'
                """, new MapSqlParameterSource("t", tenantId).addValue("u", userId));
    }

    public boolean isOnline(UUID tenantId, UUID userId) {
        Boolean b = jdbc.queryForObject("SELECT EXISTS (SELECT 1 FROM platform.user_presence "
                        + "WHERE tenant_id = :t AND user_id = :u AND last_active_at > now() - " + ONLINE_WINDOW + ")",
                new MapSqlParameterSource("t", tenantId).addValue("u", userId), Boolean.class);
        return Boolean.TRUE.equals(b);
    }

    // ── chọn người nhận ─────────────────────────────────────────────────────────

    public String assignmentMode(UUID tenantId) {
        return jdbc.queryForObject("SELECT assignment_mode FROM platform.tenants WHERE id = :t",
                new MapSqlParameterSource("t", tenantId), String.class);
    }

    /** Khoá theo doanh nghiệp: hai chuyển giao cùng lúc không cùng chọn một "người ít việc nhất". */
    public void lockTenantAssignment(UUID tenantId) {
        jdbc.query("SELECT pg_advisory_xact_lock(hashtext('assign:' || CAST(:t AS text)))",
                new MapSqlParameterSource("t", tenantId), rs -> { });
    }

    /**
     * Người nhận phù hợp: đang trực, ACTIVE, vai trò AGENT trước rồi mới tới TENANT_ADMIN, trừ
     * {@code excludeUserId}. LEAST_BUSY: ít hội thoại đang xử lý nhất; ROUND_ROBIN: được giao lâu nhất.
     */
    public Optional<UUID> pickCandidate(UUID tenantId, String mode, UUID excludeUserId) {
        String order = "ROUND_ROBIN".equals(mode)
                ? "last_assigned ASC NULLS FIRST, open_count ASC"
                : "open_count ASC, last_assigned ASC NULLS FIRST";
        return jdbc.query(CANDIDATES + """
                 WHERE online AND (CAST(:ex AS uuid) IS NULL OR user_id <> CAST(:ex AS uuid))
                 ORDER BY (role = 'AGENT') DESC,
                """ + order + ", user_id LIMIT 1",
                new MapSqlParameterSource("t", tenantId).addValue("ex", excludeUserId),
                (rs, i) -> rs.getObject("user_id", UUID.class)).stream().findFirst();
    }

    /** Mọi người nhận được hội thoại của doanh nghiệp — ô "Giao cho…" (UC015 b3). */
    public List<Assignee> assignees(UUID tenantId) {
        return jdbc.query(CANDIDATES + " ORDER BY online DESC, (role = 'AGENT') DESC, full_name",
                new MapSqlParameterSource("t", tenantId),
                (rs, i) -> new Assignee(rs.getObject("user_id", UUID.class), rs.getString("full_name"),
                        rs.getString("role"), rs.getBoolean("online"), rs.getInt("open_count")));
    }

    private static final String CANDIDATES = """
            SELECT * FROM (
                SELECT u.id AS user_id, u.full_name, r.code AS role,
                       coalesce(p.last_active_at > now() - """ + ONLINE_WINDOW + """
            , false) AS online,
                       (SELECT count(*) FROM engagement.conversations x
                         WHERE x.tenant_id = u.tenant_id AND x.assigned_user_id = u.id
                           AND x.status = 'AGENT_HANDLING') AS open_count,
                       GREATEST(
                         (SELECT max(x.assigned_at) FROM engagement.conversations x
                           WHERE x.tenant_id = u.tenant_id AND x.assigned_user_id = u.id),
                         (SELECT max(e.accepted_at) FROM engagement.handoff_events e
                           WHERE e.tenant_id = u.tenant_id AND e.to_user_id = u.id)) AS last_assigned
                FROM platform.users u
                JOIN platform.user_roles ur ON ur.user_id = u.id AND ur.tenant_id = u.tenant_id
                JOIN platform.roles r ON r.id = ur.role_id AND r.code IN ('AGENT', 'TENANT_ADMIN')
                LEFT JOIN platform.user_presence p ON p.user_id = u.id AND p.tenant_id = u.tenant_id
                WHERE u.tenant_id = :t AND u.status = 'ACTIVE' AND u.deleted_at IS NULL
            ) cand
            """;

    // ── sự kiện chuyển giao ─────────────────────────────────────────────────────

    public HandoffEventRow insertEvent(UUID tenantId, UUID conversationId, String direction, String reason,
                                       String triggeredBy, UUID actorUserId, boolean countsAgainstAi) {
        return jdbc.queryForObject("""
                INSERT INTO engagement.handoff_events
                    (tenant_id, conversation_id, direction, reason, triggered_by, actor_user_id,
                     counts_against_ai_quality, queued_at)
                VALUES (:t, :c, :d, :r, :by, :actor, :counts, CASE WHEN :d = 'BOT_TO_AGENT' THEN now() END)
                RETURNING id, direction, reason, triggered_by, counts_against_ai_quality, to_user_id,
                          queued_at, accepted_at, occurred_at
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("d", direction)
                        .addValue("r", reason).addValue("by", triggeredBy).addValue("actor", actorUserId)
                        .addValue("counts", countsAgainstAi),
                (rs, i) -> new HandoffEventRow(rs.getObject("id", UUID.class), rs.getString("direction"),
                        rs.getString("reason"), rs.getString("triggered_by"),
                        rs.getBoolean("counts_against_ai_quality"), rs.getObject("to_user_id", UUID.class),
                        ts(rs.getTimestamp("queued_at")), ts(rs.getTimestamp("accepted_at")),
                        ts(rs.getTimestamp("occurred_at"))));
    }

    /** Có người nhận → đóng sự kiện BOT_TO_AGENT còn mở gần nhất (đo thời gian chờ nhân viên). */
    public void acceptOpenEvent(UUID tenantId, UUID conversationId, UUID userId) {
        jdbc.update("""
                UPDATE engagement.handoff_events SET to_user_id = :u, accepted_at = now()
                WHERE id = (SELECT id FROM engagement.handoff_events
                            WHERE tenant_id = :t AND conversation_id = :c AND direction = 'BOT_TO_AGENT'
                              AND accepted_at IS NULL
                            ORDER BY occurred_at DESC LIMIT 1)
                """, new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("u", userId));
    }

    public Optional<HandoffEventRow> event(UUID tenantId, UUID eventId) {
        return jdbc.query("""
                SELECT id, direction, reason, triggered_by, counts_against_ai_quality, to_user_id,
                       queued_at, accepted_at, occurred_at
                FROM engagement.handoff_events WHERE tenant_id = :t AND id = :id
                """, new MapSqlParameterSource("t", tenantId).addValue("id", eventId),
                (rs, i) -> new HandoffEventRow(rs.getObject("id", UUID.class), rs.getString("direction"),
                        rs.getString("reason"), rs.getString("triggered_by"),
                        rs.getBoolean("counts_against_ai_quality"), rs.getObject("to_user_id", UUID.class),
                        ts(rs.getTimestamp("queued_at")), ts(rs.getTimestamp("accepted_at")),
                        ts(rs.getTimestamp("occurred_at")))).stream().findFirst();
    }

    // ── hàng chờ ────────────────────────────────────────────────────────────────

    /** Gỡ người phụ trách, về hàng chờ. handover_at/reason giữ nguyên (ck_conv_handover). */
    public void unassign(UUID tenantId, UUID conversationId) {
        jdbc.update("""
                UPDATE engagement.conversations
                SET status = 'PENDING_AGENT', assigned_user_id = NULL, assigned_at = NULL, updated_at = now()
                WHERE tenant_id = :t AND id = :c
                """, new MapSqlParameterSource("t", tenantId).addValue("c", conversationId));
    }

    public QueueStatus queueStatus(UUID tenantId, int overdueMinutes) {
        return jdbc.queryForObject("""
                SELECT
                  (SELECT count(*) FROM engagement.conversations
                    WHERE tenant_id = :t AND status = 'PENDING_AGENT' AND assigned_user_id IS NULL) AS waiting,
                  (SELECT count(*) FROM engagement.conversations
                    WHERE tenant_id = :t AND status = 'PENDING_AGENT' AND assigned_user_id IS NULL
                      AND coalesce(handover_at, created_at) < now() - make_interval(mins => :m)) AS overdue,
                  (SELECT count(*) FROM platform.user_presence p
                     JOIN platform.users u ON u.id = p.user_id AND u.tenant_id = p.tenant_id
                    WHERE p.tenant_id = :t AND u.status = 'ACTIVE'
                      AND p.last_active_at > now() - """ + ONLINE_WINDOW + """
                ) AS online
                """, new MapSqlParameterSource("t", tenantId).addValue("m", overdueMinutes),
                (rs, i) -> new QueueStatus(rs.getInt("waiting"), rs.getInt("overdue"), rs.getInt("online")));
    }

    public List<UUID> tenantsWithOverdue(int minutes) {
        return jdbc.queryForList("SELECT * FROM engagement.tenants_with_overdue_handoffs(:m)",
                new MapSqlParameterSource("m", minutes), UUID.class);
    }

    /** Chờ chưa ai nhận quá hạn — KHOÁ dòng, bỏ qua dòng người khác đang khoá (không chặn Hộp thư). */
    public List<Overdue> overdueWaiting(UUID tenantId, int minutes) {
        return jdbc.query("""
                SELECT id, priority, coalesce(handover_at, created_at) AS since, assigned_user_id
                FROM engagement.conversations
                WHERE tenant_id = :t AND status = 'PENDING_AGENT' AND assigned_user_id IS NULL
                  AND coalesce(handover_at, created_at) < now() - make_interval(mins => :m)
                FOR UPDATE SKIP LOCKED
                """, new MapSqlParameterSource("t", tenantId).addValue("m", minutes),
                (rs, i) -> new Overdue(rs.getObject("id", UUID.class), rs.getString("priority"),
                        ts(rs.getTimestamp("since")), null));
    }

    /**
     * Đã giao quá hạn mà người được giao CHƯA gửi tin nào kể từ lúc được giao VÀ đang ngoại tuyến
     * (UC015 6.2) — người đó có lẽ đã rời máy, khách đang chờ vô ích.
     */
    public List<Overdue> staleAssigned(UUID tenantId, int minutes) {
        return jdbc.query("""
                SELECT c.id, c.priority, c.assigned_at AS since, c.assigned_user_id
                FROM engagement.conversations c
                WHERE c.tenant_id = :t AND c.status = 'AGENT_HANDLING' AND c.assigned_user_id IS NOT NULL
                  AND c.assigned_at < now() - make_interval(mins => :m)
                  AND NOT EXISTS (SELECT 1 FROM engagement.messages m
                                  WHERE m.tenant_id = c.tenant_id AND m.conversation_id = c.id
                                    AND m.sender_type = 'AGENT' AND m.sender_user_id = c.assigned_user_id
                                    AND m.sent_at >= c.assigned_at)
                  AND NOT EXISTS (SELECT 1 FROM platform.user_presence p
                                  WHERE p.tenant_id = c.tenant_id AND p.user_id = c.assigned_user_id
                                    AND p.last_active_at > now() - """ + ONLINE_WINDOW + """
                )
                FOR UPDATE OF c SKIP LOCKED
                """, new MapSqlParameterSource("t", tenantId).addValue("m", minutes),
                (rs, i) -> new Overdue(rs.getObject("id", UUID.class), rs.getString("priority"),
                        ts(rs.getTimestamp("since")), rs.getObject("assigned_user_id", UUID.class)));
    }

    public void setPriority(UUID tenantId, UUID conversationId, String priority) {
        jdbc.update("UPDATE engagement.conversations SET priority = :p, updated_at = now() "
                        + "WHERE tenant_id = :t AND id = :c",
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("p", priority));
    }

    private static Instant ts(Timestamp t) {
        return t == null ? null : t.toInstant();
    }
}
