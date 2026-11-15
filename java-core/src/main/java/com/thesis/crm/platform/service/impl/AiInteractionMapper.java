package com.thesis.crm.platform.service.impl;

import com.thesis.crm.client.AiInteractionClient.InteractionFeedback;
import com.thesis.crm.client.AiInteractionClient.InteractionItem;
import com.thesis.crm.client.AiInteractionClient.KnowledgeGap;
import com.thesis.crm.platform.dto.response.DanhGiaAiResponse;
import com.thesis.crm.platform.dto.response.KhoangTrongTriThucResponse;
import com.thesis.crm.platform.dto.response.LuotXuLyAiResponse;
import com.thesis.crm.platform.dto.response.LuotXuLyAiResponse.TrichDan;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Gương ai-service → hình {@code dashboard-api.yaml}. Chỉ ĐỔI TÊN và GỘP chặng độ trễ; mọi con số là số
 * ai-service đã ghi. Bảng ánh xạ ở kế hoạch tích hợp giao diện mục UC027 và nháp hợp đồng mục 4.
 */
final class AiInteractionMapper {

    private AiInteractionMapper() {
    }

    static LuotXuLyAiResponse luot(InteractionItem i, Map<UUID, String> tenNhanVien) {
        // Đánh giá của khách không có raterUserId; `tenNhanVien` có thể là Map.of() — get(null) ném NPE (GD4)
        List<DanhGiaAiResponse> danhGia = i.feedback() == null ? List.of()
                : i.feedback().stream().map(f -> danhGia(f,
                        f.raterUserId() == null ? null : tenNhanVien.get(f.raterUserId()))).toList();
        List<TrichDan> trichDan = i.citations() == null ? List.of()
                : i.citations().stream().map(c -> new TrichDan(c.chunkId(), c.documentId(),
                        c.documentTitle() == null ? "Tài liệu không tên" : c.documentTitle(), c.sectionPath(),
                        c.snippet())).toList();
        return new LuotXuLyAiResponse(i.id(), i.conversationId(), i.messageId(), i.route(), i.intent(),
                i.intentConfidence(), i.userQuery(), i.answerText(), i.modelName(), i.modelVersion(),
                i.promptTokens(), i.completionTokens(), i.costVnd(), i.latencyMs(), chang(i.latencyBreakdown()),
                i.retrievalTopScore(), i.groundednessScore(), trichDan, i.refused(), i.refusalReason(), i.cached(),
                i.degraded(), i.handoff(), i.discardedAnswer(), "SUCCESS".equals(i.status()) ? null : i.status(),
                List.of(), danhGia.isEmpty() ? null : danhGia.get(0), danhGia, instant(i.createdAt()));
    }

    static DanhGiaAiResponse danhGia(InteractionFeedback f, String tenNhanVien) {
        return new DanhGiaAiResponse(f.id(), f.rating(), f.reasonCode(), f.comment(), f.correctedAnswer(),
                f.raterType(), f.raterUserId(), "AGENT".equals(f.raterType()) ? tenNhanVien : null,
                instant(f.ratedAt()));
    }

    static KhoangTrongTriThucResponse khoangTrong(KnowledgeGap g) {
        return new KhoangTrongTriThucResponse(g.id(), g.queryText(), g.gapType(), g.unansweredCount(),
                g.distinctConversationCount(), bac(g.distinctConversationCount()), instant(g.firstOccurredAt()),
                instant(g.lastOccurredAt()));
    }

    /**
     * Bậc ưu tiên từ số khách khác nhau: 1 (cao) từ 5 khách, 2 từ 2 khách, 3 khi chỉ một khách hỏi. Một
     * khách hỏi đi hỏi lại là tín hiệu yếu hơn nhiều khách cùng vấp (UC025 luồng phụ 8.1).
     */
    static int bac(int soKhach) {
        return soKhach >= 5 ? 1 : soKhach >= 2 ? 2 : 3;
    }

    /**
     * Gộp chặng như {@code AiPerformanceService#chang}: {@code retrieve} gồm cả bước nhúng câu hỏi,
     * {@code guard} gồm kiểm duyệt trước và hậu kiểm. Chặng không chạy (0 hoặc vắng) thì không có khoá —
     * lượt mẫu câu không hiện "truy hồi 0 ms" như thể đã truy hồi.
     */
    static Map<String, Integer> chang(Map<String, Integer> raw) {
        Map<String, Integer> out = new LinkedHashMap<>();
        if (raw == null) {
            return out;
        }
        them(out, "retrieve", raw, "embed_ms", "retrieve_ms");
        them(out, "rerank", raw, "rerank_ms");
        them(out, "generate", raw, "generate_ms");
        them(out, "tool", raw, "tool_ms");
        them(out, "guard", raw, "guard_ms", "postguard_ms");
        them(out, "classify", raw, "classify_ms");
        return out;
    }

    private static void them(Map<String, Integer> out, String ten, Map<String, Integer> raw, String... khoa) {
        int tong = 0;
        for (String k : khoa) {
            tong += raw.getOrDefault(k, 0);
        }
        if (tong > 0) {
            out.put(ten, tong);
        }
    }

    private static Instant instant(OffsetDateTime t) {
        return t == null ? null : t.toInstant();
    }
}
