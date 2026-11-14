package com.thesis.crm.engagement.inbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.client.AiServiceErrors;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.client.AiSummaryClient;
import com.thesis.crm.client.AiSummaryClient.SummarizeMessage;
import com.thesis.crm.client.AiSummaryClient.SummarizeRequest;
import com.thesis.crm.client.AiSummaryClient.SummarizeResponse;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.engagement.inbox.InboxDtos.InternalMessageDto;
import com.thesis.crm.engagement.inbox.InboxDtos.SummaryDto;
import com.thesis.crm.engagement.inbox.InboxDtos.WriteSummaryRequest;
import com.thesis.crm.engagement.inbox.SummaryRepository.MessageRow;
import com.thesis.crm.engagement.inbox.SummaryRepository.SummaryRow;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * UC026 — phần của CRM: cấp lịch sử cho ai-service, nhận bốn phần tóm tắt về, và hiện chúng ở cột phải.
 *
 * <p>ai-service KHÔNG ghi thẳng {@code engagement.conversations}: {@code ai_app} không có quyền trên
 * schema của Track A (ADR-0002). Đó là ranh giới quyền, không phải chuyện tiện lợi — một mô hình bị tiêm
 * chỉ thị cũng chỉ ghi được đúng năm cột tóm tắt qua endpoint này, không hơn.
 *
 * <p>Hai đường ghi, cùng một hàm ghi {@link #luu}:
 * <ul>
 *   <li>{@code CLOSING} — bất đồng bộ: {@code crm.conversation.closed} → worker ai-service →
 *       {@link #writeFromAi} qua {@code PATCH /internal/…/summary};</li>
 *   <li>{@code MANUAL} — đồng bộ: nhân viên bấm "Tóm tắt lại" → {@link #resummarize} gửi lịch sử sang
 *       {@code POST /v1/ai/summarize}, nhận bốn phần, tự ghi (chốt Q1 của GD3).</li>
 * </ul>
 */
@Service
public class SummaryService {

    /** Enum của V114 {@code summary_trigger}. */
    static final Set<String> TRIGGERS = Set.of("HANDOFF", "CLOSING", "TURN_THRESHOLD", "MANUAL");
    /** Trần cỡ trang của bề mặt nội bộ — ai-service đọc 200 tin một trang. */
    static final int MAX_INTERNAL_PAGE = 500;
    /** Trần của {@code SummarizeRequest.messages} ({@code max_length=2_000}) — giữ phần MỚI NHẤT. */
    static final int MAX_SUMMARIZE_MESSAGES = 2_000;

    private final SummaryRepository repo;
    private final TenantTransactionScope scope;
    private final TransactionTemplate tx;
    private final AiSummaryClient ai;
    private final ObjectMapper json;

    public SummaryService(SummaryRepository repo, TenantTransactionScope scope, TransactionTemplate tx,
                          AiSummaryClient ai, ObjectMapper json) {
        this.repo = repo;
        this.scope = scope;
        this.tx = tx;
        this.ai = ai;
        this.json = json;
    }

    // ── bề mặt nội bộ (ai-service gọi) ──────────────────────────────────────────

    /** UC026 bước 2. Cũ trước; tin đã che (UC041) vẫn trả, kèm cờ — ai-service tự bỏ qua. */
    @Transactional(readOnly = true)
    public PageResponse<InternalMessageDto> internalMessages(UUID tenantId, UUID conversationId, int page,
                                                             int size) {
        scope.apply(tenantId);
        requireExists(tenantId, conversationId);
        int p = Math.max(0, page);
        int s = Math.min(Math.max(1, size), MAX_INTERNAL_PAGE);
        List<InternalMessageDto> items = repo.messages(tenantId, conversationId, p * s, s).stream()
                .map(m -> new InternalMessageDto(m.senderType(), m.content(), m.sentAt(), m.redacted()))
                .toList();
        return PageResponse.of(items, p, s, repo.countMessages(tenantId, conversationId));
    }

    /** UC026 bước 4 — ai-service ghi bản tóm tắt. Luỹ đẳng: gửi lại cùng thân thì kết quả như một lần. */
    @Transactional
    public void writeFromAi(UUID tenantId, UUID conversationId, WriteSummaryRequest r) {
        scope.apply(tenantId);
        if (r == null || r.trigger() == null || !TRIGGERS.contains(r.trigger())) {
            throw invalid("trigger chỉ nhận HANDOFF, CLOSING, TURN_THRESHOLD hoặc MANUAL.");
        }
        if (r.generatedAt() == null) {
            throw invalid("Thiếu generatedAt.");
        }
        requireExists(tenantId, conversationId);
        luu(tenantId, conversationId, r.trigger(), r.mainNeed(), r.providedInfo(), r.unresolvedIssues(),
                r.nextSteps(), r.modelVersion(), r.summaryText(), r.generatedAt().toInstant());
    }

    // ── dashboard ───────────────────────────────────────────────────────────────

    /** Bản đang lưu cho cột phải; chưa có thì {@code null}. Gọi trong transaction của nơi gọi. */
    SummaryDto current(UUID tenantId, UUID conversationId) {
        return repo.summary(tenantId, conversationId).map(this::toDto).orElse(null);
    }

    /**
     * UC026 trigger {@code MANUAL}. Ba chặng, KHÔNG giữ transaction quanh lượt gọi mô hình (vài giây):
     * đọc lịch sử (transaction ngắn) → gọi ai-service → ghi (transaction ngắn). Mô hình hỏng thì bản
     * cũ giữ nguyên (luồng phụ 3.1) vì chưa có gì được ghi.
     */
    public SummaryDto resummarize(UUID tenantId, UUID conversationId) {
        List<SummarizeMessage> lichSu = tx.execute(st -> {
            scope.apply(tenantId);
            requireExists(tenantId, conversationId);
            long tong = repo.countMessages(tenantId, conversationId);
            return repo.messages(tenantId, conversationId, 0, (int) Math.max(1, tong)).stream()
                    .filter(m -> !m.redacted())
                    .map(SummaryService::tin)
                    .toList();
        });
        if (lichSu == null || lichSu.isEmpty()) {
            throw new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "CONVERSATION_TOO_SHORT",
                    "Hội thoại chưa có tin nhắn nào để tóm tắt.");
        }
        List<SummarizeMessage> gui = lichSu.size() <= MAX_SUMMARIZE_MESSAGES ? lichSu
                : lichSu.subList(lichSu.size() - MAX_SUMMARIZE_MESSAGES, lichSu.size());
        SummarizeResponse kq;
        try {
            kq = ai.summarize(tenantId, new SummarizeRequest(conversationId, "MANUAL", gui));
        } catch (AiServiceException ex) {
            throw AiServiceErrors.dich(ex);
        }
        return tx.execute(st -> {
            scope.apply(tenantId);
            requireExists(tenantId, conversationId);
            luu(tenantId, conversationId, "MANUAL", kq.mainNeed(), kq.providedInfo(), kq.unresolvedIssues(),
                    kq.nextSteps(), kq.modelVersion(), kq.summaryText(), kq.generatedAt());
            return current(tenantId, conversationId);
        });
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    /**
     * Hậu điều kiện UC026 là MỘT mệnh đề: bốn phần + thời điểm + phiên bản model + loại kích hoạt đi cùng
     * nhau (ràng buộc {@code ck_conv_summary_complete}). Thiếu phần nào thì từ chối cả bản — ai-service
     * gửi {@code "Không có"} cho phần trống, không bao giờ để rỗng.
     */
    private void luu(UUID tenantId, UUID conversationId, String trigger, String mainNeed, String providedInfo,
                     String unresolvedIssues, String nextSteps, String modelVersion, String summaryText,
                     Instant generatedAt) {
        if (blank(mainNeed) || blank(providedInfo) || blank(unresolvedIssues) || blank(nextSteps)) {
            throw invalid("Bản tóm tắt phải đủ bốn phần: mainNeed, providedInfo, unresolvedIssues, nextSteps.");
        }
        if (blank(modelVersion) || modelVersion.length() > 50) {
            throw invalid("modelVersion bắt buộc, tối đa 50 ký tự.");
        }
        Map<String, String> bonPhan = new LinkedHashMap<>();
        bonPhan.put("mainNeed", mainNeed);
        bonPhan.put("providedInfo", providedInfo);
        bonPhan.put("unresolvedIssues", unresolvedIssues);
        bonPhan.put("nextSteps", nextSteps);
        String phang = blank(summaryText) ? String.join("\n", bonPhan.values()) : summaryText;
        try {
            repo.writeSummary(tenantId, conversationId, json.writeValueAsString(bonPhan), trigger, modelVersion,
                    generatedAt, phang);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Không ghi được JSON tóm tắt", e);
        }
    }

    private SummaryDto toDto(SummaryRow r) {
        JsonNode d;
        try {
            d = json.readTree(r.dataJson());
        } catch (JsonProcessingException e) {
            d = json.createObjectNode();
        }
        return new SummaryDto(r.trigger(), text(d, "mainNeed"), text(d, "providedInfo"),
                text(d, "unresolvedIssues"), text(d, "nextSteps"), r.stale(), r.modelVersion(), r.summarizedAt());
    }

    private void requireExists(UUID tenantId, UUID conversationId) {
        if (!repo.exists(tenantId, conversationId)) {
            throw new BusinessException(HttpStatus.NOT_FOUND, "CONVERSATION_NOT_FOUND", "Không tìm thấy hội thoại.");
        }
    }

    private static SummarizeMessage tin(MessageRow m) {
        return new SummarizeMessage(m.senderType(), m.content() == null ? "" : m.content(), m.sentAt());
    }

    private static String text(JsonNode d, String key) {
        JsonNode v = d.get(key);
        return v == null || v.isNull() ? null : v.asText();
    }

    private static boolean blank(String s) {
        return s == null || s.isBlank();
    }

    private static BusinessException invalid(String msg) {
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "INVALID_SUMMARY", msg);
    }
}
