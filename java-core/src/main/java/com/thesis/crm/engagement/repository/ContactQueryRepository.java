package com.thesis.crm.engagement.repository;

import com.thesis.crm.engagement.dto.response.ContactDtos.ChannelIdentityDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import java.math.BigDecimal;
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
 * Đọc danh bạ bằng SQL tường minh — UC016.
 *
 * <p><b>Mọi câu đều có {@code tenant_id = :tenantId}</b> dù RLS đã lọc: hai lớp độc lập, một lớp
 * cấu hình sai (vd chạy bằng role chủ bảng) thì lớp kia vẫn giữ — chỉ số rò rỉ tenant phải là 0.
 *
 * <p>Phải gọi trong {@code @Transactional} đã qua {@code TenantTransactionScope.apply()}:
 * {@code platform.current_tenant()} ném lỗi khi chưa đặt tenant.
 */
@Repository
public class ContactQueryRepository {

    /** Cột sắp xếp được phép — nhận từ query string nên KHÔNG bao giờ nối chuỗi trực tiếp. */
    private static final Map<String, String> SORT_COLUMNS = Map.of(
            "fullName", "c.full_name",
            "lastInteractionAt", "c.last_contacted_at",
            "createdAt", "c.created_at");

    private static final String CONTACT_COLUMNS = """
            c.id, c.full_name, c.phone, c.email, c.primary_channel, c.status,
            c.consent_granted, c.consent_at, c.last_contacted_at, c.created_at
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public ContactQueryRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** {@code tokens}: các từ đã bỏ dấu — khách khớp khi {@code search_text} chứa ĐỦ mọi từ. */
    public record SearchFilter(
            List<String> tokens, String status, UUID tagId, Boolean hasConsent, String sort, int page, int size) {}

    public record PageResult(List<ContactDto> items, long total) {}

    /** Danh sách có lọc, sắp xếp, phân trang. Mặc định ẩn MERGED (hợp đồng SCR026). */
    public PageResult search(UUID tenantId, SearchFilter f) {
        MapSqlParameterSource p = new MapSqlParameterSource("tenantId", tenantId);
        StringBuilder where = new StringBuilder(" WHERE c.tenant_id = :tenantId AND c.deleted_at IS NULL");

        if (f.status() != null) {
            where.append(" AND c.status = :status");
            p.addValue("status", f.status());
        } else {
            where.append(" AND c.status <> 'MERGED'");
        }
        // Mỗi từ một điều kiện AND, tham số hoá — không bao giờ nối chuỗi người dùng gõ vào SQL
        for (int i = 0; i < f.tokens().size(); i++) {
            where.append(" AND c.search_text LIKE :kw").append(i).append(" ESCAPE '\\'");
            p.addValue("kw" + i, "%" + escapeLike(f.tokens().get(i)) + "%");
        }
        if (f.tagId() != null) {
            where.append("""
                     AND EXISTS (SELECT 1 FROM engagement.contact_tags ct
                                  WHERE ct.tenant_id = :tenantId AND ct.contact_id = c.id AND ct.tag_id = :tagId)""");
            p.addValue("tagId", f.tagId());
        }
        if (f.hasConsent() != null) {
            where.append(" AND c.consent_granted = :hasConsent");
            p.addValue("hasConsent", f.hasConsent());
        }

        Long total = jdbc.queryForObject("SELECT count(*) FROM engagement.contacts c" + where, p, Long.class);

        p.addValue("limit", f.size()).addValue("offset", (long) f.page() * f.size());
        List<ContactDto> rows = jdbc.query(
                "SELECT " + CONTACT_COLUMNS + " FROM engagement.contacts c" + where
                        + " ORDER BY " + orderBy(f.sort()) + " LIMIT :limit OFFSET :offset",
                p, (rs, i) -> mapContact(rs, List.of()));

        return new PageResult(withTags(tenantId, rows), total == null ? 0 : total);
    }

    /** Một khách (kể cả MERGED — hồ sơ cũ vẫn mở được qua liên kết), trừ đã xoá mềm. */
    public Optional<ContactDto> findById(UUID tenantId, UUID id) {
        List<ContactDto> rows = jdbc.query(
                "SELECT " + CONTACT_COLUMNS + " FROM engagement.contacts c"
                        + " WHERE c.tenant_id = :tenantId AND c.id = :id AND c.deleted_at IS NULL",
                new MapSqlParameterSource("tenantId", tenantId).addValue("id", id),
                (rs, i) -> mapContact(rs, List.of()));
        return withTags(tenantId, rows).stream().findFirst();
    }

    /** Trạng thái khách (ACTIVE / MERGED / ANONYMIZED); rỗng nếu không có, đã xoá, hoặc thuộc tenant khác. */
    public Optional<String> findStatus(UUID tenantId, UUID id) {
        return jdbc.query("""
                SELECT status FROM engagement.contacts
                WHERE tenant_id = :tenantId AND id = :id AND deleted_at IS NULL
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("id", id),
                (rs, i) -> rs.getString("status")).stream().findFirst();
    }

    public record DetailExtras(
            UUID mergedIntoContactId, Instant anonymizedAt, int conversationCount, int openLeadCount,
            int openDealCount, BigDecimal totalDealValue) {}

    /** Phần riêng của hồ sơ: đếm hội thoại / lead / deal — truy vấn thật, bảng trống thì ra 0. */
    public DetailExtras detailExtras(UUID tenantId, UUID id) {
        return jdbc.queryForObject("""
                SELECT c.merged_into_contact_id, c.anonymized_at,
                  (SELECT count(*) FROM engagement.conversations v
                    WHERE v.tenant_id = :tenantId AND v.contact_id = c.id) AS conversation_count,
                  (SELECT count(*) FROM sales.leads l
                    WHERE l.tenant_id = :tenantId AND l.contact_id = c.id
                      AND l.status NOT IN ('CONVERTED','DISQUALIFIED')) AS open_lead_count,
                  (SELECT count(*) FROM sales.deals d
                    WHERE d.tenant_id = :tenantId AND d.contact_id = c.id AND d.status = 'OPEN') AS open_deal_count,
                  (SELECT coalesce(sum(d.amount), 0) FROM sales.deals d
                    WHERE d.tenant_id = :tenantId AND d.contact_id = c.id AND d.status = 'OPEN') AS open_deal_value
                FROM engagement.contacts c
                WHERE c.tenant_id = :tenantId AND c.id = :id
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("id", id),
                (rs, i) -> new DetailExtras(
                        rs.getObject("merged_into_contact_id", UUID.class),
                        instant(rs, "anonymized_at"),
                        rs.getInt("conversation_count"),
                        rs.getInt("open_lead_count"),
                        rs.getInt("open_deal_count"),
                        rs.getBigDecimal("open_deal_value")));
    }

    public List<ChannelIdentityDto> channelIdentities(UUID tenantId, UUID contactId) {
        return jdbc.query("""
                SELECT ci.id, ch.type AS channel_type, ci.external_user_id, ci.display_name, ci.avatar_url,
                       ci.raw_profile ->> 'originDomain' AS origin_domain, ci.last_seen_at
                FROM engagement.channel_identities ci
                JOIN engagement.channels ch ON ch.id = ci.channel_id AND ch.tenant_id = ci.tenant_id
                WHERE ci.tenant_id = :tenantId AND ci.contact_id = :contactId
                ORDER BY ci.last_seen_at DESC
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("contactId", contactId),
                (rs, i) -> new ChannelIdentityDto(
                        rs.getObject("id", UUID.class),
                        rs.getString("channel_type"),
                        rs.getString("external_user_id"),
                        rs.getString("display_name"),
                        rs.getString("avatar_url"),
                        rs.getString("origin_domain"),
                        instant(rs, "last_seen_at")));
    }

    /** Khách khác (chưa gộp, chưa xoá) trùng số điện thoại hoặc địa chỉ thư — để gợi ý hợp nhất. */
    public List<ContactDto> findDuplicates(UUID tenantId, UUID excludeId, String phone, String email) {
        if (phone == null && email == null) {
            return List.of();
        }
        MapSqlParameterSource p = new MapSqlParameterSource("tenantId", tenantId)
                .addValue("excludeId", excludeId)
                .addValue("phone", phone)
                .addValue("email", email);
        List<ContactDto> rows = jdbc.query(
                "SELECT " + CONTACT_COLUMNS + """
                 FROM engagement.contacts c
                WHERE c.tenant_id = :tenantId AND c.id <> :excludeId
                  AND c.deleted_at IS NULL AND c.status = 'ACTIVE'
                  AND ((CAST(:phone AS varchar) IS NOT NULL AND c.phone = :phone)
                    OR (CAST(:email AS varchar) IS NOT NULL AND lower(c.email) = lower(:email)))
                ORDER BY c.created_at
                LIMIT 10
                """,
                p, (rs, i) -> mapContact(rs, List.of()));
        return withTags(tenantId, rows);
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    private List<ContactDto> withTags(UUID tenantId, List<ContactDto> rows) {
        if (rows.isEmpty()) {
            return rows;
        }
        Map<UUID, List<TagDto>> tags = tagsFor(tenantId, rows.stream().map(ContactDto::id).toList());
        List<ContactDto> out = new ArrayList<>(rows.size());
        for (ContactDto c : rows) {
            out.add(new ContactDto(c.id(), c.fullName(), c.phone(), c.email(), c.primaryChannel(), c.status(),
                    c.consentGranted(), c.consentAt(), tags.getOrDefault(c.id(), List.of()),
                    c.lastInteractionAt(), c.createdAt()));
        }
        return out;
    }

    private Map<UUID, List<TagDto>> tagsFor(UUID tenantId, Collection<UUID> contactIds) {
        Map<UUID, List<TagDto>> out = new HashMap<>();
        jdbc.query("""
                SELECT ct.contact_id, t.id, t.name, t.color, t.usage_count
                FROM engagement.contact_tags ct
                JOIN engagement.tags t ON t.id = ct.tag_id AND t.tenant_id = ct.tenant_id
                WHERE ct.tenant_id = :tenantId AND ct.contact_id IN (:ids)
                ORDER BY t.name
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("ids", contactIds),
                rs -> {
                    out.computeIfAbsent(rs.getObject("contact_id", UUID.class), k -> new ArrayList<>())
                            .add(new TagDto(rs.getObject("id", UUID.class), rs.getString("name"),
                                    rs.getString("color"), rs.getInt("usage_count")));
                });
        return out;
    }

    private static ContactDto mapContact(ResultSet rs, List<TagDto> tags) throws SQLException {
        return new ContactDto(
                rs.getObject("id", UUID.class),
                rs.getString("full_name"),
                rs.getString("phone"),
                rs.getString("email"),
                rs.getString("primary_channel"),
                rs.getString("status"),
                rs.getBoolean("consent_granted"),
                instant(rs, "consent_at"),
                tags,
                instant(rs, "last_contacted_at"),
                instant(rs, "created_at"));
    }

    private static String orderBy(String sort) {
        String fallback = "c.last_contacted_at DESC NULLS LAST, c.created_at DESC";
        if (sort == null || sort.isBlank()) {
            return fallback;
        }
        boolean desc = sort.startsWith("-");
        String column = SORT_COLUMNS.get(desc ? sort.substring(1) : sort);
        if (column == null) {
            return fallback;
        }
        return column + (desc ? " DESC NULLS LAST" : " ASC NULLS LAST") + ", c.id";
    }

    private static String escapeLike(String s) {
        return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }

    private static Instant instant(ResultSet rs, String column) throws SQLException {
        Timestamp ts = rs.getTimestamp(column);
        return ts == null ? null : ts.toInstant();
    }
}
