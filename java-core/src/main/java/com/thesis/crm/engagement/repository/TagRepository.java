package com.thesis.crm.engagement.repository;

import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * {@code engagement.tags} và {@code engagement.contact_tags} — UC017. Mọi câu có
 * {@code tenant_id = :tenantId}. {@code usage_count} do trigger {@code trg_contact_tags_count}
 * (V125) cập nhật — repository không tự cộng trừ.
 */
@Repository
public class TagRepository {

    /** Gói không xác định (không có thuê bao hiệu lực) tính như TRIAL — quyết định UC017. */
    private static final String FALLBACK_PLAN = "TRIAL";
    private static final int FALLBACK_MAX_TAGS = 20;

    private final NamedParameterJdbcTemplate jdbc;

    public TagRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<TagDto> listAll(UUID tenantId) {
        return jdbc.query("""
                SELECT id, name, color, usage_count FROM engagement.tags
                WHERE tenant_id = :tenantId ORDER BY lower(name)
                """,
                new MapSqlParameterSource("tenantId", tenantId), (rs, i) -> map(rs));
    }

    public Optional<TagDto> findById(UUID tenantId, UUID tagId) {
        return jdbc.query("""
                SELECT id, name, color, usage_count FROM engagement.tags
                WHERE tenant_id = :tenantId AND id = :tagId
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("tagId", tagId),
                (rs, i) -> map(rs)).stream().findFirst();
    }

    /** Thẻ cùng tên sau khi bỏ dấu + viết thường — cùng biểu thức với chỉ mục uq_tags_tenant_name. */
    public Optional<TagDto> findByFoldedName(UUID tenantId, String name) {
        return jdbc.query("""
                SELECT id, name, color, usage_count FROM engagement.tags
                WHERE tenant_id = :tenantId
                  AND engagement.fold_vi(btrim(name)) = engagement.fold_vi(btrim(:name))
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("name", name),
                (rs, i) -> map(rs)).stream().findFirst();
    }

    public int count(UUID tenantId) {
        Integer n = jdbc.queryForObject("SELECT count(*) FROM engagement.tags WHERE tenant_id = :tenantId",
                new MapSqlParameterSource("tenantId", tenantId), Integer.class);
        return n == null ? 0 : n;
    }

    /** Trần số thẻ theo gói của thuê bao còn hiệu lực gần nhất; không có thì như gói TRIAL. */
    public int maxTags(UUID tenantId) {
        List<Integer> fromSubscription = jdbc.query("""
                SELECT p.max_tags
                FROM platform.tenant_subscriptions s
                JOIN platform.subscription_plans p ON p.id = s.plan_id
                WHERE s.tenant_id = :tenantId AND s.status IN ('TRIALING','ACTIVE','PAST_DUE')
                ORDER BY s.period_start DESC
                LIMIT 1
                """,
                new MapSqlParameterSource("tenantId", tenantId), (rs, i) -> rs.getInt(1));
        if (!fromSubscription.isEmpty()) {
            return fromSubscription.get(0);
        }
        List<Integer> trial = jdbc.query(
                "SELECT max_tags FROM platform.subscription_plans WHERE code = :code",
                new MapSqlParameterSource("code", FALLBACK_PLAN), (rs, i) -> rs.getInt(1));
        return trial.isEmpty() ? FALLBACK_MAX_TAGS : trial.get(0);
    }

    /**
     * Chèn thẻ; trùng tên (bỏ dấu, viết thường) thì KHÔNG chèn và trả rỗng.
     *
     * <p>Dùng {@code ON CONFLICT} trên chính biểu thức của chỉ mục thay vì bắt lỗi trùng: trong
     * Postgres, vi phạm UNIQUE làm hỏng cả transaction nên không đọc lại thẻ cũ được — hai người tạo
     * cùng một thẻ trong cùng lúc sẽ có một người nhận lỗi 500.
     */
    public Optional<TagDto> insertIfAbsent(UUID tenantId, UUID createdBy, String name, String color) {
        return jdbc.query("""
                INSERT INTO engagement.tags (tenant_id, name, color, created_by)
                VALUES (:tenantId, :name, :color, :createdBy)
                ON CONFLICT (tenant_id, engagement.fold_vi(btrim(name))) DO NOTHING
                RETURNING id, name, color, usage_count
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("name", name)
                        .addValue("color", color).addValue("createdBy", createdBy),
                (rs, i) -> map(rs)).stream().findFirst();
    }

    /** @return {@code true} nếu vừa gắn mới; {@code false} nếu đã gắn từ trước (không đổi gì). */
    public boolean attach(UUID tenantId, UUID contactId, UUID tagId, UUID taggedBy) {
        return jdbc.update("""
                INSERT INTO engagement.contact_tags (contact_id, tag_id, tenant_id, tagged_by)
                VALUES (:contactId, :tagId, :tenantId, :taggedBy)
                ON CONFLICT (contact_id, tag_id) DO NOTHING
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("contactId", contactId)
                        .addValue("tagId", tagId).addValue("taggedBy", taggedBy)) > 0;
    }

    /** @return {@code true} nếu vừa gỡ; {@code false} nếu vốn chưa gắn. */
    public boolean detach(UUID tenantId, UUID contactId, UUID tagId) {
        return jdbc.update("""
                DELETE FROM engagement.contact_tags
                WHERE tenant_id = :tenantId AND contact_id = :contactId AND tag_id = :tagId
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("contactId", contactId)
                        .addValue("tagId", tagId)) > 0;
    }

    private static TagDto map(java.sql.ResultSet rs) throws java.sql.SQLException {
        return new TagDto(rs.getObject("id", UUID.class), rs.getString("name"), rs.getString("color"),
                rs.getInt("usage_count"));
    }
}
