package com.thesis.crm.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * Tóm tắt hội thoại ĐỒNG BỘ — UC026 trigger {@code MANUAL} (nút "Tóm tắt lại", chốt Q1 của GD3).
 * Đường chính {@code CLOSING} đi bất đồng bộ qua {@code crm.conversation.closed} và ai-service tự ghi
 * về {@code PATCH /internal/conversations/{id}/summary}; đường này thì java-core gửi kèm lịch sử, nhận
 * bốn phần về và TỰ ghi.
 *
 * <p>Record là GƯƠNG của {@code SummarizeRequest}/{@code SummarizeResponse} trong
 * {@code ai-service/src/ai/schemas.py}. Thân gửi đi ghi {@code snake_case} (mapper của
 * {@link AiServiceClient}); phản hồi của ai-service lại khai alias camelCase ({@code mainNeed}…) nên
 * gương đọc theo đúng tên đó qua {@code @JsonProperty} của từng trường.
 */
@Component
public class AiSummaryClient {

    private final AiServiceClient ai;

    public AiSummaryClient(AiServiceClient ai) {
        this.ai = ai;
    }

    public SummarizeResponse summarize(UUID tenantId, SummarizeRequest than) {
        return ai.post(tenantId, b -> b.path("/v1/ai/summarize").build(), than, SummarizeResponse.class);
    }

    /** {@code sender}: CUSTOMER · BOT · AGENT · SYSTEM ({@code engagement.messages.sender_type}). */
    public record SummarizeMessage(String sender, String text, Instant createdAt) {
    }

    public record SummarizeRequest(UUID conversationId, String trigger, List<SummarizeMessage> messages) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record SummarizeResponse(
            @JsonProperty("trigger") String trigger,
            @JsonProperty("mainNeed") String mainNeed,
            @JsonProperty("providedInfo") String providedInfo,
            @JsonProperty("unresolvedIssues") String unresolvedIssues,
            @JsonProperty("nextSteps") String nextSteps,
            @JsonProperty("modelVersion") String modelVersion,
            @JsonProperty("summaryText") String summaryText,
            @JsonProperty("generatedAt") Instant generatedAt,
            @JsonProperty("interactionId") UUID interactionId) {
    }
}
