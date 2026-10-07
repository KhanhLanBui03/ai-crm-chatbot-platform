package com.thesis.crm.sales.lead;

import java.math.BigDecimal;
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
 * SQL của UC032. Mọi câu có {@code tenant_id = :t} tường minh — lớp thứ hai cạnh RLS, như các
 * repository UC012–UC017. Gọi trong transaction đã {@code TenantTransactionScope.apply()}.
 */
@Repository
public class LeadRepository {

    /** Dòng lead thô, đã nối tên khách và tên người phụ trách. */
    public record LeadRow(
            UUID id, UUID contactId, String contactName, String contactPhone, UUID sourceConversationId,
            String source, String status, String interestedProduct, BigDecimal budgetMin, BigDecimal budgetMax,
            String budgetConfidence, String urgency, Integer currentScore, Instant scoreUpdatedAt,
            UUID ownerUserId, String ownerName, String disqualifiedReason, Instant convertedAt,
            Instant createdAt, Instant updatedAt) {}

    public record Filter(List<String> tokens, String status, String source, UUID ownerUserId, Integer minScore,
                         int page, int size) {}

    /** Khách được chọn khi tạo lead — kèm trạng thái để từ chối khách đã gộp/ẩn danh/xoá. */
    public record ContactRef(UUID id, String status, boolean deleted) {}

    public record ScoreRow(int score, String modelVersion, String topFactorsJson, String confidence,
                           Instant scoredAt) {}

