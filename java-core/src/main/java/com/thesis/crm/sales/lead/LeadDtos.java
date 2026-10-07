package com.thesis.crm.sales.lead;

import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Hình dạng vào/ra của UC032 — khớp {@code Lead}, {@code LeadChiTiet}, {@code DiemLead},
 * {@code TaoLeadRequest}, {@code CapNhatLeadRequest} trong {@code docs/openapi/dashboard-api.yaml}.
 */
public final class LeadDtos {

    private LeadDtos() {}

    /** Một dòng ở danh sách (schema {@code Lead}). */
    public record LeadDto(
            UUID id, UUID contactId, String contactName, String contactPhone, UUID sourceConversationId,
            String source, String status, String interestedProduct, BigDecimal budgetMin, BigDecimal budgetMax,
            String budgetConfidence, String urgency, Integer currentScore, Instant scoreUpdatedAt,
            UUID ownerUserId, String ownerName, Instant createdAt) {}

    /**
     * Chi tiết (schema {@code LeadChiTiet}). {@code @JsonUnwrapped} không dùng được với record lồng
     * nhau ổn định, nên chép phẳng các trường của {@link LeadDto}.
     *
     * <p>{@code allowedNextStatuses}: trạng thái được phép đi tiếp — giao diện chỉ hiện đúng các nút
     * này (UC032 luồng 8.2), không tự suy luật chuyển trạng thái lần thứ hai.
     */
    public record LeadDetail(
            UUID id, UUID contactId, String contactName, String contactPhone, UUID sourceConversationId,
            String source, String status, String interestedProduct, BigDecimal budgetMin, BigDecimal budgetMax,
            String budgetConfidence, String urgency, Integer currentScore, Instant scoreUpdatedAt,
            UUID ownerUserId, String ownerName, Instant createdAt,
            ScoreDto latestScore, String disqualifyReason, UUID convertedDealId, Instant convertedAt,
            int activityCount, Instant closedAt, List<String> allowedNextStatuses) {}

    /** Một lần chấm điểm (schema {@code DiemLead}). */
    public record ScoreDto(int score, String modelVersion, String scoringMode, JsonNode topFactors,
                           String confidence, Instant computedAt) {}

    public record CreateLeadRequest(
            UUID contactId, UUID sourceConversationId, String interestedProduct, BigDecimal budgetMin,
            BigDecimal budgetMax, String urgency, UUID ownerUserId) {}

    /** Ngữ cảnh gửi kèm 409 trùng — giao diện dẫn người dùng tới lead đang mở. */
    public record OpenLeadConflict(UUID leadId, String status, UUID ownerUserId, String ownerName) {}

    /** Ngữ cảnh gửi kèm 422 chuyển trạng thái sai (UC032 luồng 8.1–8.2). */
    public record TransitionError(String from, String to, List<String> allowedNextStatuses) {}
}
