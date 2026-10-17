package com.thesis.crm.sales.activity;

import com.thesis.crm.common.enums.LeadStatus;
import com.thesis.crm.sales.activity.ActivityDtos.ActivityDto;
import com.thesis.crm.sales.activity.ActivityDtos.TodoCount;
import com.thesis.crm.sales.entity.Activity;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import jakarta.persistence.TypedQuery;
import java.time.Instant;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * Truy cập dữ liệu UC035 qua Entity {@link Activity} (JPA). Mọi truy vấn lọc {@code tenantId} tường minh —
 * lớp thứ hai cạnh RLS. Gọi trong transaction đã {@code TenantTransactionScope.apply()}.
 *
 * <p>"Hôm nay" tính theo giờ Việt Nam — một định nghĩa cho cả danh sách lẫn số đỏ trên menu. "Bây giờ" là
 * {@code current_timestamp} của CSDL (mốc đầu transaction), như bản SQL trước.
 *
 * <p>Giữ nguyên chữ ký các hàm từ bản SQL tay, nên {@code ActivityService} không phải đổi.
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

    private static final ZoneId VN = ZoneId.of("Asia/Ho_Chi_Minh");

    /** Ghép tên khách, nhãn lead, tên deal, tên người làm/người được nhắc — cùng tenant. */
    private static final String SELECT = """
            SELECT a, coalesce(k.fullName, 'Khách chưa có tên'), coalesce(l.interestedProduct, 'Lead'), d.title,
                   coalesce(pu.fullName, pu.email), coalesce(ru.fullName, ru.email)
            FROM Activity a
            JOIN Contact k ON k.id = a.contactId AND k.tenantId = a.tenantId
            LEFT JOIN Lead l ON l.id = a.leadId AND l.tenantId = a.tenantId
            LEFT JOIN Deal d ON d.id = a.dealId AND d.tenantId = a.tenantId
            LEFT JOIN User pu ON pu.id = a.performedBy AND pu.tenantId = a.tenantId
            LEFT JOIN User ru ON ru.id = a.remindUserId AND ru.tenantId = a.tenantId
            """;

    private final EntityManager em;

    public ActivityRepository(EntityManager em) {
        this.em = em;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    /** "Việc của tôi" sắp theo giờ nhắc gần nhất; còn lại theo thời điểm thực hiện mới nhất. */
    public List<ActivityDto> search(UUID tenantId, Filter f) {
        Map<String, Object> p = new HashMap<>();
        String order = f.mineUserId() != null
                ? " ORDER BY a.remindAt, a.id"
                : " ORDER BY coalesce(a.performedAt, a.createdAt) DESC, a.id";
        TypedQuery<Object[]> q = em.createQuery(SELECT + where(tenantId, f, p) + order, Object[].class)
                .setFirstResult(f.page() * f.size())
                .setMaxResults(f.size());
        p.forEach(q::setParameter);
        return q.getResultList().stream().map(ActivityRepository::map).toList();
    }

    public long count(UUID tenantId, Filter f) {
        Map<String, Object> p = new HashMap<>();
        TypedQuery<Long> q = em.createQuery("SELECT count(a) FROM Activity a" + where(tenantId, f, p), Long.class);
        p.forEach(q::setParameter);
        return q.getSingleResult();
    }

    private static String where(UUID tenantId, Filter f, Map<String, Object> p) {
        StringBuilder w = new StringBuilder(" WHERE a.tenantId = :t");
        p.put("t", tenantId);
        if (f.contactId() != null) {
            w.append(" AND a.contactId = :contact");
            p.put("contact", f.contactId());
        }
        if (f.leadId() != null) {
            w.append(" AND a.leadId = :lead");
            p.put("lead", f.leadId());
        }
        if (f.dealId() != null) {
            w.append(" AND a.dealId = :deal");
            p.put("deal", f.dealId());
        }
        if (f.type() != null) {
            w.append(" AND a.type = :type");
            p.put("type", f.type());
        }
        if (f.remindStatus() != null) {
            w.append(" AND a.remindStatus = :rs");
            p.put("rs", f.remindStatus());
        }
        if (f.mineUserId() != null) {
            // Việc của tôi = lời nhắc giao cho tôi, chưa xong, chưa huỷ
            w.append(" AND a.remindUserId = :me AND a.remindStatus IN ('PENDING', 'SENT')");
            p.put("me", f.mineUserId());
            if ("OVERDUE".equals(f.bucket())) {
                w.append(" AND a.remindAt < current_timestamp");
            } else if ("TODAY".equals(f.bucket())) {
                w.append(" AND a.remindAt >= current_timestamp AND a.remindAt < :cuoiHomNay");
                p.put("cuoiHomNay", cuoiHomNay());
            } else if ("UPCOMING".equals(f.bucket())) {
                w.append(" AND a.remindAt >= :cuoiHomNay");
                p.put("cuoiHomNay", cuoiHomNay());
            }
        }
        return w.toString();
    }

    public Optional<ActivityDto> find(UUID tenantId, UUID id) {
        return em.createQuery(SELECT + " WHERE a.tenantId = :t AND a.id = :id", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("id", id)
                .getResultStream().findFirst().map(ActivityRepository::map);
    }

    /** Khoá dòng ({@code SELECT … FOR UPDATE}) để hai người sửa cùng lúc không đè nhau. */
    public Optional<Owner> lock(UUID tenantId, UUID id) {
        return em.createQuery("SELECT a FROM Activity a WHERE a.tenantId = :t AND a.id = :id", Activity.class)
                .setParameter("t", tenantId)
                .setParameter("id", id)
                .setLockMode(LockModeType.PESSIMISTIC_WRITE)
                .getResultStream().findFirst()
                .map(a -> new Owner(a.getId(), a.getSource(), a.getPerformedBy(), a.getRemindUserId(),
                        a.getRemindStatus(), a.getRemindAt()));
    }

    public TodoCount todoCount(UUID tenantId, UUID userId) {
        Object[] r = em.createQuery("""
                SELECT sum(CASE WHEN a.remindAt < current_timestamp THEN 1 ELSE 0 END),
                       sum(CASE WHEN a.remindAt >= current_timestamp AND a.remindAt < :cuoiHomNay THEN 1 ELSE 0 END)
                FROM Activity a
                WHERE a.tenantId = :t AND a.remindUserId = :u AND a.remindStatus IN ('PENDING', 'SENT')
                """, Object[].class)
                .setParameter("t", tenantId)
                .setParameter("u", userId)
                .setParameter("cuoiHomNay", cuoiHomNay())
                .getSingleResult();
        // Không có dòng nào thì sum() trả null
        return new TodoCount(soNguyen(r[0]), soNguyen(r[1]));
    }

    /** Khách của lead / deal — để chặn gắn hoạt động của khách A vào lead của khách B. */
    public Optional<UUID> contactOfLead(UUID tenantId, UUID leadId) {
        return motId("SELECT l.contactId FROM Lead l WHERE l.tenantId = :t AND l.id = :id", tenantId, leadId);
    }

    public Optional<UUID> contactOfDeal(UUID tenantId, UUID dealId) {
        return motId("SELECT d.contactId FROM Deal d WHERE d.tenantId = :t AND d.id = :id", tenantId, dealId);
    }

    /** Khách của hội thoại (có thể chưa gắn khách → rỗng). */
    public Optional<UUID> contactOfConversation(UUID tenantId, UUID conversationId) {
        return motId("SELECT c.contactId FROM Conversation c WHERE c.tenantId = :t AND c.id = :id",
                tenantId, conversationId);
    }

    /** Deal ĐANG MỞ mới nhất của khách — nơi gắn hoạt động AUTO đầu tiên. */
    public Optional<UUID> latestOpenDeal(UUID tenantId, UUID contactId) {
        return motId("""
                SELECT d.id FROM Deal d WHERE d.tenantId = :t AND d.contactId = :id AND d.status = 'OPEN'
                ORDER BY d.createdAt DESC""", tenantId, contactId);
    }

    /** Lead ĐANG MỞ của khách (tối đa một — V132). */
    public Optional<UUID> openLead(UUID tenantId, UUID contactId) {
        return em.createQuery("""
                SELECT l.id FROM Lead l WHERE l.tenantId = :t AND l.contactId = :c AND l.status IN :mo""", UUID.class)
                .setParameter("t", tenantId)
                .setParameter("c", contactId)
                .setParameter("mo", List.of(LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED))
                .setMaxResults(1)
                .getResultStream().findFirst();
    }

    // ── ghi ─────────────────────────────────────────────────────────────────────

    public UUID insert(UUID tenantId, NewActivity n) {
        Activity a = new Activity(tenantId, n.contactId(), n.type(), n.source(), n.performedBy());
        a.setLeadId(n.leadId());
        a.setDealId(n.dealId());
        a.setConversationId(n.conversationId());
        a.setSubject(n.subject());
        a.setContent(n.content());
        a.setOutcome(n.outcome());
        a.setPerformedAt(n.performedAt() != null ? n.performedAt() : Instant.now());
        a.setReminder(n.remindAt(), n.remindUserId(), n.remindAt() == null ? "NONE" : "PENDING");
        em.persist(a);
        em.flush(); // lỗi ràng buộc nổ ngay tại đây, như INSERT trước đây
        return a.getId();
    }

    public void update(UUID tenantId, UUID id, String outcome, String content, Instant remindAt, UUID remindUserId,
                       String remindStatus) {
        em.createQuery("SELECT a FROM Activity a WHERE a.tenantId = :t AND a.id = :id", Activity.class)
                .setParameter("t", tenantId)
                .setParameter("id", id)
                .getResultStream().findFirst()
                .ifPresent(a -> {
                    a.setOutcome(outcome);
                    a.setContent(content);
                    a.setReminder(remindAt, remindUserId, remindStatus);
                });
        em.flush();
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private Optional<UUID> motId(String jpql, UUID tenantId, UUID id) {
        return em.createQuery(jpql, UUID.class)
                .setParameter("t", tenantId)
                .setParameter("id", id)
                .setMaxResults(1)
                .getResultStream().findFirst();
    }

    /** Nửa đêm sắp tới theo giờ Việt Nam. */
    private static Instant cuoiHomNay() {
        return java.time.LocalDate.now(VN).plusDays(1).atStartOfDay(VN).toInstant();
    }

    private static int soNguyen(Object o) {
        return o == null ? 0 : ((Number) o).intValue();
    }

    private static ActivityDto map(Object[] r) {
        Activity a = (Activity) r[0];
        return new ActivityDto(a.getId(), a.getContactId(), (String) r[1], a.getLeadId(),
                a.getLeadId() == null ? null : (String) r[2], a.getDealId(), (String) r[3],
                a.getConversationId(), a.getType(), a.getSubject(), a.getContent(), a.getOutcome(), a.getSource(),
                a.getPerformedBy(), (String) r[4], a.getPerformedAt(), a.getRemindAt(), a.getRemindUserId(),
                (String) r[5], a.getRemindStatus(), a.getCreatedAt());
    }
}
