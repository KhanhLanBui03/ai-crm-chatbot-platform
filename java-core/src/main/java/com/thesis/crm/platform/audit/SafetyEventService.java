package com.thesis.crm.platform.audit;

import com.thesis.crm.client.AiServiceClient;
import com.thesis.crm.client.AiServiceClient.SafetyEventItem;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.common.enums.AuditSeverity;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.entity.AuditLog;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.security.TenantTransactionScope;
import com.thesis.crm.security.TraceIdFilter;
import jakarta.persistence.EntityManager;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC040 bước 8 — màn "Cảnh báo an toàn" HỢP NHẤT ba nguồn, không phải ba màn rời:
 * <ol>
 *   <li>{@code ai.ai_interactions.safety_flag} — tiêm chỉ thị, dò dữ liệu (ai-service)</li>
 *   <li>{@code ai.ai_tool_calls} bị chặn — nhóm MCP đã hoãn nên hiện luôn rỗng (ai-service)</li>
 *   <li>{@code platform.audit_logs} mức {@code CRITICAL} — của java-core, đọc qua Entity {@link AuditLog}</li>
 * </ol>
 * Hai nguồn đầu ở schema ai-service mà java-core không được đọc (ADR-0002) — lấy qua
 * {@link AiServiceClient#listSafetyEvents}. Gộp ở tầng đọc rẻ hơn dựng một đường ghi xuyên hai làn.
 *
 * <p>ai-service không trả lời thì báo lỗi 503 chứ KHÔNG lặng lẽ trả mỗi phần java-core: màn cảnh báo thiếu
 * hai phần ba nguồn mà trông như "không có sự cố" là nói dối người xem.
 */
@Service
public class SafetyEventService {

    static final int SO_NGAY_MAC_DINH = 30;
    /** Tối đa mỗi nguồn — sự cố an toàn là ngoại lệ hiếm, 500 dòng/30 ngày đã là báo động. */
    static final int TRAN_MOI_NGUON = 500;

    private final EntityManager em;
    private final TenantTransactionScope scope;
    private final AiServiceClient ai;

    public SafetyEventService(EntityManager em, TenantTransactionScope scope, AiServiceClient ai) {
        this.em = em;
        this.scope = scope;
        this.ai = ai;
    }

    /** Một cảnh báo — hợp đồng {@code SuKienAnToan}. {@code id} là chuỗi vì ba nguồn có ba kiểu khoá. */
    public record SuKienAnToan(String id, String eventType, String severity, String threatSurface,
                               UUID conversationId, String detector, Map<String, String> evidence,
                               String actionTaken, Instant occurredAt) {}

    @Transactional(readOnly = true)
    public PageResponse<SuKienAnToan> list(UUID tenantId, boolean isAdmin, String severity, String eventType,
                                          LocalDate from, LocalDate to, int page, int size) {
        if (!isAdmin) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN",
                    "Chỉ quản trị viên doanh nghiệp được xem cảnh báo an toàn.");
        }
        scope.apply(tenantId);
        ZoneId zone = muiGio(tenantId);
        LocalDate den = to != null ? to : LocalDate.now(zone);
        LocalDate tu = from != null ? from : den.minusDays(SO_NGAY_MAC_DINH - 1L);
        Instant batDau = tu.atStartOfDay(zone).toInstant();
        Instant ketThuc = den.plusDays(1).atStartOfDay(zone).toInstant();

        List<SuKienAnToan> tatCa = new ArrayList<>();
        tatCa.addAll(tuAi(tenantId, batDau, ketThuc));
        tatCa.addAll(tuNhatKy(tenantId, batDau, ketThuc));
        List<SuKienAnToan> loc = tatCa.stream()
                .filter(e -> severity == null || severity.equals(e.severity()))
                .filter(e -> eventType == null || eventType.equals(e.eventType()))
                .sorted(Comparator.comparing(SuKienAnToan::occurredAt).reversed())
                .toList();

        int co = Math.min(Math.max(size, 1), 100);
        int trang = Math.max(page, 0);
        int dau = Math.min(trang * co, loc.size());
        return PageResponse.of(loc.subList(dau, Math.min(dau + co, loc.size())), trang, co, loc.size());
    }

    private List<SuKienAnToan> tuAi(UUID tenantId, Instant tu, Instant den) {
        List<SafetyEventItem> ds;
        try {
            ds = ai.listSafetyEvents(tenantId, MDC.get(TraceIdFilter.MDC_KEY), tu, den, TRAN_MOI_NGUON);
        } catch (AiServiceException e) {
            throw new BusinessException(HttpStatus.SERVICE_UNAVAILABLE, "AI_SERVICE_UNAVAILABLE",
                    "Chưa lấy được cảnh báo từ dịch vụ AI — danh sách sẽ thiếu, thử lại sau ít phút.");
        }
        return ds.stream().map(i -> new SuKienAnToan(
                i.eventId().toString(), i.eventType(), i.severity(), i.threatSurface(), i.conversationId(),
                i.detector(), i.evidence() == null ? Map.of() : i.evidence(), i.actionTaken(), i.occurredAt()))
                .toList();
    }

    /**
     * Nhật ký mức CRITICAL — nỗ lực vượt phạm vi doanh nghiệp mà java-core chặn được. Bằng chứng chỉ có mã
     * hành động và loại đối tượng: phần trước/sau của nhật ký có thể chứa dữ liệu đã che, không đưa ra đây.
     */
    private List<SuKienAnToan> tuNhatKy(UUID tenantId, Instant tu, Instant den) {
        return em.createQuery("""
                        SELECT a FROM AuditLog a
                        WHERE a.tenantId = :t AND a.severity = :muc AND a.createdAt >= :tu AND a.createdAt < :den
                        ORDER BY a.createdAt DESC""", AuditLog.class)
                .setParameter("t", tenantId)
                .setParameter("muc", AuditSeverity.CRITICAL)
                .setParameter("tu", tu)
                .setParameter("den", den)
                .setMaxResults(TRAN_MOI_NGUON)
                .getResultStream()
                .map(a -> {
                    Map<String, String> bc = new LinkedHashMap<>();
                    bc.put("action", a.getAction());
                    bc.put("entityType", a.getEntityType());
                    return new SuKienAnToan("audit-" + a.getId(), "CROSS_TENANT_PROBE", "CRITICAL", "T7", null,
                            "java-core", bc, "BLOCKED", a.getCreatedAt());
                })
                .toList();
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
