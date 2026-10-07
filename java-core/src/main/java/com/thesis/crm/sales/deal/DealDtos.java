package com.thesis.crm.sales.deal;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.thesis.crm.sales.lead.LeadDtos.LeadDto;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

/**
 * Hình dạng vào/ra của UC033 + UC034 — khớp {@code Pheu}, {@code GiaiDoanPheu}, {@code Deal},
 * {@code DealChiTiet}, {@code LichSuGiaiDoan}, {@code ChuyenDoiLeadResult} trong
 * {@code docs/openapi/dashboard-api.yaml}.
 *
 * <p>Trường boolean ghi {@code @JsonProperty} tường minh: tên thành phần record bắt đầu bằng "is" dễ bị
 * Jackson cắt thành "won"/"overdue" tuỳ phiên bản.
 */
public final class DealDtos {

    private DealDtos() {}

    public record PipelineDto(UUID id, String name, @JsonProperty("isDefault") boolean isDefault,
                              @JsonProperty("isActive") boolean isActive, List<StageDto> stages) {}

    public record StageDto(UUID id, String name, int position, Integer probability,
                           @JsonProperty("isWon") boolean isWon, @JsonProperty("isLost") boolean isLost,
                           List<String> requiredFields, int dealCount, BigDecimal dealValueTotal) {}

    public record DealDto(
            UUID id, UUID contactId, String contactName, UUID leadId, UUID pipelineId, UUID stageId,
            String stageName, String title, BigDecimal amount, String currency, LocalDate expectedCloseDate,
            @JsonProperty("isOverdue") boolean isOverdue, String status, String source, UUID ownerUserId,
            String ownerName, Instant stageChangedAt, Instant createdAt) {}

    /** Chi tiết (schema {@code DealChiTiet}) — chép phẳng các trường của {@link DealDto}. */
    public record DealDetail(
            UUID id, UUID contactId, String contactName, UUID leadId, UUID pipelineId, UUID stageId,
            String stageName, String title, BigDecimal amount, String currency, LocalDate expectedCloseDate,
            @JsonProperty("isOverdue") boolean isOverdue, String status, String source, UUID ownerUserId,
            String ownerName, Instant stageChangedAt, Instant createdAt,
            String closeReason, Instant closedAt, List<HistoryDto> stageHistory, List<Object> activities) {}

    public record HistoryDto(UUID fromStageId, String fromStageName, UUID toStageId, String toStageName,
                             Long durationSeconds, String changedByName, Instant changedAt) {}

    /** SCR046 — tạo deal thủ công. {@code leadId} không nhận ở đây: deal từ lead đi qua /convert. */
    public record CreateDealRequest(UUID contactId, UUID leadId, UUID pipelineId, UUID stageId, String title,
                                    BigDecimal amount, String currency, LocalDate expectedCloseDate,
                                    UUID ownerUserId) {}

    /** UC033 — phễu/giai đoạn bỏ trống thì vào giai đoạn mở đầu tiên của phễu mặc định. */
    public record ConvertRequest(String title, UUID pipelineId, UUID stageId, BigDecimal amount,
                                 LocalDate expectedCloseDate) {}

    public record MoveStageRequest(UUID stageId, String closeReason) {}

    public record ConvertResult(DealDto deal, LeadDto lead, List<String> warnings) {}

    /** Ngữ cảnh 422 thiếu trường bắt buộc của giai đoạn đích (UC034 luồng 5.1). */
    public record MissingFields(List<String> missingFields) {}
}
