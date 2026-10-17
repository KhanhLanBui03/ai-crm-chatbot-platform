package com.thesis.crm.engagement.repository;

import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import jakarta.persistence.EntityManager;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * {@code engagement.tags} và {@code engagement.contact_tags} — UC017, qua Entity {@code Tag} /
 * {@code ContactTag} (JPA). Mọi câu lọc {@code tenantId}. {@code usage_count} do trigger
 * {@code trg_contact_tags_count} (V125) cập nhật — repository không tự cộng trừ.
 *
 * <p><b>Hai câu cố ý giữ native SQL</b> ({@link #insertIfAbsent}, {@link #attach}): cần
 * {@code ON CONFLICT DO NOTHING}, JPA không có lệnh tương đương. Đi bằng {@code persist()} thì hai người
 * tạo cùng một thẻ cùng lúc, người sau vấp vi phạm UNIQUE — mà trong Postgres lỗi đó làm hỏng CẢ
 * transaction, không bắt rồi đọc lại thẻ cũ được (lỗi 500).
 */
@Repository
public class TagRepository {

    /** Gói không xác định (không có thuê bao hiệu lực) tính như TRIAL — quyết định UC017. */
    private static final String FALLBACK_PLAN = "TRIAL";
    private static final int FALLBACK_MAX_TAGS = 20;

    private static final String SELECT_DTO = """
            SELECT new com.thesis.crm.engagement.dto.response.ContactDtos$TagDto(t.id, t.name, t.color, t.usageCount)
            FROM Tag t
            """;

    private final EntityManager em;

    public TagRepository(EntityManager em) {
        this.em = em;
    }

    public List<TagDto> listAll(UUID tenantId) {
        return em.createQuery(SELECT_DTO + "WHERE t.tenantId = :tenantId ORDER BY lower(t.name)", TagDto.class)
                .setParameter("tenantId", tenantId)
                .getResultList();
    }

    public Optional<TagDto> findById(UUID tenantId, UUID tagId) {
        return em.createQuery(SELECT_DTO + "WHERE t.tenantId = :tenantId AND t.id = :tagId", TagDto.class)
                .setParameter("tenantId", tenantId)
                .setParameter("tagId", tagId)
                .getResultStream().findFirst();
    }

    /** Thẻ cùng tên sau khi bỏ dấu + viết thường — cùng biểu thức với chỉ mục uq_tags_tenant_name. */
    public Optional<TagDto> findByFoldedName(UUID tenantId, String name) {
        return em.createQuery(SELECT_DTO + """
                WHERE t.tenantId = :tenantId
                  AND function('engagement.fold_vi', trim(t.name)) = function('engagement.fold_vi', trim(:name))
                """, TagDto.class)
                .setParameter("tenantId", tenantId)
                .setParameter("name", name)
                .getResultStream().findFirst();
    }

    public int count(UUID tenantId) {
        return em.createQuery("SELECT count(t) FROM Tag t WHERE t.tenantId = :tenantId", Long.class)
                .setParameter("tenantId", tenantId)
                .getSingleResult().intValue();
    }

    /** Trần số thẻ theo gói của thuê bao còn hiệu lực gần nhất; không có thì như gói TRIAL. */
    public int maxTags(UUID tenantId) {
        List<Short> fromSubscription = em.createQuery("""
                SELECT p.maxTags
                FROM TenantSubscription s, SubscriptionPlan p
                WHERE p.id = s.planId AND s.tenantId = :tenantId
                  AND s.status IN ('TRIALING', 'ACTIVE', 'PAST_DUE')
                ORDER BY s.periodStart DESC
                """, Short.class)
                .setParameter("tenantId", tenantId)
                .setMaxResults(1)
                .getResultList();
        if (!fromSubscription.isEmpty()) {
            return fromSubscription.get(0);
        }
        List<Short> trial = em.createQuery("SELECT p.maxTags FROM SubscriptionPlan p WHERE p.code = :code", Short.class)
                .setParameter("code", FALLBACK_PLAN)
                .getResultList();
        return trial.isEmpty() ? FALLBACK_MAX_TAGS : trial.get(0);
    }

    /**
     * Chèn thẻ; trùng tên (bỏ dấu, viết thường) thì KHÔNG chèn và trả rỗng. Native SQL có chủ đích —
     * xem chú thích lớp.
     */
    public Optional<TagDto> insertIfAbsent(UUID tenantId, UUID createdBy, String name, String color) {
        List<?> rows = em.createNativeQuery("""
                INSERT INTO engagement.tags (tenant_id, name, color, created_by)
                VALUES (:tenantId, :name, :color, :createdBy)
                ON CONFLICT (tenant_id, engagement.fold_vi(btrim(name))) DO NOTHING
                RETURNING id, name, color, usage_count
                """)
                .setParameter("tenantId", tenantId)
                .setParameter("name", name)
                .setParameter("color", color)
                .setParameter("createdBy", createdBy)
                .getResultList();
        return rows.stream().findFirst().map(r -> {
            Object[] c = (Object[]) r;
            return new TagDto((UUID) c[0], (String) c[1], (String) c[2], ((Number) c[3]).intValue());
        });
    }

    /**
     * @return {@code true} nếu vừa gắn mới; {@code false} nếu đã gắn từ trước (không đổi gì). Native SQL
     *         có chủ đích — xem chú thích lớp.
     */
    public boolean attach(UUID tenantId, UUID contactId, UUID tagId, UUID taggedBy) {
        return em.createNativeQuery("""
                INSERT INTO engagement.contact_tags (contact_id, tag_id, tenant_id, tagged_by)
                VALUES (:contactId, :tagId, :tenantId, :taggedBy)
                ON CONFLICT (contact_id, tag_id) DO NOTHING
                """)
                .setParameter("tenantId", tenantId)
                .setParameter("contactId", contactId)
                .setParameter("tagId", tagId)
                .setParameter("taggedBy", taggedBy)
                .executeUpdate() > 0;
    }

    /** @return {@code true} nếu vừa gỡ; {@code false} nếu vốn chưa gắn. */
    public boolean detach(UUID tenantId, UUID contactId, UUID tagId) {
        return em.createQuery("""
                DELETE FROM ContactTag ct
                WHERE ct.tenantId = :tenantId AND ct.contactId = :contactId AND ct.tagId = :tagId
                """)
                .setParameter("tenantId", tenantId)
                .setParameter("contactId", contactId)
                .setParameter("tagId", tagId)
                .executeUpdate() > 0;
    }
}
