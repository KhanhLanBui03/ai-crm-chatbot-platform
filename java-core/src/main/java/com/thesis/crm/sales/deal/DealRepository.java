package com.thesis.crm.sales.deal;

import com.thesis.crm.sales.deal.DealDtos.HistoryDto;
import com.thesis.crm.sales.entity.Deal;
import com.thesis.crm.sales.entity.DealStage;
import com.thesis.crm.sales.entity.DealStageHistory;
import com.thesis.crm.sales.entity.Pipeline;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import jakarta.persistence.TypedQuery;
import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * Truy cập dữ liệu UC033 + UC034 qua Entity {@link Deal}, {@link DealStage}, {@link Pipeline},
 * {@link DealStageHistory} (JPA). Mọi truy vấn lọc {@code tenantId} tường minh — lớp thứ hai cạnh RLS.
 * Gọi trong transaction đã {@code TenantTransactionScope.apply()}.
 *
 * <p>Giữ nguyên chữ ký các hàm từ bản SQL tay, nên {@code DealService} không phải đổi.
 */
@Repository
public class DealRepository {

    public record PipelineRow(UUID id, String name, boolean isDefault, boolean isActive) {}

    public record StageRow(UUID id, UUID pipelineId, String name, int position, Integer probability,
                           boolean won, boolean lost, List<String> requiredFields, int dealCount,
                           BigDecimal dealValueTotal) {
        boolean closing() {
            return won || lost;
        }
    }

    public record DealRow(
            UUID id, UUID contactId, String contactName, UUID leadId, UUID pipelineId, UUID stageId,
            String stageName, String title, BigDecimal amount, String currency, LocalDate expectedCloseDate,
            boolean overdue, String status, String source, UUID ownerUserId, String ownerName,
            Instant stageChangedAt, Instant createdAt, String closeReason, Instant closedAt) {}

    public record Filter(UUID pipelineId, UUID stageId, String status, UUID ownerUserId, UUID contactId, int page,
                         int size) {}

    public record NewDeal(UUID contactId, UUID leadId, UUID pipelineId, UUID stageId, String title,
                          BigDecimal amount, LocalDate expectedCloseDate, String source, UUID ownerUserId) {}

    private static final ZoneId VN = ZoneId.of("Asia/Ho_Chi_Minh");

    /** Deal kèm tên giai đoạn, tên khách, tên người phụ trách — cùng tenant. */
    private static final String SELECT = """
            SELECT d, s.name, coalesce(k.fullName, 'Khách chưa có tên'), u.fullName
            FROM Deal d
            JOIN DealStage s ON s.id = d.stageId AND s.tenantId = d.tenantId
            JOIN Contact k ON k.id = d.contactId AND k.tenantId = d.tenantId
            LEFT JOIN User u ON u.id = d.ownerUserId AND u.tenantId = d.tenantId
            """;

    private final EntityManager em;

    public DealRepository(EntityManager em) {
        this.em = em;
    }

    // ── phễu ────────────────────────────────────────────────────────────────────

    public List<PipelineRow> pipelines(UUID tenantId, boolean includeInactive) {
        return em.createQuery("""
                SELECT p FROM Pipeline p
                WHERE p.tenantId = :t AND (:all = true OR p.isActive = true)
                ORDER BY p.isDefault DESC, p.name""", Pipeline.class)
                .setParameter("t", tenantId)
                .setParameter("all", includeInactive)
                .getResultStream()
                .map(p -> new PipelineRow(p.getId(), p.getName(), p.isDefault(), p.isActive()))
                .toList();
    }

    /** Giai đoạn kèm số deal và tổng giá trị — cột Kanban cần cả hai trước khi vẽ. */
    public List<StageRow> stagesWithTotals(UUID tenantId) {
        return em.createQuery("""
                SELECT s, count(d.id), coalesce(sum(d.amount), 0)
                FROM DealStage s
                LEFT JOIN Deal d ON d.stageId = s.id AND d.tenantId = s.tenantId
                WHERE s.tenantId = :t
                GROUP BY s.id
                ORDER BY s.pipelineId, s.position""", Object[].class)
                .setParameter("t", tenantId)
                .getResultStream()
                .map(r -> stageRow((DealStage) r[0], ((Number) r[1]).intValue(), soTien(r[2])))
                .toList();
    }

    public Optional<StageRow> stage(UUID tenantId, UUID stageId) {
        return em.createQuery("""
                SELECT s FROM DealStage s
                JOIN Pipeline p ON p.id = s.pipelineId AND p.tenantId = s.tenantId AND p.isActive = true
                WHERE s.tenantId = :t AND s.id = :id""", DealStage.class)
                .setParameter("t", tenantId)
                .setParameter("id", stageId)
                .getResultStream().findFirst()
                .map(s -> stageRow(s, 0, BigDecimal.ZERO));
    }

