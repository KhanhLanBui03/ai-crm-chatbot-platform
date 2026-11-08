package com.thesis.crm.platform.service;

import com.thesis.crm.analytics.entity.TopicConversation;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.security.TenantTransactionScope;
import jakarta.persistence.EntityManager;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC006 bước 5–7 — mức sử dụng theo ngày, tách theo kênh HOẶC theo nhánh xử lý (SCR015).
 *
 * <p>Token, chi phí, số lượt, lượt dùng đệm: cộng trên {@code analytics.metrics_daily} (UC039 dựng từ sự kiện
 * {@code ai.turn.completed}). Số hội thoại:
 * <ul>
 *   <li>theo kênh — đếm hội thoại MỞ trong ngày ở {@code engagement.conversations}: một hội thoại thuộc đúng một
 *       kênh và tính một lần (trục thu phí của gói);</li>
 *   <li>theo nhánh — đếm hội thoại có ít nhất một lượt đi qua nhánh đó trong ngày ({@code topic_conversations},
 *       chiều ROUTE). Một hội thoại có thể có mặt ở nhiều nhánh — vì thế không gộp hai chiều (đặc tả 6.1).</li>
 * </ul>
 * Ngày tính theo múi giờ doanh nghiệp. Chỉ quản trị viên.
 */
@Service
public class UsageDailyService {

    static final int SO_NGAY_MAC_DINH = 30;
    static final int CO_TRANG_TOI_DA = 100;

    /** Một dòng của SCR015 — khớp {@code DiemSuDungNgay} trong {@code dashboard-api.yaml}. */
    public record DiemSuDungNgay(
            LocalDate statDate,
            String channelType,
            String route,
            long conversations,
            long turns,
            long promptTokens,
            long completionTokens,
            BigDecimal costVnd,
            long cachedHits) {
    }

    private final EntityManager em;
    private final TenantTransactionScope scope;

    public UsageDailyService(EntityManager em, TenantTransactionScope scope) {
        this.em = em;
        this.scope = scope;
    }

