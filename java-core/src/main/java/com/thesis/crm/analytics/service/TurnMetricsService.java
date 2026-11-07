package com.thesis.crm.analytics.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.analytics.entity.MetricsDaily;
import com.thesis.crm.analytics.entity.MetricsDaily.LuotXong;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.security.TenantTransactionScope;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import jakarta.persistence.TypedQuery;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC039 bước 3–4 — cộng MỘT sự kiện {@code ai.turn.completed} vào {@code analytics.metrics_daily}.
 *
 * <p>Chống trùng theo cặp (nhóm tiêu thụ, mã sự kiện) ở {@code analytics.processed_events} TRONG CÙNG
 * transaction với phép cộng: cộng xong mà chưa kịp xác nhận offset thì Kafka giao lại — lần sau thấy mã đã
 * có và bỏ qua, không cộng hai lần. Rollback thì cả hai cùng mất, lần giao lại cộng đúng một lần.
 *
 * <p>Cộng dồn qua Entity {@link MetricsDaily}: tìm dòng theo khoá 5 chiều kèm khoá dòng, chưa có thì tạo.
 * Mọi sự kiện của một doanh nghiệp vào cùng một phân vùng (khoá {@code tenant_id}) nên không có hai
 * consumer cùng tạo một dòng.
 */
@Service
public class TurnMetricsService {

    public static final String NHOM_TIEU_THU = "analytics-cg";

    /** Khớp TỪNG CHỮ CHECK của V113/V204 — lệch một chữ là dòng hỏng nằm lại ở hàng đợi lỗi. */
    static final Set<String> NHANH = Set.of("SMALL_TALK", "RAG", "TOOL_CALL", "CLARIFY", "HANDOFF", "SUMMARY",
            "EXTRACTION");

    private final EntityManager em;
    private final TenantTransactionScope scope;

    public TurnMetricsService(EntityManager em, TenantTransactionScope scope) {
        this.em = em;
        this.scope = scope;
    }

