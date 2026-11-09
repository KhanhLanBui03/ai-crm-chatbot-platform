package com.thesis.crm.analytics.service;

import com.thesis.crm.analytics.dto.response.TopicDtos.KyPhanCum;
import com.thesis.crm.analytics.dto.response.TopicDtos.ThongKeChuDe;
import com.thesis.crm.analytics.entity.TopicConversation;
import com.thesis.crm.client.AiServiceClient;
import com.thesis.crm.client.AiServiceClient.TopicClusterRun;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.security.TenantTransactionScope;
import com.thesis.crm.security.TraceIdFilter;
import jakarta.persistence.EntityManager;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC038 bước 7–8 — đọc {@code analytics.topic_conversations} thành số liệu theo (ngày, chủ đề).
 *
 * <p>Gộp bằng JPQL {@code GROUP BY} trên Entity {@link TopicConversation}. Một hội thoại tính là "bị từ chối"
 * nếu có ít nhất một lượt từ chối trong chủ đề đó — khớp cách màn hình chia tỉ lệ theo số hội thoại.
 *
 * <p>Lớp {@code CLUSTER}: cụm và việc gán hội thoại vào cụm nằm ở ai-service (kỳ phân cụm hằng tuần, V215
 * bên đó); số liệu trả lời/từ chối của TỪNG hội thoại nằm ở đây (lớp {@code INTENT}). Ghép hai thứ lúc
 * đọc — AI không ghi bảng CRM (ADR-0002), và java-core không phải lưu lại một bản sao gán cụm.
 */
@Service
public class TopicReportService {

    static final int SO_NGAY_MAC_DINH = 30;
    /** Danh sách {@code IN} chia lô — Postgres giới hạn 32.767 tham số một câu. */
    static final int LO_IN = 1000;

    private final EntityManager em;
    private final TenantTransactionScope scope;
    private final AiServiceClient ai;

    public TopicReportService(EntityManager em, TenantTransactionScope scope, AiServiceClient ai) {
        this.em = em;
        this.scope = scope;
        this.ai = ai;
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
        if (TopicConversation.CLUSTER.equals(lop)) {
            return theoCum(tenantId, tu, den);
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

    /** Kỳ phân cụm đang dùng — {@code null} khi doanh nghiệp chưa có kỳ nào. Chỉ quản trị viên. */
    @Transactional(readOnly = true)
    public KyPhanCum kyPhanCum(UUID tenantId, boolean isAdmin) {
        if (!isAdmin) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN",
                    "Chỉ quản trị viên doanh nghiệp được xem thống kê chủ đề.");
        }
        return layKy(tenantId).map(k -> new KyPhanCum(k.status(), k.skipReason(), k.startedAt(), k.windowFrom(),
                k.windowTo(), k.conversationCount(), k.minConversations(), k.vectorSource(), k.k(), k.silhouette(),
                k.namingMethod())).orElse(null);
    }

    private Optional<TopicClusterRun> layKy(UUID tenantId) {
        try {
            return ai.latestTopicClusters(tenantId, MDC.get(TraceIdFilter.MDC_KEY));
        } catch (AiServiceException e) {
            throw new BusinessException(HttpStatus.SERVICE_UNAVAILABLE, "AI_SERVICE_UNAVAILABLE",
                    "Chưa lấy được cụm chủ đề từ dịch vụ AI — thử lại sau ít phút.");
        }
    }

    /**
     * Ghép gán cụm (ai-service) với số liệu từng hội thoại theo ngày (lớp INTENT ở đây). Hội thoại chạm
     * nhiều ý định trong một ngày được cộng các ý định lại thành MỘT hội thoại của cụm.
     */
    private List<ThongKeChuDe> theoCum(UUID tenantId, LocalDate tu, LocalDate den) {
        Optional<TopicClusterRun> ky = layKy(tenantId);
        if (ky.isEmpty() || !"DONE".equals(ky.get().status()) || ky.get().assignments() == null) {
            return List.of();
        }
        Map<UUID, TopicClusterRun.Cluster> cum = new HashMap<>();
        ky.get().clusters().forEach(c -> cum.put(c.clusterId(), c));
        Map<UUID, UUID> cumCua = new HashMap<>();
        ky.get().assignments().forEach(a -> cumCua.put(a.conversationId(), a.clusterId()));

        // (ngày, cụm) → [số hội thoại, tự xử lý, bị từ chối]
        Map<LocalDate, Map<UUID, long[]>> gop = new HashMap<>();
        List<UUID> ids = new ArrayList<>(cumCua.keySet());
        for (int i = 0; i < ids.size(); i += LO_IN) {
            List<Object[]> dong = em.createQuery("""
                            SELECT t.conversationId, t.statDate, sum(t.answeredCount), sum(t.refusalCount),
                                   sum(t.handoffCount)
                            FROM TopicConversation t
                            WHERE t.tenantId = :t AND t.dimension = :d AND t.statDate BETWEEN :tu AND :den
                              AND t.conversationId IN :ids
                            GROUP BY t.conversationId, t.statDate""", Object[].class)
                    .setParameter("t", tenantId)
                    .setParameter("d", TopicConversation.INTENT)
                    .setParameter("tu", tu)
                    .setParameter("den", den)
                    .setParameter("ids", ids.subList(i, Math.min(i + LO_IN, ids.size())))
                    .getResultList();
            for (Object[] r : dong) {
                UUID cumId = cumCua.get((UUID) r[0]);
                if (cumId == null || !cum.containsKey(cumId)) {
                    continue;
                }
                long traLoi = ((Number) r[2]).longValue();
                long tuChoi = ((Number) r[3]).longValue();
                long chuyenGiao = ((Number) r[4]).longValue();
                long[] so = gop.computeIfAbsent((LocalDate) r[1], d -> new HashMap<>())
                        .computeIfAbsent(cumId, c -> new long[3]);
                so[0]++;
                if (traLoi > 0 && tuChoi == 0 && chuyenGiao == 0) {
                    so[1]++;
                }
                if (tuChoi > 0) {
                    so[2]++;
                }
            }
        }
        List<ThongKeChuDe> kq = new ArrayList<>();
        gop.forEach((ngay, theoCum) -> theoCum.forEach((cumId, so) -> kq.add(new ThongKeChuDe(ngay,
                TopicConversation.CLUSTER, cumId.toString(), cumId, cum.get(cumId).label(), so[0], so[1], so[2]))));
        kq.sort(Comparator.comparing(ThongKeChuDe::statDate).thenComparing(ThongKeChuDe::topicLabel));
        return kq;
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
