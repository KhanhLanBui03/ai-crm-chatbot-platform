package com.thesis.crm.platform.dto.response;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Một lượt xử lý của tác tử AI — hình {@code LuotXuLyAi} của {@code dashboard-api.yaml} (SCR036, cột ngữ
 * cảnh hộp thư). Dựng từ {@code InteractionItem} của ai-service: java-core không đọc schema {@code ai}
 * (ADR-0002); riêng {@code DanhGiaAi.ratedByName} tra {@code platform.users}.
 *
 * @param latencyBreakdown chặng đã GỘP cho giao diện: {@code retrieve} (nhúng + truy hồi), {@code rerank},
 *                         {@code generate}, {@code tool}, {@code guard}, {@code classify} — cùng luật với
 *                         {@code AiPerformanceService} để hai màn gọi một chặng bằng một tên
 * @param discardedAnswer  câu đã sinh nhưng bị HUỶ vì không bám nguồn — khách chưa từng nhận
 * @param errorCode        {@code FAILED}/{@code TIMEOUT} khi lượt hỏng; {@code null} khi chạy xong
 * @param toolCalls        luôn rỗng — nhóm MCP đã hoãn (UC021/024/028)
 * @param feedback         đánh giá mới nhất của người (khách hoặc nhân viên); {@code feedbacks} có đủ
 */
public record LuotXuLyAiResponse(
        UUID id,
        UUID conversationId,
        UUID messageId,
        String route,
        String intentLabel,
        Double intentConfidence,
        String userQuery,
        String answerText,
        String modelName,
        String modelVersion,
        int promptTokens,
        int completionTokens,
        double costVnd,
        Integer latencyMs,
        Map<String, Integer> latencyBreakdown,
        Double retrievalTopScore,
        Double groundednessScore,
        List<TrichDan> citations,
        boolean refused,
        String refusalReason,
        boolean cached,
        boolean degraded,
        boolean handoff,
        String discardedAnswer,
        String errorCode,
        List<Object> toolCalls,
        DanhGiaAiResponse feedback,
        List<DanhGiaAiResponse> feedbacks,
        Instant createdAt) {

    /** {@code TrichDan} — căn cứ đã trích, giữ thứ tự [1], [2]… của câu trả lời. */
    public record TrichDan(UUID chunkId, UUID documentId, String documentTitle, String sectionPath,
            String snippet) {
    }
}
