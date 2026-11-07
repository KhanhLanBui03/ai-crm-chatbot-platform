package com.thesis.crm.analytics.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.DynamicUpdate;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * {@code analytics.metrics_daily} — mô hình đọc theo ngày của UC039 (V113, V137). Một dòng = một tổ hợp
 * khoá 5 chiều (doanh nghiệp, ngày, kênh, nhánh, mô hình), khoá duy nhất {@code NULLS NOT DISTINCT}.
 *
 * <p>Bảng tồn tại vì RANH GIỚI QUYỀN chứ không vì hiệu năng: chi phí, token, độ trễ nằm ở schema của
 * ai-service mà java-core không được đọc (ADR-0002) — consumer {@code analytics-cg} cộng dồn từ sự kiện
 * {@code ai.turn.completed}.
 *
 * <p>Chỉ map các cột UC039 dùng; các cột đếm hội thoại ({@code conversation_count}…) của nguồn
 * {@code crm.conversation.v1} để nguyên cho người làm nguồn đó.
 */
@Entity
@DynamicUpdate
@Table(name = "metrics_daily", schema = "analytics")
public class MetricsDaily {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "metric_date", nullable = false, updatable = false)
    private LocalDate metricDate;

    @Column(name = "channel_id", updatable = false)
    private UUID channelId;

    /** Bảy giá trị khớp TỪNG CHỮ {@code ai.ai_interactions.branch} (V204). */
    @Column(length = 30, updatable = false)
    private String branch;

    @Column(name = "model_name", length = 100, updatable = false)
    private String modelName;

    @Column(name = "interaction_count", nullable = false)
    private int interactionCount;

    @Column(name = "refusal_count", nullable = false)
    private int refusalCount;

    @Column(name = "positive_feedback", nullable = false)
    private int positiveFeedback;

    @Column(name = "negative_feedback", nullable = false)
    private int negativeFeedback;

    @Column(name = "prompt_tokens", nullable = false)
    private long promptTokens;

    @Column(name = "completion_tokens", nullable = false)
    private long completionTokens;

    /** 4 chữ số thập phân — một lượt gọi mô hình nhỏ có thể dưới 1 đồng. */
    @Column(name = "cost_vnd", nullable = false, precision = 16, scale = 4)
    private BigDecimal costVnd = BigDecimal.ZERO;

    @Column(name = "latency_sum_ms", nullable = false)
    private long latencySumMs;

    @Column(name = "llm_call_count", nullable = false)
    private int llmCallCount;

    @Column(name = "cached_count", nullable = false)
    private int cachedCount;

    @Column(name = "degraded_count", nullable = false)
    private int degradedCount;

    @Column(name = "failed_count", nullable = false)
    private int failedCount;

    @Column(name = "groundedness_sum", nullable = false, precision = 14, scale = 3)
    private BigDecimal groundednessSum = BigDecimal.ZERO;

    @Column(name = "groundedness_count", nullable = false)
    private int groundednessCount;

    /** {@code {"retrieve_ms": {"sum": 1234, "n": 5}, …}} (V137). */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "stage_latency", nullable = false)
    private Map<String, Map<String, Long>> stageLatency = new HashMap<>();

    /** Mốc cộng dồn gần nhất — trang báo cáo hiện mốc này để người xem thấy số liệu đang trễ (UC039 6.1). */
    @Column(name = "last_calculated_at", nullable = false)
    private Instant lastCalculatedAt = Instant.now();

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    /** Trigger {@code trg_touch_updated_at} tự đặt mỗi lần UPDATE. */
    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt = Instant.now();

    protected MetricsDaily() {
        // JPA yêu cầu constructor không tham số
    }

    public MetricsDaily(UUID tenantId, LocalDate metricDate, UUID channelId, String branch, String modelName) {
        this.tenantId = tenantId;
        this.metricDate = metricDate;
        this.channelId = channelId;
        this.branch = branch;
        this.modelName = modelName;
    }

    /** Cộng MỘT lượt xử lý vào dòng này. */
    public void cong(LuotXong l, Instant at) {
        interactionCount++;
        if (!l.answered()) {
            refusalCount++;
        }
        if (l.llmCalled()) {
            llmCallCount++;
        }
        if (l.cached()) {
            cachedCount++;
        }
        if (l.degraded()) {
            degradedCount++;
        }
        if (!"SUCCESS".equals(l.status())) {
            failedCount++;
        }
        promptTokens += l.promptTokens();
        completionTokens += l.completionTokens();
        costVnd = costVnd.add(l.costVnd());
        latencySumMs += l.latencyMs();
        if (l.groundedness() != null) {
            groundednessSum = groundednessSum.add(l.groundedness());
            groundednessCount++;
        }
        // Map mới để Hibernate thấy cột JSON đã đổi (so sánh theo giá trị, không theo tham chiếu)
        Map<String, Map<String, Long>> moi = new HashMap<>();
        stageLatency.forEach((k, v) -> moi.put(k, new HashMap<>(v)));
        l.stages().forEach((chang, ms) -> {
            Map<String, Long> o = moi.computeIfAbsent(chang, k -> new HashMap<>());
            o.merge("sum", (long) ms, Long::sum);
            o.merge("n", 1L, Long::sum);
        });
        stageLatency = moi;
        lastCalculatedAt = at;
    }

    /** Một lượt đã đọc từ sự kiện {@code ai.turn.completed} — dạng gọn để cộng dồn. */
    public record LuotXong(boolean answered, boolean llmCalled, boolean cached, boolean degraded, String status,
                           long promptTokens, long completionTokens, BigDecimal costVnd, long latencyMs,
                           BigDecimal groundedness, Map<String, Integer> stages) {}

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public LocalDate getMetricDate() { return metricDate; }
    public UUID getChannelId() { return channelId; }
    public String getBranch() { return branch; }
    public String getModelName() { return modelName; }
    public int getInteractionCount() { return interactionCount; }
    public int getRefusalCount() { return refusalCount; }
    public int getPositiveFeedback() { return positiveFeedback; }
    public int getNegativeFeedback() { return negativeFeedback; }
    public long getPromptTokens() { return promptTokens; }
    public long getCompletionTokens() { return completionTokens; }
    public BigDecimal getCostVnd() { return costVnd; }
    public long getLatencySumMs() { return latencySumMs; }
    public int getLlmCallCount() { return llmCallCount; }
    public int getCachedCount() { return cachedCount; }
    public int getDegradedCount() { return degradedCount; }
    public int getFailedCount() { return failedCount; }
    public BigDecimal getGroundednessSum() { return groundednessSum; }
    public int getGroundednessCount() { return groundednessCount; }
    public Map<String, Map<String, Long>> getStageLatency() { return stageLatency; }
    public Instant getLastCalculatedAt() { return lastCalculatedAt; }
}
