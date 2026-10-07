package com.thesis.crm.sales.activity;

import com.thesis.crm.sales.activity.ActivityDtos.ActivityDto;
import com.thesis.crm.sales.activity.ActivityDtos.TodoCount;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * SQL của UC035. Mọi câu có {@code tenant_id = :t} tường minh — lớp thứ hai cạnh RLS. Gọi trong
 * transaction đã {@code TenantTransactionScope.apply()}.
 *
 * <p>"Hôm nay" tính theo giờ Việt Nam — một định nghĩa cho cả danh sách lẫn số đỏ trên menu.
 */
@Repository
public class ActivityRepository {

    public record Filter(UUID contactId, UUID leadId, UUID dealId, String type, String remindStatus,
                         UUID mineUserId, String bucket, int page, int size) {}

    public record NewActivity(UUID contactId, UUID leadId, UUID dealId, UUID conversationId, String type,
                              String subject, String content, String outcome, String source, UUID performedBy,
                              Instant performedAt, Instant remindAt, UUID remindUserId) {}

    /** Thông tin tối thiểu để kiểm quyền sửa. */
    public record Owner(UUID id, String source, UUID performedBy, UUID remindUserId, String remindStatus,
                        Instant remindAt) {}

    private static final String NGAY_VN = "(now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date";
    private static final String CUOI_HOM_NAY =
            "((" + NGAY_VN + " + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')";