    @Transactional(readOnly = true)
    public PageResponse<DiemSuDungNgay> daily(UUID tenantId, boolean isAdmin, String groupBy, LocalDate from,
            LocalDate to, String sort, int page, int size) {
        if (!isAdmin) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN",
                    "Chỉ quản trị viên doanh nghiệp được xem mức sử dụng theo ngày.");
        }
        boolean theoKenh = groupBy == null || groupBy.isBlank() || "channel".equals(groupBy);
        if (!theoKenh && !"route".equals(groupBy)) {
            // Đặc tả 6.1: không có chế độ gộp hai chiều
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_GROUP_BY",
                    "groupBy chỉ nhận channel hoặc route — gộp hai chiều sẽ đếm một hội thoại nhiều lần.");
        }
        scope.apply(tenantId);
        ZoneId zone = muiGio(tenantId);
        LocalDate den = to != null ? to : LocalDate.now(zone);
        LocalDate tu = from != null ? from : den.minusDays(SO_NGAY_MAC_DINH - 1L);
        if (tu.isAfter(den)) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_RANGE", "Ngày bắt đầu sau ngày kết thúc.");
        }

        Map<UUID, String> loaiKenh = new HashMap<>();
        em.createQuery("SELECT c.id, c.type FROM Channel c WHERE c.tenantId = :t", Object[].class)
                .setParameter("t", tenantId)
                .getResultList()
                .forEach(r -> loaiKenh.put((UUID) r[0], (String) r[1]));

        // (ngày, khoá chiều) → số liệu đang cộng. Khoá null = lượt không gắn được kênh (hội thoại đã xoá).
        Map<LocalDate, Map<String, long[]>> so = new HashMap<>();
        Map<LocalDate, Map<String, BigDecimal>> phi = new HashMap<>();
        String nhom = theoKenh ? "m.channelId" : "m.branch";
        List<Object[]> dong = em.createQuery("SELECT m.metricDate, " + nhom + ", sum(m.interactionCount), "
                        + "sum(m.promptTokens), sum(m.completionTokens), sum(m.costVnd), sum(m.cachedCount) "
                        + "FROM MetricsDaily m WHERE m.tenantId = :t AND m.metricDate BETWEEN :tu AND :den "
                        + "GROUP BY m.metricDate, " + nhom, Object[].class)
                .setParameter("t", tenantId)
                .setParameter("tu", tu)
                .setParameter("den", den)
                .getResultList();
        for (Object[] r : dong) {
            LocalDate ngay = (LocalDate) r[0];
            String khoa = theoKenh ? (r[1] == null ? null : loaiKenh.get((UUID) r[1])) : (String) r[1];
            long[] v = o(so, ngay, khoa);
            v[1] += ((Number) r[2]).longValue();
            v[2] += ((Number) r[3]).longValue();
            v[3] += ((Number) r[4]).longValue();
            v[4] += ((Number) r[6]).longValue();
            phi.computeIfAbsent(ngay, d -> new HashMap<>()).merge(khoa,
                    r[5] == null ? BigDecimal.ZERO : (BigDecimal) r[5], BigDecimal::add);
        }

        if (theoKenh) {
            Instant dau = tu.atStartOfDay(zone).toInstant();
            Instant cuoi = den.plusDays(1).atStartOfDay(zone).toInstant();
            em.createQuery("""
                            SELECT c.createdAt, c.channelId FROM Conversation c
                            WHERE c.tenantId = :t AND c.createdAt >= :dau AND c.createdAt < :cuoi""", Object[].class)
                    .setParameter("t", tenantId)
                    .setParameter("dau", dau)
                    .setParameter("cuoi", cuoi)
                    .getResultList()
                    .forEach(r -> o(so, ((Instant) r[0]).atZone(zone).toLocalDate(), loaiKenh.get((UUID) r[1]))[0]++);
        } else {
            em.createQuery("""
                            SELECT t.statDate, t.topicKey, count(t) FROM TopicConversation t
                            WHERE t.tenantId = :t AND t.dimension = :d AND t.statDate BETWEEN :tu AND :den
                            GROUP BY t.statDate, t.topicKey""", Object[].class)
                    .setParameter("t", tenantId)
                    .setParameter("d", TopicConversation.ROUTE)
                    .setParameter("tu", tu)
                    .setParameter("den", den)
                    .getResultList()
                    .forEach(r -> o(so, (LocalDate) r[0], (String) r[1])[0] += ((Number) r[2]).longValue());
        }

        List<DiemSuDungNgay> ds = new ArrayList<>();
        so.forEach((ngay, theoKhoa) -> theoKhoa.forEach((khoa, v) -> ds.add(new DiemSuDungNgay(ngay,
                theoKenh ? khoa : null, theoKenh ? null : khoa, v[0], v[1], v[2], v[3],
                phi.getOrDefault(ngay, Map.of()).getOrDefault(khoa, BigDecimal.ZERO), v[4]))));
        ds.sort(thuTu(sort));

        int co = Math.min(Math.max(size, 1), CO_TRANG_TOI_DA);
        int trang = Math.max(page, 0);
        int dau = Math.min(trang * co, ds.size());
        return PageResponse.of(ds.subList(dau, Math.min(dau + co, ds.size())), trang, co, ds.size());
    }

    /** [hội thoại, lượt, token vào, token ra, lượt dùng đệm] */
    private static long[] o(Map<LocalDate, Map<String, long[]>> so, LocalDate ngay, String khoa) {
        return so.computeIfAbsent(ngay, d -> new HashMap<>()).computeIfAbsent(khoa, k -> new long[5]);
    }

    /** {@code -statDate} (mặc định) · {@code statDate} · {@code ±conversations|promptTokens|completionTokens|costVnd}. */
    static Comparator<DiemSuDungNgay> thuTu(String sort) {
        String s = sort == null || sort.isBlank() ? "-statDate" : sort.strip();
        boolean giam = s.startsWith("-");
        String truong = giam ? s.substring(1) : s;
        Comparator<DiemSuDungNgay> c = switch (truong) {
            case "conversations" -> Comparator.comparingLong(DiemSuDungNgay::conversations);
            case "promptTokens" -> Comparator.comparingLong(DiemSuDungNgay::promptTokens);
            case "completionTokens" -> Comparator.comparingLong(DiemSuDungNgay::completionTokens);
            case "costVnd" -> Comparator.comparing(DiemSuDungNgay::costVnd);
            default -> Comparator.comparing(DiemSuDungNgay::statDate);
        };
        if (giam) {
            c = c.reversed();
        }
        // Cùng giá trị thì xếp theo khoá chiều cho thứ tự ổn định giữa các trang
        return c.thenComparing(d -> Objects.toString(d.channelType() != null ? d.channelType() : d.route(), ""));
    }

    private ZoneId muiGio(UUID tenantId) {
        Tenant t = em.find(Tenant.class, tenantId);
        try {
            return ZoneId.of(t == null || t.getTimezone() == null ? "Asia/Ho_Chi_Minh" : t.getTimezone());
        } catch (Exception e) {
            return ZoneId.of("Asia/Ho_Chi_Minh");
        }
    }
}