    /**
     * @return {@code false} nếu sự kiện đã xử lý trước đó (bỏ qua — {@code DUPLICATE_EVENT} của đặc tả)
     * @throws IllegalArgumentException sự kiện sai lược đồ — không cộng gì
     */
    @Transactional
    public boolean ghiNhan(JsonNode suKien) {
        UUID tenantId = UUID.fromString(batBuoc(suKien, "tenant_id"));
        String eventId = batBuoc(suKien, "event_id");
        Instant occurredAt = Instant.parse(batBuoc(suKien, "occurred_at"));
        JsonNode p = suKien.path("payload");
        String branch = p.path("branch").asText(null);
        if (!NHANH.contains(branch)) {
            throw new IllegalArgumentException("Nhánh lạ '" + branch + "' — không khớp 7 giá trị đã cam kết.");
        }

        scope.apply(tenantId);
        // Native có chủ đích: chống trùng cần INSERT … ON CONFLICT DO NOTHING (docs/events/README.md quy ước
        // 5) — persist() thì lần trùng vấp khoá chính và hỏng cả transaction.
        int moi = em.createNativeQuery("""
                INSERT INTO analytics.processed_events (consumer_group, event_id, tenant_id)
                VALUES (:g, :e, :t) ON CONFLICT DO NOTHING""")
                .setParameter("g", NHOM_TIEU_THU)
                .setParameter("e", eventId)
                .setParameter("t", tenantId)
                .executeUpdate();
        if (moi == 0) {
            return false;
        }

        UUID channelId = kenhCuaHoiThoai(tenantId, p.path("conversation_id").asText(null));
        LocalDate ngay = occurredAt.atZone(muiGio(tenantId)).toLocalDate();
        String moHinh = moHinh(p);
        MetricsDaily dong = timHoacTao(tenantId, ngay, channelId, branch, moHinh);
        dong.cong(luot(p), Instant.now());
        em.flush();
        return true;
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    private MetricsDaily timHoacTao(UUID tenantId, LocalDate ngay, UUID channelId, String branch, String moHinh) {
        // So khớp NULL tường minh — "= :x" với x = null không bao giờ đúng trong SQL
        StringBuilder q = new StringBuilder("""
                SELECT m FROM MetricsDaily m
                WHERE m.tenantId = :t AND m.metricDate = :d AND m.branch = :b""");
        q.append(channelId == null ? " AND m.channelId IS NULL" : " AND m.channelId = :c");
        q.append(moHinh == null ? " AND m.modelName IS NULL" : " AND m.modelName = :mh");
        TypedQuery<MetricsDaily> tq = em.createQuery(q.toString(), MetricsDaily.class)
                .setParameter("t", tenantId)
                .setParameter("d", ngay)
                .setParameter("b", branch)
                .setLockMode(LockModeType.PESSIMISTIC_WRITE);
        if (channelId != null) {
            tq.setParameter("c", channelId);
        }
        if (moHinh != null) {
            tq.setParameter("mh", moHinh);
        }
        Optional<MetricsDaily> co = tq.getResultStream().findFirst();
        if (co.isPresent()) {
            return co.get();
        }
        MetricsDaily m = new MetricsDaily(tenantId, ngay, channelId, branch, moHinh);
        em.persist(m);
        return m;
    }

    private UUID kenhCuaHoiThoai(UUID tenantId, String conversationId) {
        if (conversationId == null) {
            return null;
        }
        try {
            return em.createQuery("SELECT c.channelId FROM Conversation c WHERE c.tenantId = :t AND c.id = :id",
                            UUID.class)
                    .setParameter("t", tenantId)
                    .setParameter("id", UUID.fromString(conversationId))
                    .getResultStream().findFirst().orElse(null);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    /** Ngày của số liệu tính theo múi giờ doanh nghiệp — "hôm nay" của họ, không phải của máy chủ. */
    private ZoneId muiGio(UUID tenantId) {
        Tenant t = em.find(Tenant.class, tenantId);
        try {
            return ZoneId.of(t == null || t.getTimezone() == null ? "Asia/Ho_Chi_Minh" : t.getTimezone());
        } catch (Exception e) {
            return ZoneId.of("Asia/Ho_Chi_Minh");
        }
    }

    /** Khoá chiều "mô hình" gồm cả phiên bản — đổi phiên bản giữa kỳ thì tách dòng (UC039 4.2). */
    static String moHinh(JsonNode p) {
        String ten = p.path("model_name").asText(null);
        String phienBan = p.path("model_version").isNull() ? null : p.path("model_version").asText(null);
        if (ten == null || ten.isBlank()) {
            return null;
        }
        String k = phienBan == null || phienBan.isBlank() ? ten : ten + "@" + phienBan;
        return k.length() > 100 ? k.substring(0, 100) : k;
    }

    private static LuotXong luot(JsonNode p) {
        Map<String, Integer> cacChang = new HashMap<>();
        p.path("latency_breakdown").properties().forEach(e -> {
            if (e.getValue().canConvertToInt() && e.getValue().asInt() >= 0) {
                cacChang.put(e.getKey(), e.getValue().asInt());
            }
        });
        JsonNode g = p.path("groundedness_score");
        return new LuotXong(
                p.path("is_answered").asBoolean(false),
                p.path("llm_called").asBoolean(false),
                p.path("is_cached").asBoolean(false),
                p.path("is_degraded").asBoolean(false),
                p.path("status").asText("SUCCESS"),
                Math.max(p.path("prompt_tokens").asLong(0), 0),
                Math.max(p.path("completion_tokens").asLong(0), 0),
                p.path("cost_vnd").decimalValue().max(BigDecimal.ZERO),
                Math.max(p.path("latency_ms").asLong(0), 0),
                g.isNumber() ? g.decimalValue() : null,
                cacChang);
    }

    private static String batBuoc(JsonNode n, String truong) {
        String v = n.path(truong).asText(null);
        if (v == null || v.isBlank()) {
            throw new IllegalArgumentException("Sự kiện thiếu trường '" + truong + "'.");
        }
        return v;
    }
}
