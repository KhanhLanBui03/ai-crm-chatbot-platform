package com.thesis.crm.client;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriBuilder;

/**
 * Lượt xử lý và đánh giá phía ai-service — UC023 bước 10, UC025, UC027 (GD2). Chỉ là bảng địa chỉ và
 * gương DTO; vận chuyển, header tenant/trace và mã lỗi do {@link AiServiceClient} lo — cùng khuôn
 * {@link AiKnowledgeClient} của GD1.
 *
 * <p>Record ở đây là GƯƠNG của {@code ai-service/src/ai/schemas.py} ({@code InteractionItem},
 * {@code FeedbackRequest}, {@code KnowledgeGapItem}, {@code QualitySummary}). Tên trường Java viết
 * camelCase, mapper {@code snake_case} đổi chiều; khoá của {@code latencyBreakdown} là DỮ LIỆU nên giữ
 * nguyên ({@code retrieve_ms}…). Nháp hợp đồng: {@code docs/contracts/giao-dien-gd.md} mục 4.
 */
@Component
public class AiInteractionClient {

    private final AiServiceClient ai;

    public AiInteractionClient(AiServiceClient ai) {
        this.ai = ai;
    }

    /** SCR036 — mới nhất trước. {@code tu}/{@code den} là nửa khoảng {@code [tu, den)}. */
    public InteractionPage list(UUID tenantId, String route, Boolean refused, String rating, UUID conversationId,
            Instant tu, Instant den, int page, int size) {
        return ai.get(tenantId, b -> {
            Map<String, Object> bien = new HashMap<>();
            b.path("/v1/ai-interactions").queryParam("page", page).queryParam("size", size);
            themNeuCo(b, bien, "route", route);
            themNeuCo(b, bien, "refused", refused);
            themNeuCo(b, bien, "rating", rating);
            themNeuCo(b, bien, "conversation_id", conversationId);
            themNeuCo(b, bien, "tu", tu);
            themNeuCo(b, bien, "den", den);
            return b.build(bien);
        }, InteractionPage.class);
    }

    /** UC027 bước 5. Đánh giá lại từ cùng phía thì ai-service CẬP NHẬT dòng cũ ({@code created = false}). */
    public FeedbackRecorded feedback(UUID tenantId, UUID interactionId, FeedbackRequest than) {
        return ai.post(tenantId, b -> b.path("/v1/ai-interactions/{id}/feedback").build(interactionId), than,
                FeedbackRecorded.class);
    }

    /** SCR034 — sắp theo số hội thoại khác nhau trước (UC025 luồng phụ 8.1), cửa sổ 30 ngày. */
    public KnowledgeGapPage knowledgeGaps(UUID tenantId, String gapType, int page, int size) {
        return ai.get(tenantId, b -> {
            Map<String, Object> bien = new HashMap<>();
            b.path("/v1/knowledge-gaps").queryParam("page", page).queryParam("size", size);
            themNeuCo(b, bien, "gap_type", gapType);
            return b.build(bien);
        }, KnowledgeGapPage.class);
    }

    /** UC027 bước 7 — tín hiệu chất lượng trong {@code [tu, den)}, đếm theo THỜI ĐIỂM LƯỢT. */
    public QualitySummary quality(UUID tenantId, Instant tu, Instant den) {
        return ai.get(tenantId, b -> {
            Map<String, Object> bien = new HashMap<>();
            b.path("/v1/ai/quality");
            themNeuCo(b, bien, "tu", tu);
            themNeuCo(b, bien, "den", den);
            return b.build(bien);
        }, QualitySummary.class);
    }

    /** Giá trị đi qua BIẾN URI (mã hoá chặt) — như {@code AiKnowledgeClient#themNeuCo}. */
    private static void themNeuCo(UriBuilder b, Map<String, Object> bien, String ten, Object giaTri) {
        if (giaTri != null && !(giaTri instanceof String s && s.isBlank())) {
            b.queryParam(ten, "{" + ten + "}");
            bien.put(ten, giaTri.toString());
        }
    }

    // ── Gương DTO ───────────────────────────────────────────────────────────────────

    public record InteractionCitation(UUID chunkId, UUID documentId, String documentTitle, String sectionPath,
            String snippet) {
    }

    /** Đánh giá của NGƯỜI. {@code raterUserId} để java-core tra tên nhân viên ở {@code platform.users}. */
    public record InteractionFeedback(UUID id, String raterType, UUID raterUserId, String rating, String reasonCode,
            String comment, String correctedAnswer, OffsetDateTime ratedAt) {
    }

    public record InteractionItem(
            UUID id,
            UUID conversationId,
            UUID messageId,
            String route,
            String intent,
            Double intentConfidence,
            String userQuery,
            String answerText,
            boolean refused,
            String refusalReason,
            String discardedAnswer,
            Double retrievalTopScore,
            Double groundednessScore,
            String modelName,
            String modelVersion,
            int promptTokens,
            int completionTokens,
            double costVnd,
            Integer latencyMs,
            Map<String, Integer> latencyBreakdown,
            String status,
            boolean llmCalled,
            boolean degraded,
            boolean handoff,
            boolean cached,
            List<InteractionCitation> citations,
            List<InteractionFeedback> feedback,
            OffsetDateTime createdAt) {
    }

    public record InteractionPage(List<InteractionItem> items, long total, int page, int size) {
    }

    /**
     * Gương {@code FeedbackRequest} — {@code extra="forbid"} phía ai-service: KHÔNG có trường tenant.
     * {@code rating} là 1/−1; {@code raterType} luôn điền (null thì ai-service 422).
     */
    public record FeedbackRequest(int rating, String reasonCode, String raterType, UUID raterUserId, String comment,
            String correctedAnswer) {
    }

    public record FeedbackRecorded(String message, UUID feedbackId, boolean created) {
    }

    public record KnowledgeGap(UUID id, String queryText, String gapType, int unansweredCount,
            int distinctConversationCount, OffsetDateTime firstOccurredAt, OffsetDateTime lastOccurredAt) {
    }

    public record KnowledgeGapPage(List<KnowledgeGap> items, long total, int page, int size) {
    }

    /** Tỉ lệ luôn đi kèm tử số và mẫu số — cộng hai phía là cộng tử với tử, mẫu với mẫu. */
    public record TyLe(long tuSo, long mauSo, Double giaTri) {
    }

    public record DanhGiaPhia(String raterType, TyLe tyLeTichCuc) {
    }

    /** Chỉ phần java-core dùng (UC039 ô "Phản hồi tích cực"); các tín hiệu khác bỏ qua. */
    public record QualitySummary(List<DanhGiaPhia> danhGia) {
    }
}
