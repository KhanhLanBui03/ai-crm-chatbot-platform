package com.thesis.crm.analytics.service;

import com.thesis.crm.analytics.dto.response.TopicDtos.ThongKeChuDe;
import com.thesis.crm.analytics.entity.TopicConversation;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.security.TenantTransactionScope;
import jakarta.persistence.EntityManager;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC038 bước 7–8 — đọc {@code analytics.topic_conversations} thành số liệu theo (ngày, chủ đề).
 *
 * <p>Gộp bằng JPQL {@code GROUP BY} trên Entity {@link TopicConversation}. Một hội thoại tính là "bị từ chối"
 * nếu có ít nhất một lượt từ chối trong chủ đề đó — khớp cách màn hình chia tỉ lệ theo số hội thoại.
 */
@Service
public class TopicReportService {

    static final int SO_NGAY_MAC_DINH = 30;

    private final EntityManager em;
    private final TenantTransactionScope scope;

    public TopicReportService(EntityManager em, TenantTransactionScope scope) {
        this.em = em;
        this.scope = scope;
    }

    @Transactional(readOnly = true)
    public List<ThongKeChuDe> report(UUID tenantId, boolean isAdmin, String dimension, LocalDate from, LocalDate to) {
        if (!isAdmin) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN",
                    "Chỉ quản trị viên doanh nghiệp được xem thống kê chủ đề.");
        }
        String lop = dimension == null || dimension.isBlank() ? TopicConversation.INTENT
                : dimension.strip().toUpperCase(Locale.ROOT);
        if (!TopicConversation.INTENT.equals(lop) && !TopicConversation.CLUSTER.equals(lop)) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_DIMENSION",
                    "dimension chỉ nhận INTENT hoặc CLUSTER.");
        }
        scope.apply(tenantId);
        LocalDate den = to != null ? to : LocalDate.now(muiGio(tenantId));
        LocalDate tu = from != null ? from : den.minusDays(SO_NGAY_MAC_DINH - 1L);
        if (tu.isAfter(den)) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_RANGE", "Ngày bắt đầu sau ngày kết thúc.");
        }

        List<Object[]> dong = em.createQuery("""
                        SELECT t.statDate, t.topicKey, max(t.topicLabel), count(t),
                               sum(CASE WHEN t.answeredCount > 0 AND t.refusalCount = 0 AND t.handoffCount = 0
                                        THEN 1 ELSE 0 END),
                               sum(CASE WHEN t.refusalCount > 0 THEN 1 ELSE 0 END)
                        FROM TopicConversation t
                        WHERE t.tenantId = :t AND t.dimension = :d AND t.statDate BETWEEN :tu AND :den
                        GROUP BY t.statDate, t.topicKey
                        ORDER BY t.statDate, t.topicKey""", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("d", lop)
                .setParameter("tu", tu)
                .setParameter("den", den)
                .getResultList();

        return dong.stream().map(r -> new ThongKeChuDe(
                (LocalDate) r[0],
                lop,
                (String) r[1],
                TopicConversation.CLUSTER.equals(lop) ? uuid((String) r[1]) : null,
                (String) r[2],
                ((Number) r[3]).longValue(),
                ((Number) r[4]).longValue(),
                ((Number) r[5]).longValue())).toList();
    }

    private static UUID uuid(String s) {
        try {
            return UUID.fromString(s);
        } catch (IllegalArgumentException e) {
            return null;
        }
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
