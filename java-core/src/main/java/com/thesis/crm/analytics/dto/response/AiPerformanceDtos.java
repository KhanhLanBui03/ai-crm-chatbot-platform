package com.thesis.crm.analytics.dto.response;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/** Hợp đồng UC039 — {@code HieuQuaAi} trong {@code docs/openapi/dashboard-api.yaml}. */
public final class AiPerformanceDtos {

    private AiPerformanceDtos() {
    }

    /**
     * @param updatedAt   mốc cộng dồn gần nhất của doanh nghiệp; {@code null} khi chưa từng có lượt nào —
     *                    consumer đọng thì mốc này lùi lại và giao diện phải hiện ra (UC039 6.1)
     * @param llmFreeRate KPI §1.6 — tỉ lệ lượt KHÔNG gọi LLM (ngưỡng ≥ 0,55)
     * @param avgLatencyMs trung bình = tổng độ trễ ÷ số lượt. Không có p95: phân vị không cộng dồn qua nhiều
     *                    ngày (UC039 6.2) — trả số ước lượng là nói sai cho người xem
     */
    public record HieuQuaAi(
            Instant updatedAt, long totalInteractions, double refusalRate, double positiveFeedbackRate,
            long feedbackCount, double cachedRate, Double avgGroundedness, Long avgLatencyMs, BigDecimal costVnd,
            double llmFreeRate, List<TheoNhanh> routeDistribution, List<LyDoChuyenGiao> handoffReasons,
            Map<String, Long> latencyBreakdown, List<String> modelVersions, String errorMessage) {}

    public record TheoNhanh(String route, long count, BigDecimal costVnd) {}

    public record LyDoChuyenGiao(String reason, long count, boolean countsAgainstAiQuality) {}
}