    /** Giai đoạn MỞ đầu tiên của phễu mặc định — nơi deal mới vào khi không chỉ định. */
    public Optional<StageRow> defaultFirstStage(UUID tenantId) {
        return em.createQuery("""
                SELECT s FROM DealStage s
                JOIN Pipeline p ON p.id = s.pipelineId AND p.tenantId = s.tenantId
                WHERE s.tenantId = :t AND p.isDefault = true AND p.isActive = true
                  AND s.won = false AND s.lost = false
                ORDER BY s.position""", DealStage.class)
                .setParameter("t", tenantId)
                .setMaxResults(1)
                .getResultStream().findFirst()
                .map(s -> stageRow(s, 0, BigDecimal.ZERO));
    }

    // ── deal: đọc ───────────────────────────────────────────────────────────────

    public List<DealRow> search(UUID tenantId, Filter f) {
        Map<String, Object> p = new HashMap<>();
        // Dấu cách đầu chuỗi là bắt buộc: text block cắt khoảng trắng đầu dòng → ":contactORDER BY"
        TypedQuery<Object[]> q = em.createQuery(SELECT + where(tenantId, f, p)
                        + " ORDER BY s.position, d.expectedCloseDate NULLS LAST, d.createdAt DESC, d.id", Object[].class)
                .setFirstResult(f.page() * f.size())
                .setMaxResults(f.size());
        p.forEach(q::setParameter);
        LocalDate homNay = LocalDate.now(VN);
        return q.getResultStream().map(r -> map(r, homNay)).toList();
    }

    public long count(UUID tenantId, Filter f) {
        Map<String, Object> p = new HashMap<>();
        TypedQuery<Long> q = em.createQuery("SELECT count(d) FROM Deal d" + where(tenantId, f, p), Long.class);
        p.forEach(q::setParameter);
        return q.getSingleResult();
    }

    private static String where(UUID tenantId, Filter f, Map<String, Object> p) {
        StringBuilder w = new StringBuilder(" WHERE d.tenantId = :t");
        p.put("t", tenantId);
        if (f.pipelineId() != null) {
            w.append(" AND d.pipelineId = :pipeline");
            p.put("pipeline", f.pipelineId());
        }
        if (f.stageId() != null) {
            w.append(" AND d.stageId = :stage");
            p.put("stage", f.stageId());
        }
        if (f.status() != null) {
            w.append(" AND d.status = :status");
            p.put("status", f.status());
        }
        if (f.ownerUserId() != null) {
            w.append(" AND d.ownerUserId = :owner");
            p.put("owner", f.ownerUserId());
        }
        if (f.contactId() != null) {
            w.append(" AND d.contactId = :contact");
            p.put("contact", f.contactId());
        }
        return w.toString();
    }

