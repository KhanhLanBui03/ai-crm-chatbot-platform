package com.thesis.crm.analytics.service;

import com.thesis.crm.analytics.dto.response.AiPerformanceDtos.HieuQuaAi;
import com.thesis.crm.analytics.dto.response.AiPerformanceDtos.LyDoChuyenGiao;
import com.thesis.crm.analytics.dto.response.AiPerformanceDtos.TheoNhanh;
import com.thesis.crm.analytics.entity.MetricsDaily;
import com.thesis.crm.client.AiInteractionClient;
import com.thesis.crm.client.AiInteractionClient.DanhGiaPhia;
import com.thesis.crm.client.AiInteractionClient.QualitySummary;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.security.TenantTransactionScope;
import jakarta.persistence.EntityManager;
import jakarta.persistence.TypedQuery;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC039 — gộp số liệu cho màn "Hiệu quả và chi phí của tác tử AI" từ mô hình đọc {@link MetricsDaily} và lý
 * do chuyển giao ở {@code engagement.handoff_events}. Đọc qua Entity, lọc {@code tenantId} cùng RLS.
 *
 * <p><b>Ô "Phản hồi tích cực" (UC027 bước 7) lấy từ ai-service, không từ {@code metrics_daily}</b> — chốt
 * Q2 đợt GD2 (10/11/2026). Sự kiện {@code ai.turn.completed} phát ngay khi lượt chat xong, TRƯỚC khi có
 * ai bấm 👍/👎, nên hai cột {@code positive_feedback}/{@code negative_feedback} không có nguồn nào cộng.
 * {@code GET /v1/ai/quality} đếm thẳng {@code ai.ai_feedback} (đặc tả UC027: "AI tổng hợp vào chỉ số hiệu
 * quả"): đánh giá lại tự đúng vì chỉ có một dòng mỗi phía, và đánh giá được gom theo NGÀY CỦA LƯỢT — cùng
 * cách {@code metrics_daily} gom các ô khác. ai-service lỗi thì riêng ô này trống và có
 * {@code errorMessage}; các ô khác vẫn có số.
 */
@Service
public class AiPerformanceService {

    private static final Logger log = LoggerFactory.getLogger(AiPerformanceService.class);
    /** Phía tính vào ô — đúng nhãn "lượt đánh giá của nhân viên và khách"; nhãn máy AUTO_EVAL không tính. */
    static final List<String> PHIA_NGUOI = List.of("CUSTOMER", "AGENT");
    static final String LOI_DANH_GIA = "Tạm không lấy được số đánh giá từ dịch vụ AI — các chỉ số khác vẫn đúng.";

    /** Thứ tự hiển thị — đủ 7 nhánh, nhánh 0 lượt vẫn có dòng (UC039 5.1: ẩn đi thì không thấy điểm nghẽn). */
    static final List<String> CAC_NHANH = List.of("SMALL_TALK", "RAG", "CLARIFY", "HANDOFF", "TOOL_CALL", "SUMMARY",
            "EXTRACTION");
    static final int SO_NGAY_MAC_DINH = 30;

    private final EntityManager em;
    private final TenantTransactionScope scope;
    private final AiInteractionClient ai;

    public AiPerformanceService(EntityManager em, TenantTransactionScope scope, AiInteractionClient ai) {
        this.em = em;
        this.scope = scope;
        this.ai = ai;
    }

    @Transactional(readOnly = true)
    public HieuQuaAi report(UUID tenantId, boolean isAdmin, LocalDate from, LocalDate to, String modelVersion) {
        if (!isAdmin) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN",
                    "Chỉ quản trị viên doanh nghiệp được xem hiệu quả và chi phí AI.");
        }
        scope.apply(tenantId);
        ZoneId zone = muiGio(tenantId);
        LocalDate den = to != null ? to : LocalDate.now(zone);
        LocalDate tu = from != null ? from : den.minusDays(SO_NGAY_MAC_DINH - 1L);

        StringBuilder q = new StringBuilder(
                "SELECT m FROM MetricsDaily m WHERE m.tenantId = :t AND m.metricDate BETWEEN :tu AND :den");
        if (modelVersion != null && !modelVersion.isBlank()) {
            q.append(" AND m.modelName = :mh");
        }
        TypedQuery<MetricsDaily> tq = em.createQuery(q.toString(), MetricsDaily.class)
                .setParameter("t", tenantId).setParameter("tu", tu).setParameter("den", den);
        if (modelVersion != null && !modelVersion.isBlank()) {
            tq.setParameter("mh", modelVersion.strip());
        }
        List<MetricsDaily> dong = tq.getResultList();

        long luot = 0, tuChoi = 0, goiLlm = 0, dem = 0, treTong = 0, demBam = 0;
        BigDecimal chiPhi = BigDecimal.ZERO, tongBam = BigDecimal.ZERO;
        Map<String, long[]> theoNhanh = new HashMap<>();          // nhánh → [số lượt]
        Map<String, BigDecimal> phiNhanh = new HashMap<>();
        Map<String, long[]> chang = new HashMap<>();               // chặng → [tổng ms, số lượt chạy chặng]
        for (MetricsDaily m : dong) {
            luot += m.getInteractionCount();
            tuChoi += m.getRefusalCount();
            goiLlm += m.getLlmCallCount();
            dem += m.getCachedCount();
            treTong += m.getLatencySumMs();
            demBam += m.getGroundednessCount();
            chiPhi = chiPhi.add(m.getCostVnd());
            tongBam = tongBam.add(m.getGroundednessSum());
            theoNhanh.computeIfAbsent(m.getBranch(), k -> new long[1])[0] += m.getInteractionCount();
            phiNhanh.merge(m.getBranch(), m.getCostVnd(), BigDecimal::add);
            m.getStageLatency().forEach((ten, o) -> {
                long[] a = chang.computeIfAbsent(ten, k -> new long[2]);
                a[0] += o.getOrDefault("sum", 0L);
                a[1] += o.getOrDefault("n", 0L);
            });
        }

        List<TheoNhanh> phanBo = new ArrayList<>();
        for (String b : CAC_NHANH) {
            phanBo.add(new TheoNhanh(b, theoNhanh.getOrDefault(b, new long[1])[0],
                    phiNhanh.getOrDefault(b, BigDecimal.ZERO)));
        }
        long[] tichCucVaDanhGia = danhGiaCuaNguoi(tenantId, tu.atStartOfDay(zone).toInstant(),
                den.plusDays(1).atStartOfDay(zone).toInstant());
        long danhGia = tichCucVaDanhGia == null ? 0 : tichCucVaDanhGia[1];
        return new HieuQuaAi(
                capNhatGanNhat(tenantId),
                luot,
                tiLe(tuChoi, luot),
                tichCucVaDanhGia == null ? 0 : tiLe(tichCucVaDanhGia[0], danhGia),
                danhGia,
                tiLe(dem, luot),
                demBam == 0 ? null : tongBam.doubleValue() / demBam,
                luot == 0 ? null : treTong / luot,
                chiPhi,
                luot == 0 ? 0 : 1 - (double) goiLlm / luot,
                phanBo,
                lyDoChuyenGiao(tenantId, tu.atStartOfDay(zone).toInstant(), den.plusDays(1).atStartOfDay(zone).toInstant()),
                chang(chang),
                phienBanMoHinh(dong),
                tichCucVaDanhGia == null ? LOI_DANH_GIA : null);
    }

    /**
     * {@code [số khen, số đánh giá]} của khách + nhân viên trong {@code [tu, den)} — cộng TỬ với tử, MẪU với
     * mẫu (không cộng hai tỉ lệ). Mẫu số là số lượt ĐÃ có đánh giá, không phải tổng số lượt (đặc tả
     * UC027); một lượt được cả khách lẫn nhân viên đánh giá thì góp hai — đúng nhãn "lượt đánh giá".
     * {@code null} khi ai-service không trả lời được.
     *
     * <p>Bộ lọc {@code modelVersion} của màn KHÔNG áp cho ô này (ai-service không lọc đánh giá theo mô
     * hình) — ghi ở "giảm độ sâu" của báo cáo đợt giao diện.
     */
    private long[] danhGiaCuaNguoi(UUID tenantId, Instant tu, Instant den) {
        QualitySummary q;
        try {
            q = ai.quality(tenantId, tu, den);
        } catch (AiServiceException ex) {
            log.warn("Không lấy được số đánh giá từ ai-service: {} {}", ex.getStatus(), ex.getCode());
            return null;
        }
        long khen = 0;
        long tong = 0;
        for (DanhGiaPhia p : q.danhGia() == null ? List.<DanhGiaPhia>of() : q.danhGia()) {
            if (PHIA_NGUOI.contains(p.raterType()) && p.tyLeTichCuc() != null) {
                khen += p.tyLeTichCuc().tuSo();
                tong += p.tyLeTichCuc().mauSo();
            }
        }
        return new long[] {khen, tong};
    }

    /**
     * Trung bình từng chặng, chia theo số lượt CHẠY chặng đó. Bốn khoá đầu là khoá giao diện đang vẽ
     * ({@code retrieve} gồm cả bước nhúng câu hỏi); các chặng còn lại trả thêm để không giấu số.
     */
    private static Map<String, Long> chang(Map<String, long[]> c) {
        Map<String, Long> out = new LinkedHashMap<>();
        out.put("retrieve", tb(c, "embed_ms") + tb(c, "retrieve_ms"));
        out.put("rerank", tb(c, "rerank_ms"));
        out.put("generate", tb(c, "generate_ms"));
        out.put("tool", tb(c, "tool_ms"));
        out.put("guard", tb(c, "guard_ms") + tb(c, "postguard_ms"));
        out.put("classify", tb(c, "classify_ms"));
        return out;
    }

    private static long tb(Map<String, long[]> c, String k) {
        long[] a = c.get(k);
        return a == null || a[1] == 0 ? 0 : a[0] / a[1];
    }

    private List<LyDoChuyenGiao> lyDoChuyenGiao(UUID tenantId, Instant tu, Instant den) {
        return em.createQuery("""
                        SELECT h.reason, h.countsAgainstAiQuality, count(h)
                        FROM HandoffEvent h
                        WHERE h.tenantId = :t AND h.direction = 'BOT_TO_AGENT'
                          AND h.occurredAt >= :tu AND h.occurredAt < :den
                        GROUP BY h.reason, h.countsAgainstAiQuality
                        ORDER BY count(h) DESC""", Object[].class)
                .setParameter("t", tenantId).setParameter("tu", tu).setParameter("den", den)
                .getResultStream()
                .map(r -> new LyDoChuyenGiao((String) r[0], ((Number) r[2]).longValue(), (Boolean) r[1]))
                .toList();
    }

    /** Mốc của CẢ doanh nghiệp, không theo khoảng lọc — người xem cần biết consumer có đang đọng không. */
    private Instant capNhatGanNhat(UUID tenantId) {
        return em.createQuery("SELECT max(m.lastCalculatedAt) FROM MetricsDaily m WHERE m.tenantId = :t", Instant.class)
                .setParameter("t", tenantId).getSingleResult();
    }

    private static List<String> phienBanMoHinh(List<MetricsDaily> dong) {
        TreeSet<String> s = new TreeSet<>();
        dong.forEach(m -> {
            if (m.getModelName() != null) {
                s.add(m.getModelName());
            }
        });
        return List.copyOf(s);
    }

    private static double tiLe(long tu, long mau) {
        return mau == 0 ? 0 : (double) tu / mau;
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