    private static final String SELECT = """
            SELECT a.id, a.contact_id, coalesce(k.full_name, 'Khách chưa có tên') AS contact_name,
                   a.lead_id, coalesce(l.interested_product, 'Lead') AS lead_label, a.deal_id, d.title AS deal_title,
                   a.conversation_id, a.type, a.subject, a.content, a.outcome, a.source, a.performed_by,
                   coalesce(pu.full_name, pu.email) AS performer_name, a.performed_at, a.remind_at, a.remind_user_id,
                   coalesce(ru.full_name, ru.email) AS remind_name, a.remind_status, a.created_at
            FROM sales.activities a
            JOIN engagement.contacts k ON k.id = a.contact_id AND k.tenant_id = a.tenant_id
            LEFT JOIN sales.leads l ON l.id = a.lead_id AND l.tenant_id = a.tenant_id
            LEFT JOIN sales.deals d ON d.id = a.deal_id AND d.tenant_id = a.tenant_id
            LEFT JOIN platform.users pu ON pu.id = a.performed_by AND pu.tenant_id = a.tenant_id
            LEFT JOIN platform.users ru ON ru.id = a.remind_user_id AND ru.tenant_id = a.tenant_id
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public ActivityRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    /** "Việc của tôi" sắp theo giờ nhắc gần nhất; còn lại theo thời điểm thực hiện mới nhất. */
    public List<ActivityDto> search(UUID tenantId, Filter f) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId);
        String where = where(f, p);
        p.addValue("lim", f.size()).addValue("off", (long) f.page() * f.size());
        String order = f.mineUserId() != null
                ? " ORDER BY a.remind_at, a.id"
                : " ORDER BY coalesce(a.performed_at, a.created_at) DESC, a.id";
        return jdbc.query(SELECT + where + order + " LIMIT :lim OFFSET :off", p, ActivityRepository::map);
    }

    public long count(UUID tenantId, Filter f) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId);
        Long n = jdbc.queryForObject("SELECT count(*) FROM sales.activities a" + where(f, p), p, Long.class);
        return n == null ? 0 : n;
    }

    private static String where(Filter f, MapSqlParameterSource p) {
        StringBuilder w = new StringBuilder(" WHERE a.tenant_id = :t");
        if (f.contactId() != null) {
            w.append(" AND a.contact_id = :contact");
            p.addValue("contact", f.contactId());
        }
        if (f.leadId() != null) {
            w.append(" AND a.lead_id = :lead");
            p.addValue("lead", f.leadId());
        }
        if (f.dealId() != null) {
            w.append(" AND a.deal_id = :deal");
            p.addValue("deal", f.dealId());
        }
        if (f.type() != null) {
            w.append(" AND a.type = :type");
            p.addValue("type", f.type());
        }
        if (f.remindStatus() != null) {
            w.append(" AND a.remind_status = :rs");
            p.addValue("rs", f.remindStatus());
        }
        if (f.mineUserId() != null) {
            // Việc của tôi = lời nhắc giao cho tôi, chưa xong, chưa huỷ
            w.append(" AND a.remind_user_id = :me AND a.remind_status IN ('PENDING','SENT')");
            p.addValue("me", f.mineUserId());
            if ("OVERDUE".equals(f.bucket())) {
                w.append(" AND a.remind_at < now()");
            } else if ("TODAY".equals(f.bucket())) {
                w.append(" AND a.remind_at >= now() AND a.remind_at < ").append(CUOI_HOM_NAY);
            } else if ("UPCOMING".equals(f.bucket())) {
                w.append(" AND a.remind_at >= ").append(CUOI_HOM_NAY);
            }
        }
        return w.toString();
    }

    public Optional<ActivityDto> find(UUID tenantId, UUID id) {
        return jdbc.query(SELECT + " WHERE a.tenant_id = :t AND a.id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", id), ActivityRepository::map)
                .stream().findFirst();
    }

    public Optional<Owner> lock(UUID tenantId, UUID id) {
        return jdbc.query("""
                SELECT id, source, performed_by, remind_user_id, remind_status, remind_at
                FROM sales.activities WHERE tenant_id = :t AND id = :id FOR UPDATE""",
                new MapSqlParameterSource("t", tenantId).addValue("id", id),
                (rs, i) -> new Owner(rs.getObject("id", UUID.class), rs.getString("source"),
                        rs.getObject("performed_by", UUID.class), rs.getObject("remind_user_id", UUID.class),
                        rs.getString("remind_status"), instant(rs, "remind_at")))
                .stream().findFirst();
    }

    public TodoCount todoCount(UUID tenantId, UUID userId) {
        return jdbc.queryForObject("""
                SELECT count(*) FILTER (WHERE remind_at < now())::int AS overdue,
                       count(*) FILTER (WHERE remind_at >= now() AND remind_at < %s)::int AS today
                FROM sales.activities
                WHERE tenant_id = :t AND remind_user_id = :u AND remind_status IN ('PENDING','SENT')"""
                        .formatted(CUOI_HOM_NAY),
                new MapSqlParameterSource("t", tenantId).addValue("u", userId),
                (rs, i) -> new TodoCount(rs.getInt("overdue"), rs.getInt("today")));
    }

    /** Khách của lead / deal — để chặn gắn hoạt động của khách A vào lead của khách B. */
    public Optional<UUID> contactOfLead(UUID tenantId, UUID leadId) {
        return jdbc.queryForList("SELECT contact_id FROM sales.leads WHERE tenant_id = :t AND id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", leadId), UUID.class).stream().findFirst();
    }

    public Optional<UUID> contactOfDeal(UUID tenantId, UUID dealId) {
        return jdbc.queryForList("SELECT contact_id FROM sales.deals WHERE tenant_id = :t AND id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", dealId), UUID.class).stream().findFirst();
    }

    /** Khách của hội thoại (có thể chưa gắn khách → rỗng). */
    public Optional<UUID> contactOfConversation(UUID tenantId, UUID conversationId) {
        return jdbc.query("SELECT contact_id FROM engagement.conversations WHERE tenant_id = :t AND id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", conversationId),
                (rs, i) -> Optional.ofNullable(rs.getObject("contact_id", UUID.class)))
                .stream().findFirst().flatMap(o -> o);
    }

    /** Deal ĐANG MỞ mới nhất của khách — nơi gắn hoạt động AUTO đầu tiên. */
    public Optional<UUID> latestOpenDeal(UUID tenantId, UUID contactId) {
        return jdbc.queryForList("""
                SELECT id FROM sales.deals WHERE tenant_id = :t AND contact_id = :c AND status = 'OPEN'
                ORDER BY created_at DESC LIMIT 1""",
                new MapSqlParameterSource("t", tenantId).addValue("c", contactId), UUID.class).stream().findFirst();
    }

    /** Lead ĐANG MỞ của khách (tối đa một — V132). */
    public Optional<UUID> openLead(UUID tenantId, UUID contactId) {
        return jdbc.queryForList("""
                SELECT id FROM sales.leads WHERE tenant_id = :t AND contact_id = :c
                  AND status IN ('NEW','CONTACTED','QUALIFIED') LIMIT 1""",
                new MapSqlParameterSource("t", tenantId).addValue("c", contactId), UUID.class).stream().findFirst();
    }

    // ── ghi ─────────────────────────────────────────────────────────────────────

    public UUID insert(UUID tenantId, NewActivity a) {
        return jdbc.queryForObject("""
                INSERT INTO sales.activities (tenant_id, contact_id, lead_id, deal_id, conversation_id, type, subject,
                                              content, outcome, source, performed_by, performed_at, remind_at,
                                              remind_user_id, remind_status)
                VALUES (:t, :contact, :lead, :deal, :conv, :type, :subject, :content, :outcome, :source, :by,
                        coalesce(CAST(:at AS timestamptz), now()), CAST(:remindAt AS timestamptz), :remindUser,
                        CASE WHEN CAST(:remindAt AS timestamptz) IS NULL THEN 'NONE' ELSE 'PENDING' END)
                RETURNING id""",
                new MapSqlParameterSource("t", tenantId).addValue("contact", a.contactId()).addValue("lead", a.leadId())
                        .addValue("deal", a.dealId()).addValue("conv", a.conversationId()).addValue("type", a.type())
                        .addValue("subject", a.subject()).addValue("content", a.content())
                        .addValue("outcome", a.outcome()).addValue("source", a.source())
                        .addValue("by", a.performedBy()).addValue("at", ts(a.performedAt()))
                        .addValue("remindAt", ts(a.remindAt())).addValue("remindUser", a.remindUserId()),
                UUID.class);
    }

    public void update(UUID tenantId, UUID id, String outcome, String content, Instant remindAt, UUID remindUserId,
                       String remindStatus) {
        jdbc.update("""
                UPDATE sales.activities SET outcome = :outcome, content = :content, remind_at = :remindAt,
                       remind_user_id = :remindUser, remind_status = :rs
                WHERE tenant_id = :t AND id = :id""",
                new MapSqlParameterSource("t", tenantId).addValue("id", id).addValue("outcome", outcome)
                        .addValue("content", content).addValue("remindAt", ts(remindAt))
                        .addValue("remindUser", remindUserId).addValue("rs", remindStatus));
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static ActivityDto map(ResultSet rs, int i) throws SQLException {
        UUID leadId = rs.getObject("lead_id", UUID.class);
        return new ActivityDto(rs.getObject("id", UUID.class), rs.getObject("contact_id", UUID.class),
                rs.getString("contact_name"), leadId, leadId == null ? null : rs.getString("lead_label"),
                rs.getObject("deal_id", UUID.class), rs.getString("deal_title"),
                rs.getObject("conversation_id", UUID.class), rs.getString("type"), rs.getString("subject"),
                rs.getString("content"), rs.getString("outcome"), rs.getString("source"),
                rs.getObject("performed_by", UUID.class), rs.getString("performer_name"),
                instant(rs, "performed_at"), instant(rs, "remind_at"), rs.getObject("remind_user_id", UUID.class),
                rs.getString("remind_name"), rs.getString("remind_status"), instant(rs, "created_at"));
    }

    private static Timestamp ts(Instant i) {
        return i == null ? null : Timestamp.from(i);
    }

    private static Instant instant(ResultSet rs, String col) throws SQLException {
        Timestamp t = rs.getTimestamp(col);
        return t == null ? null : t.toInstant();
    }
}