    private static final String SELECT = """
            SELECT l.id, l.contact_id, coalesce(k.full_name, 'Khách chưa có tên') AS contact_name, k.phone,
                   l.source_conversation_id, l.source, l.status, l.interested_product, l.budget_min, l.budget_max,
                   l.budget_confidence, l.urgency, l.current_score, l.score_updated_at,
                   l.owner_user_id, u.full_name AS owner_name, l.disqualified_reason, l.converted_at,
                   l.created_at, l.updated_at
            FROM sales.leads l
            JOIN engagement.contacts k ON k.id = l.contact_id AND k.tenant_id = l.tenant_id
            LEFT JOIN platform.users u ON u.id = l.owner_user_id AND u.tenant_id = l.tenant_id
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public LeadRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    /** Sắp điểm giảm dần, lead chưa chấm điểm xếp cuối (UC032 bước 3); hoà điểm thì lead mới trước. */
    public List<LeadRow> search(UUID tenantId, Filter f) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId);
        String where = where(f, p);
        p.addValue("lim", f.size()).addValue("off", (long) f.page() * f.size());
        return jdbc.query(SELECT + where
                + " ORDER BY l.current_score DESC NULLS LAST, l.created_at DESC, l.id LIMIT :lim OFFSET :off",
                p, LeadRepository::map);
    }

    public long count(UUID tenantId, Filter f) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId);
        Long n = jdbc.queryForObject("""
                SELECT count(*) FROM sales.leads l
                JOIN engagement.contacts k ON k.id = l.contact_id AND k.tenant_id = l.tenant_id
                """ + where(f, p), p, Long.class);
        return n == null ? 0 : n;
    }

    private static String where(Filter f, MapSqlParameterSource p) {
        StringBuilder w = new StringBuilder(" WHERE l.tenant_id = :t");
        if (f.status() != null) {
            w.append(" AND l.status = :status");
            p.addValue("status", f.status());
        }
        if (f.source() != null) {
            w.append(" AND l.source = :source");
            p.addValue("source", f.source());
        }
        if (f.ownerUserId() != null) {
            w.append(" AND l.owner_user_id = :owner");
            p.addValue("owner", f.ownerUserId());
        }
        if (f.minScore() != null) {
            w.append(" AND l.current_score >= :minScore");
            p.addValue("minScore", f.minScore());
        }
        // Tìm theo tên/SĐT khách, không dấu — dùng lại cột search_text của danh bạ (V124)
        for (int i = 0; i < f.tokens().size(); i++) {
            w.append(" AND k.search_text LIKE :kw").append(i).append(" ESCAPE '\\'");
            p.addValue("kw" + i, "%" + escapeLike(f.tokens().get(i)) + "%");
        }
        return w.toString();
    }

    public Optional<LeadRow> find(UUID tenantId, UUID leadId) {
        return jdbc.query(SELECT + " WHERE l.tenant_id = :t AND l.id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", leadId), LeadRepository::map)
                .stream().findFirst();
    }

    /** Khoá dòng lead trước khi sửa — hai người sửa cùng lúc thì người sau thấy trạng thái mới nhất. */
    public boolean lock(UUID tenantId, UUID leadId) {
        return !jdbc.queryForList("SELECT id FROM sales.leads WHERE tenant_id = :t AND id = :id FOR UPDATE",
                new MapSqlParameterSource("t", tenantId).addValue("id", leadId), UUID.class).isEmpty();
    }

    /** Lead đang mở của khách (tối đa một — chỉ mục {@code uq_leads_mot_lead_mo_moi_khach}). */
    public Optional<LeadRow> findOpenByContact(UUID tenantId, UUID contactId) {
        return jdbc.query(SELECT + """
                 WHERE l.tenant_id = :t AND l.contact_id = :c AND l.status IN ('NEW','CONTACTED','QUALIFIED')""",
                new MapSqlParameterSource("t", tenantId).addValue("c", contactId), LeadRepository::map)
                .stream().findFirst();
    }

    public Optional<ContactRef> findContact(UUID tenantId, UUID contactId) {
        return jdbc.query("""
                SELECT id, status, deleted_at IS NOT NULL AS deleted FROM engagement.contacts
                WHERE tenant_id = :t AND id = :id""",
                new MapSqlParameterSource("t", tenantId).addValue("id", contactId),
                (rs, i) -> new ContactRef(rs.getObject("id", UUID.class), rs.getString("status"),
                        rs.getBoolean("deleted")))
                .stream().findFirst();
    }

    /** Khách của một hội thoại — {@code null} trong Optional nghĩa là hội thoại chưa gắn khách. */
    public Optional<Optional<UUID>> conversationContact(UUID tenantId, UUID conversationId) {
        return jdbc.query("SELECT contact_id FROM engagement.conversations WHERE tenant_id = :t AND id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", conversationId),
                (rs, i) -> Optional.ofNullable(rs.getObject("contact_id", UUID.class)))
                .stream().findFirst();
    }

    /** Người dùng ĐANG HOẠT ĐỘNG của doanh nghiệp — trả tên, hoặc rỗng nếu không hợp lệ. */
    public Optional<String> activeUserName(UUID tenantId, UUID userId) {
        return jdbc.queryForList("""
                SELECT full_name FROM platform.users
                WHERE tenant_id = :t AND id = :id AND status = 'ACTIVE' AND deleted_at IS NULL""",
                new MapSqlParameterSource("t", tenantId).addValue("id", userId), String.class)
                .stream().findFirst();
    }

    public Optional<UUID> convertedDealId(UUID tenantId, UUID leadId) {
        return jdbc.queryForList("SELECT id FROM sales.deals WHERE tenant_id = :t AND lead_id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", leadId), UUID.class)
                .stream().findFirst();
    }

    public int activityCount(UUID tenantId, UUID leadId) {
        Integer n = jdbc.queryForObject(
                "SELECT count(*)::int FROM sales.activities WHERE tenant_id = :t AND lead_id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", leadId), Integer.class);
        return n == null ? 0 : n;
    }

    /** Lịch sử điểm, mới nhất trước (UC032 bước 6). Bảng chỉ ghi thêm — {@code sales.lead_scores}, V113. */
    public List<ScoreRow> scores(UUID tenantId, UUID leadId, int limit) {
        return jdbc.query("""
                SELECT score, model_version, top_factors::text AS top_factors, confidence, scored_at
                FROM sales.lead_scores WHERE tenant_id = :t AND lead_id = :id
                ORDER BY scored_at DESC LIMIT :lim""",
                new MapSqlParameterSource("t", tenantId).addValue("id", leadId).addValue("lim", limit),
                (rs, i) -> new ScoreRow(rs.getInt("score"), rs.getString("model_version"),
                        rs.getString("top_factors"), rs.getString("confidence"), instant(rs, "scored_at")));
    }

    // ── ghi ─────────────────────────────────────────────────────────────────────

    public UUID insert(UUID tenantId, LeadDtos.CreateLeadRequest r, UUID ownerUserId) {
        return jdbc.queryForObject("""
                INSERT INTO sales.leads (tenant_id, contact_id, source_conversation_id, source, status,
                                         interested_product, budget_min, budget_max, urgency, owner_user_id)
                VALUES (:t, :contact, :conv, 'MANUAL', 'NEW', :product, :bmin, :bmax, :urgency, :owner)
                RETURNING id""",
                new MapSqlParameterSource("t", tenantId).addValue("contact", r.contactId())
                        .addValue("conv", r.sourceConversationId()).addValue("product", r.interestedProduct())
                        .addValue("bmin", r.budgetMin()).addValue("bmax", r.budgetMax())
                        .addValue("urgency", r.urgency()).addValue("owner", ownerUserId), UUID.class);
    }

    /** Ghi đè trọn các trường người dùng sửa được — service đã gộp giá trị cũ với phần thay đổi. */
    public void update(UUID tenantId, UUID leadId, String status, String interestedProduct, BigDecimal budgetMin,
                       BigDecimal budgetMax, String urgency, UUID ownerUserId, String disqualifiedReason) {
        jdbc.update("""
                UPDATE sales.leads SET status = :status, interested_product = :product, budget_min = :bmin,
                       budget_max = :bmax, urgency = :urgency, owner_user_id = :owner, disqualified_reason = :reason
                WHERE tenant_id = :t AND id = :id""",
                new MapSqlParameterSource("t", tenantId).addValue("id", leadId).addValue("status", status)
                        .addValue("product", interestedProduct).addValue("bmin", budgetMin)
                        .addValue("bmax", budgetMax).addValue("urgency", urgency).addValue("owner", ownerUserId)
                        .addValue("reason", disqualifiedReason));
    }

    /** UC033 — lead đã thành deal: khoá lại, giữ bản ghi (đặc tả b7). */
    public void markConverted(UUID tenantId, UUID leadId, UUID ownerUserId) {
        jdbc.update("""
                UPDATE sales.leads SET status = 'CONVERTED', converted_at = now(), owner_user_id = :owner
                WHERE tenant_id = :t AND id = :id""",
                new MapSqlParameterSource("t", tenantId).addValue("id", leadId).addValue("owner", ownerUserId));
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static LeadRow map(ResultSet rs, int i) throws SQLException {
        int raw = rs.getInt("current_score");
        Integer score = rs.wasNull() ? null : raw;
        return new LeadRow(
                rs.getObject("id", UUID.class), rs.getObject("contact_id", UUID.class), rs.getString("contact_name"),
                rs.getString("phone"), rs.getObject("source_conversation_id", UUID.class), rs.getString("source"),
                rs.getString("status"), rs.getString("interested_product"), rs.getBigDecimal("budget_min"),
                rs.getBigDecimal("budget_max"), rs.getString("budget_confidence"), rs.getString("urgency"),
                score, instant(rs, "score_updated_at"),
                rs.getObject("owner_user_id", UUID.class), rs.getString("owner_name"),
                rs.getString("disqualified_reason"), instant(rs, "converted_at"),
                instant(rs, "created_at"), instant(rs, "updated_at"));
    }

    private static Instant instant(ResultSet rs, String col) throws SQLException {
        Timestamp ts = rs.getTimestamp(col);
        return ts == null ? null : ts.toInstant();
    }

    private static String escapeLike(String s) {
        return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }
}
