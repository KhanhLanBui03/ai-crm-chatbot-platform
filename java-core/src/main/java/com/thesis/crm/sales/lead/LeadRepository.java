package com.thesis.crm.sales.lead;

import com.thesis.crm.common.enums.LeadSource;
import com.thesis.crm.common.enums.LeadStatus;
import com.thesis.crm.common.enums.Level;
import com.thesis.crm.engagement.entity.Contact;
import com.thesis.crm.sales.entity.Lead;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import jakarta.persistence.TypedQuery;
import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * Truy cập dữ liệu UC032 qua Entity {@link Lead} (JPA). Mọi truy vấn lọc {@code tenantId} tường minh — lớp
 * thứ hai cạnh RLS. Gọi trong transaction đã {@code TenantTransactionScope.apply()}.
 *
 * <p>Giữ nguyên chữ ký các hàm từ bản SQL tay, nên {@code LeadService} không phải đổi.
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
                         UUID contactId, int page, int size) {}

    /** Khách được chọn khi tạo lead — kèm trạng thái để từ chối khách đã gộp/ẩn danh/xoá. */
    public record ContactRef(UUID id, String status, boolean deleted) {}

    public record ScoreRow(int score, String modelVersion, String topFactorsJson, String confidence,
                           Instant scoredAt) {}

    private static final List<LeadStatus> DANG_MO = List.of(LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED);

    /** Lead kèm tên + SĐT khách và tên người phụ trách — cùng tenant. */
    private static final String SELECT = """
            SELECT l, coalesce(k.fullName, 'Khách chưa có tên'), k.phone, u.fullName
            FROM Lead l
            JOIN Contact k ON k.id = l.contactId AND k.tenantId = l.tenantId
            LEFT JOIN User u ON u.id = l.ownerUserId AND u.tenantId = l.tenantId
            """;

    private final EntityManager em;

    public LeadRepository(EntityManager em) {
        this.em = em;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    /** Sắp điểm giảm dần, lead chưa chấm điểm xếp cuối (UC032 bước 3); hoà điểm thì lead mới trước. */
    public List<LeadRow> search(UUID tenantId, Filter f) {
        Map<String, Object> p = new HashMap<>();
        TypedQuery<Object[]> q = em.createQuery(SELECT + where(tenantId, f, p)
                        + " ORDER BY l.currentScore DESC NULLS LAST, l.createdAt DESC, l.id", Object[].class)
                .setFirstResult(f.page() * f.size())
                .setMaxResults(f.size());
        p.forEach(q::setParameter);
        return q.getResultStream().map(LeadRepository::map).toList();
    }

    public long count(UUID tenantId, Filter f) {
        Map<String, Object> p = new HashMap<>();
        TypedQuery<Long> q = em.createQuery("""
                SELECT count(l) FROM Lead l
                JOIN Contact k ON k.id = l.contactId AND k.tenantId = l.tenantId
                """ + where(tenantId, f, p), Long.class);
        p.forEach(q::setParameter);
        return q.getSingleResult();
    }

    private static String where(UUID tenantId, Filter f, Map<String, Object> p) {
        StringBuilder w = new StringBuilder(" WHERE l.tenantId = :t");
        p.put("t", tenantId);
        if (f.status() != null) {
            w.append(" AND l.status = :status");
            p.put("status", LeadStatus.valueOf(f.status()));
        }
        if (f.source() != null) {
            w.append(" AND l.source = :source");
            p.put("source", LeadSource.valueOf(f.source()));
        }
        if (f.ownerUserId() != null) {
            w.append(" AND l.ownerUserId = :owner");
            p.put("owner", f.ownerUserId());
        }
        if (f.contactId() != null) {
            w.append(" AND l.contactId = :contact");
            p.put("contact", f.contactId());
        }
        if (f.minScore() != null) {
            w.append(" AND l.currentScore >= :minScore");
            p.put("minScore", f.minScore().shortValue());
        }
        // Tìm theo tên/SĐT khách, không dấu — dùng lại cột search_text của danh bạ (V124)
        for (int i = 0; i < f.tokens().size(); i++) {
            w.append(" AND k.searchText LIKE :kw").append(i).append(" ESCAPE '!'");
            p.put("kw" + i, "%" + escapeLike(f.tokens().get(i)) + "%");
        }
        return w.toString();
    }

    public Optional<LeadRow> find(UUID tenantId, UUID leadId) {
        return em.createQuery(SELECT + " WHERE l.tenantId = :t AND l.id = :id", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("id", leadId)
                .getResultStream().findFirst().map(LeadRepository::map);
    }

    /** Khoá dòng lead trước khi sửa — hai người sửa cùng lúc thì người sau thấy trạng thái mới nhất. */
    public boolean lock(UUID tenantId, UUID leadId) {
        return managed(tenantId, leadId, LockModeType.PESSIMISTIC_WRITE).isPresent();
    }

    /** Lead đang mở của khách (tối đa một — chỉ mục {@code uq_leads_mot_lead_mo_moi_khach}). */
    public Optional<LeadRow> findOpenByContact(UUID tenantId, UUID contactId) {
        return em.createQuery(SELECT + " WHERE l.tenantId = :t AND l.contactId = :c AND l.status IN :mo",
                        Object[].class)
                .setParameter("t", tenantId)
                .setParameter("c", contactId)
                .setParameter("mo", DANG_MO)
                .getResultStream().findFirst().map(LeadRepository::map);
    }

    public Optional<ContactRef> findContact(UUID tenantId, UUID contactId) {
        return em.createQuery("SELECT k FROM Contact k WHERE k.tenantId = :t AND k.id = :id", Contact.class)
                .setParameter("t", tenantId)
                .setParameter("id", contactId)
                .getResultStream().findFirst()
                .map(k -> new ContactRef(k.getId(), k.getStatus(), k.getDeletedAt() != null));
    }

    /** Khách của một hội thoại — {@code null} trong Optional nghĩa là hội thoại chưa gắn khách. */
    public Optional<Optional<UUID>> conversationContact(UUID tenantId, UUID conversationId) {
        // Optional ngoài: hội thoại có tồn tại không. Optional trong: hội thoại đã gắn khách chưa.
        List<Object[]> rows = em.createQuery(
                        "SELECT c.id, c.contactId FROM Conversation c WHERE c.tenantId = :t AND c.id = :id", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("id", conversationId)
                .getResultList();
        return rows.stream().findFirst().map(r -> Optional.ofNullable((UUID) r[1]));
    }

    /** Người dùng ĐANG HOẠT ĐỘNG của doanh nghiệp — trả tên, hoặc rỗng nếu không hợp lệ. */
    public Optional<String> activeUserName(UUID tenantId, UUID userId) {
        return em.createQuery("""
                SELECT u.fullName FROM User u
                WHERE u.tenantId = :t AND u.id = :id AND u.status = 'ACTIVE' AND u.deletedAt IS NULL""", String.class)
                .setParameter("t", tenantId)
                .setParameter("id", userId)
                .getResultStream().findFirst();
    }

    public Optional<UUID> convertedDealId(UUID tenantId, UUID leadId) {
        return em.createQuery("SELECT d.id FROM Deal d WHERE d.tenantId = :t AND d.leadId = :id", UUID.class)
                .setParameter("t", tenantId)
                .setParameter("id", leadId)
                .setMaxResults(1)
                .getResultStream().findFirst();
    }

    public int activityCount(UUID tenantId, UUID leadId) {
        return em.createQuery("SELECT count(a) FROM Activity a WHERE a.tenantId = :t AND a.leadId = :id", Long.class)
                .setParameter("t", tenantId)
                .setParameter("id", leadId)
                .getSingleResult().intValue();
    }

    /**
     * Lịch sử điểm, mới nhất trước (UC032 bước 6). Bảng chỉ ghi thêm — {@code sales.lead_scores}, V113.
     *
     * <p>Tạm giữ native SQL: Entity {@code LeadScore} do Dev A tạo cùng UC030/UC041 — không tạo trùng ở
     * đây. Đổi sang Entity đó khi nhánh của Dev A đã merge.
     */
    public List<ScoreRow> scores(UUID tenantId, UUID leadId, int limit) {
        List<?> rows = em.createNativeQuery("""
                SELECT score, model_version, top_factors::text AS top_factors, confidence, scored_at
                FROM sales.lead_scores WHERE tenant_id = :t AND lead_id = :id
                ORDER BY scored_at DESC LIMIT :lim""")
                .setParameter("t", tenantId)
                .setParameter("id", leadId)
                .setParameter("lim", limit)
                .getResultList();
        return rows.stream().map(o -> {
            Object[] r = (Object[]) o;
            return new ScoreRow(((Number) r[0]).intValue(), (String) r[1], (String) r[2], (String) r[3],
                    thoiDiem(r[4]));
        }).toList();
    }

    // ── ghi ─────────────────────────────────────────────────────────────────────

    public UUID insert(UUID tenantId, LeadDtos.CreateLeadRequest r, UUID ownerUserId) {
        Lead l = new Lead(tenantId, r.contactId(), LeadSource.MANUAL);
        l.setSourceConversationId(r.sourceConversationId());
        l.setInterestedProduct(r.interestedProduct());
        l.setBudgetMin(r.budgetMin());
        l.setBudgetMax(r.budgetMax());
        l.setUrgency(r.urgency() == null ? null : Level.valueOf(r.urgency()));
        l.setOwnerUserId(ownerUserId);
        em.persist(l);
        em.flush(); // vi phạm "một lead mở mỗi khách" nổ ngay tại đây, như INSERT trước đây
        return l.getId();
    }

    /** Ghi đè trọn các trường người dùng sửa được — service đã gộp giá trị cũ với phần thay đổi. */
    public void update(UUID tenantId, UUID leadId, String status, String interestedProduct, BigDecimal budgetMin,
                       BigDecimal budgetMax, String urgency, UUID ownerUserId, String disqualifiedReason) {
        managed(tenantId, leadId, LockModeType.NONE).ifPresent(l -> {
            l.setStatus(LeadStatus.valueOf(status));
            l.setInterestedProduct(interestedProduct);
            l.setBudgetMin(budgetMin);
            l.setBudgetMax(budgetMax);
            l.setUrgency(urgency == null ? null : Level.valueOf(urgency));
            l.setOwnerUserId(ownerUserId);
            l.setDisqualifiedReason(disqualifiedReason);
            ghiVaNapLai(l);
        });
    }

    /** UC033 — lead đã thành deal: khoá lại, giữ bản ghi (đặc tả b7). */
    public void markConverted(UUID tenantId, UUID leadId, UUID ownerUserId) {
        managed(tenantId, leadId, LockModeType.NONE).ifPresent(l -> {
            l.setStatus(LeadStatus.CONVERTED);
            l.setConvertedAt(Instant.now());
            l.setOwnerUserId(ownerUserId);
            ghiVaNapLai(l);
        });
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private Optional<Lead> managed(UUID tenantId, UUID leadId, LockModeType lock) {
        return em.createQuery("SELECT l FROM Lead l WHERE l.tenantId = :t AND l.id = :id", Lead.class)
                .setParameter("t", tenantId)
                .setParameter("id", leadId)
                .setLockMode(lock)
                .getResultStream().findFirst();
    }

    /**
     * Ghi xuống CSDL rồi nạp lại: {@code updated_at} do trigger đặt, mà service dùng nó làm mốc "đã loại"
     * ({@code closedAt}) ngay trong cùng request — không nạp lại thì trả về mốc cũ.
     */
    private void ghiVaNapLai(Lead l) {
        em.flush();
        em.refresh(l);
    }

    private static LeadRow map(Object[] r) {
        Lead l = (Lead) r[0];
        return new LeadRow(l.getId(), l.getContactId(), (String) r[1], (String) r[2], l.getSourceConversationId(),
                l.getSource().name(), l.getStatus().name(), l.getInterestedProduct(), l.getBudgetMin(),
                l.getBudgetMax(), l.getBudgetConfidence() == null ? null : l.getBudgetConfidence().name(),
                l.getUrgency() == null ? null : l.getUrgency().name(),
                l.getCurrentScore() == null ? null : l.getCurrentScore().intValue(), l.getScoreUpdatedAt(),
                l.getOwnerUserId(), (String) r[3], l.getDisqualifiedReason(), l.getConvertedAt(),
                l.getCreatedAt(), l.getUpdatedAt());
    }

    /** Native query trả {@code timestamptz} dưới dạng {@link Timestamp}, {@link OffsetDateTime} hoặc {@link Instant} tuỳ driver. */
    private static Instant thoiDiem(Object o) {
        if (o == null) {
            return null;
        }
        if (o instanceof Instant i) {
            return i;
        }
        if (o instanceof OffsetDateTime odt) {
            return odt.toInstant();
        }
        return ((Timestamp) o).toInstant();
    }

    /** Ký tự thoát của LIKE là {@code !} — xem {@code ESCAPE '!'} ở {@link #where}. */
    private static String escapeLike(String s) {
        return s.replace("!", "!!").replace("%", "!%").replace("_", "!_");
    }
}