    public Optional<DealRow> find(UUID tenantId, UUID dealId) {
        LocalDate homNay = LocalDate.now(VN);
        return em.createQuery(SELECT + " WHERE d.tenantId = :t AND d.id = :id", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("id", dealId)
                .getResultStream().findFirst()
                .map(r -> map(r, homNay));
    }

    /** Khoá dòng ({@code SELECT … FOR UPDATE}) — hai người kéo cùng một deal không đè nhau. */
    public boolean lock(UUID tenantId, UUID dealId) {
        return managed(tenantId, dealId, LockModeType.PESSIMISTIC_WRITE).isPresent();
    }

    /** Số deal ĐANG MỞ của khách — UC033: có thì cảnh báo, không chặn. */
    public int openDealsOfContact(UUID tenantId, UUID contactId) {
        return em.createQuery("""
                SELECT count(d) FROM Deal d WHERE d.tenantId = :t AND d.contactId = :c AND d.status = 'OPEN'""",
                Long.class)
                .setParameter("t", tenantId)
                .setParameter("c", contactId)
                .getSingleResult().intValue();
    }

    public List<HistoryDto> history(UUID tenantId, UUID dealId) {
        return em.createQuery("""
                SELECT h, f.name, t2.name, u.fullName
                FROM DealStageHistory h
                JOIN DealStage t2 ON t2.id = h.toStageId AND t2.tenantId = h.tenantId
                LEFT JOIN DealStage f ON f.id = h.fromStageId AND f.tenantId = h.tenantId
                LEFT JOIN User u ON u.id = h.changedBy AND u.tenantId = h.tenantId
                WHERE h.tenantId = :t AND h.dealId = :id
                ORDER BY h.changedAt, h.id""", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("id", dealId)
                .getResultStream()
                .map(r -> {
                    DealStageHistory h = (DealStageHistory) r[0];
                    return new HistoryDto(h.getFromStageId(), (String) r[1], h.getToStageId(), (String) r[2],
                            h.getDurationSeconds(), (String) r[3], h.getChangedAt());
                })
                .toList();
    }

    // ── deal: ghi ───────────────────────────────────────────────────────────────

    public UUID insert(UUID tenantId, NewDeal n) {
        Deal d = new Deal(tenantId, n.contactId(), n.pipelineId(), n.stageId(), n.title(), n.source());
        d.setLeadId(n.leadId());
        d.setAmount(n.amount());
        d.setExpectedCloseDate(n.expectedCloseDate());
        d.setOwnerUserId(n.ownerUserId());
        em.persist(d);
        em.flush(); // lỗi ràng buộc nổ ngay tại đây, như INSERT trước đây
        return d.getId();
    }

    public void updateFields(UUID tenantId, UUID dealId, String title, BigDecimal amount, LocalDate date, UUID owner) {
        managed(tenantId, dealId, LockModeType.NONE).ifPresent(d -> {
            d.setTitle(title);
            d.setAmount(amount);
            d.setExpectedCloseDate(date);
            d.setOwnerUserId(owner);
        });
        em.flush();
    }

    /** Đổi giai đoạn và trạng thái đóng/mở trong MỘT câu UPDATE — ràng buộc không thấy trạng thái lưng chừng. */
    public void moveStage(UUID tenantId, UUID dealId, UUID stageId, String status, String closeReason, UUID owner) {
        Instant now = Instant.now();
        managed(tenantId, dealId, LockModeType.NONE).ifPresent(d -> {
            d.setStageId(stageId);
            d.setStatus(status, now);
            d.setStageChangedAt(now);
            d.setCloseReason(closeReason);
            d.setOwnerUserId(owner);
        });
        em.flush();
    }

    /** Đổi lý do thua khi deal vẫn ở cột Thua — không đụng mốc vào giai đoạn, không sinh dòng lịch sử. */
    public void updateCloseReason(UUID tenantId, UUID dealId, String reason) {
        managed(tenantId, dealId, LockModeType.NONE).ifPresent(d -> d.setCloseReason(reason));
        em.flush();
    }

    /** Ghi lịch sử; {@code from = null} là dòng tạo deal. Thời gian ở giai đoạn trước tính bằng giây. */
    public void insertHistory(UUID tenantId, UUID dealId, UUID fromStageId, UUID toStageId, Instant enteredFromAt,
                              UUID changedBy) {
        Instant now = Instant.now();
        Long duration = fromStageId == null || enteredFromAt == null
                ? null
                : Math.max(0, Duration.between(enteredFromAt, now).getSeconds());
        em.persist(new DealStageHistory(tenantId, dealId, fromStageId, toStageId, duration, changedBy, now));
        em.flush();
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private Optional<Deal> managed(UUID tenantId, UUID dealId, LockModeType lock) {
        return em.createQuery("SELECT d FROM Deal d WHERE d.tenantId = :t AND d.id = :id", Deal.class)
                .setParameter("t", tenantId)
                .setParameter("id", dealId)
                .setLockMode(lock)
                .getResultStream().findFirst();
    }

    private static StageRow stageRow(DealStage s, int count, BigDecimal total) {
        String[] req = s.getRequiredFields();
        return new StageRow(s.getId(), s.getPipelineId(), s.getName(), s.getPosition(),
                s.getProbability() == null ? null : s.getProbability().intValue(), s.isWon(), s.isLost(),
                req == null ? List.of() : List.of(req), count, total);
    }

    private static BigDecimal soTien(Object o) {
        return o instanceof BigDecimal b ? b : new BigDecimal(o.toString());
    }

    /** "Quá hạn" theo ngày ở Việt Nam — một định nghĩa cho mọi màn hình (hợp đồng {@code isOverdue}). */
    private static DealRow map(Object[] r, LocalDate homNay) {
        Deal d = (Deal) r[0];
        boolean overdue = "OPEN".equals(d.getStatus()) && d.getExpectedCloseDate() != null
                && d.getExpectedCloseDate().isBefore(homNay);
        return new DealRow(d.getId(), d.getContactId(), (String) r[2], d.getLeadId(), d.getPipelineId(),
                d.getStageId(), (String) r[1], d.getTitle(), d.getAmount(), d.getCurrency(), d.getExpectedCloseDate(),
                overdue, d.getStatus(), d.getSource(), d.getOwnerUserId(), (String) r[3], d.getStageChangedAt(),
                d.getCreatedAt(), d.getCloseReason(), d.getClosedAt());
    }
}
