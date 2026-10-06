package com.thesis.crm.engagement.widget;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.engagement.widget.AiChatClient.AiReply;
import com.thesis.crm.engagement.widget.AiChatClient.Turn;
import com.thesis.crm.engagement.widget.WidgetDtos.Appearance;
import com.thesis.crm.engagement.widget.WidgetDtos.CitationDto;
import com.thesis.crm.engagement.widget.WidgetDtos.MessageDto;
import com.thesis.crm.engagement.widget.WidgetDtos.SessionResponse;
import com.thesis.crm.engagement.widget.WidgetDtos.TurnResponse;
import com.thesis.crm.engagement.widget.WidgetRepository.ChannelRow;
import com.thesis.crm.engagement.widget.WidgetRepository.ConversationRow;
import com.thesis.crm.engagement.widget.WidgetRepository.IdentityRow;
import com.thesis.crm.engagement.widget.WidgetRepository.MessageRow;
import com.thesis.crm.engagement.widget.WidgetRepository.QuotaRow;
import com.thesis.crm.engagement.widget.WidgetRepository.TenantState;
import com.thesis.crm.engagement.widget.WidgetTokenService.WidgetSession;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * UC009 bước 10–11 và UC010 — khách vãng lai chat qua widget.
 *
 * <p><b>Tenant</b> luôn lấy từ khoá công khai (đã tra ở CSDL) hoặc từ token do chính máy chủ ký,
 * không bao giờ từ thứ trình duyệt tự khai (luật 1). Mỗi transaction đặt {@code app.tenant_id}
 * trước truy vấn đầu tiên (luật 3).
 *
 * <p><b>Gọi AI nằm NGOÀI transaction</b>: một lượt AI mất vài giây; giữ kết nối CSDL và khoá dòng
 * suốt thời gian đó thì vài chục khách chat cùng lúc là cạn pool. Vì vậy một lượt gửi tin chia
 * hai transaction: (1) lưu tin khách và quyết định có gọi AI không, (2) lưu kết quả AI.
 */
@Service
public class WidgetService {

    static final int MAX_CONTENT = 1000;
    static final Duration NEW_CONVERSATION_AFTER = Duration.ofHours(24);
    private static final int HISTORY_FOR_AI = 10;
    private static final int HISTORY_FOR_WIDGET = 50;
    private static final Set<String> CLOSED = Set.of("RESOLVED", "CLOSED");
    private static final Set<String> WITH_AGENT = Set.of("PENDING_AGENT", "AGENT_HANDLING");

    static final String HANDOFF_TEXT = "Cảm ơn bạn! Nhân viên sẽ liên hệ với bạn trong thời gian sớm nhất.";

    private final WidgetRepository repo;
    private final WidgetTokenService tokens;
    private final WidgetRateLimiter limiter;
    private final AiChatClient ai;
    private final TenantTransactionScope scope;
    private final AuditLogWriter audit;
    private final TransactionTemplate tx;
    private final ObjectMapper json;

    public WidgetService(WidgetRepository repo, WidgetTokenService tokens, WidgetRateLimiter limiter,
                         AiChatClient ai, TenantTransactionScope scope, AuditLogWriter audit,
                         TransactionTemplate tx, ObjectMapper json) {
        this.repo = repo;
        this.tokens = tokens;
        this.limiter = limiter;
        this.ai = ai;
        this.scope = scope;
        this.audit = audit;
        this.tx = tx;
        this.json = json;
    }

    // ── Mở phiên (UC009 bước 10–11) ─────────────────────────────────────────────

    public SessionResponse startSession(String widgetKey, String origin, String oldToken, String clientIp) {
        limiter.checkSession(clientIp);
        ChannelRow ch = repo.resolveKey(widgetKey.trim())
                .orElseThrow(() -> new AppException("Không tìm thấy widget.", HttpStatus.NOT_FOUND));
        JsonNode config = readJson(ch.configJson());

        SessionResponse res = tx.execute(st -> {
            scope.apply(ch.tenantId());
            if (!WidgetOriginPolicy.allowed(origin, domains(config))) {
                // 10.2 — ghi nhận nỗ lực truy cập. Trả null rồi ném NGOÀI transaction: ném trong này
                // thì dòng kiểm toán rollback theo.
                audit.recordSystemAction(ch.tenantId(), "WIDGET_ORIGIN_REJECTED", "CHANNEL", ch.channelId(),
                        "WARNING", Map.of("origin", WidgetOriginPolicy.hostOf(origin).orElse("(không có)")));
                return null;
            }
            if (!serviceLive(ch)) {
                return new SessionResponse("SUSPENDED", null, null, null, List.of());
            }
            UUID visitorId = tokens.parse(oldToken)
                    .filter(s -> s.tenantId().equals(ch.tenantId()) && s.channelId().equals(ch.channelId()))
                    .map(WidgetSession::visitorId)
                    .orElseGet(UUID::randomUUID);
            WidgetSession session = new WidgetSession(ch.tenantId(), ch.channelId(), visitorId);

            Optional<ConversationRow> conv =
                    repo.latestConversationOfVisitor(ch.tenantId(), ch.channelId(), visitorId.toString());
            List<MessageDto> history = conv
                    .map(c -> repo.messages(ch.tenantId(), c.id(), null, HISTORY_FOR_WIDGET).stream()
                            .map(this::toDto).toList())
                    .orElse(List.of());
            return new SessionResponse("ACTIVE", tokens.issue(session), appearance(config),
                    conv.map(ConversationRow::status).orElse(null), history);
        });
        if (res == null) {
            throw new AppException("Tên miền này chưa được phép nhúng widget.", HttpStatus.FORBIDDEN);
        }
        return res;
    }

    // ── Gửi tin (UC010) ─────────────────────────────────────────────────────────

    private enum Next { NONE, CALL_AI }

    private record Accepted(UUID conversationId, Next next, List<MessageDto> messages,
                            List<Turn> history, String hoursNote) {}

    public TurnResponse sendMessage(String token, String origin, String rawContent, String traceId) {
        WidgetSession s = tokens.require(token);
        limiter.checkMessage(s.visitorId().toString());
        String content = rawContent == null ? "" : rawContent.strip();
        if (content.isEmpty()) {
            throw new AppException("Tin nhắn không được để trống.", HttpStatus.UNPROCESSABLE_ENTITY);
        }
        if (content.length() > MAX_CONTENT) {
            throw new AppException("Tin nhắn tối đa 1.000 ký tự — bạn chia thành vài tin ngắn hơn nhé.",
                    HttpStatus.UNPROCESSABLE_ENTITY);
        }

        // (1) Lưu tin khách, quyết định đường đi
        Accepted acc = tx.execute(st -> {
            scope.apply(s.tenantId());
            BusinessHours hours = requireAccess(s, origin);
            IdentityRow identity = identityOf(s);

            Optional<ConversationRow> last = repo.latestConversation(s.tenantId(), identity.id());
            boolean isNew = last.isEmpty() || CLOSED.contains(last.get().status())
                    || last.get().lastActivityAt().isBefore(Instant.now().minus(NEW_CONVERSATION_AFTER));

            boolean quotaExceeded = false;
            UUID conversationId;
            String status;
            if (isNew) {
                Optional<QuotaRow> quota = repo.lockConversationQuota(s.tenantId());
                if (quota.isPresent() && quota.get().used() >= quota.get().quota()) {
                    quotaExceeded = true;           // 6.1 — vẫn lưu, nhưng không gọi AI
                } else {
                    quota.ifPresent(q -> repo.incrementUsage(s.tenantId(), q.id()));
                }
                conversationId = repo.insertConversation(s.tenantId(), s.channelId(), identity.id(),
                        identity.contactId(), subjectOf(content));
                status = "BOT_HANDLING";
            } else {
                conversationId = last.get().id();
                status = last.get().status();
            }

            List<Turn> history = isNew ? List.of() : historyForAi(s.tenantId(), conversationId);
            List<MessageDto> out = new ArrayList<>();
            out.add(toDto(repo.insertMessage(s.tenantId(), conversationId, "CUSTOMER", "INBOUND", content, "{}")));
            repo.touch(s.tenantId(), identity.id(), identity.contactId());

            String hoursNote = hours.isOpenNow() ? "" : outsideHoursNote(hours);
            if (WITH_AGENT.contains(status)) {
                return new Accepted(conversationId, Next.NONE, out, history, hoursNote);   // 6.3–6.4
            }
            if (quotaExceeded) {
                handoffWithNotice(s.tenantId(), conversationId, "QUOTA_EXCEEDED", hoursNote, out);
                return new Accepted(conversationId, Next.NONE, out, history, hoursNote);
            }
            return new Accepted(conversationId, Next.CALL_AI, out, history, hoursNote);
        });

        if (acc.next() == Next.NONE) {
            return new TurnResponse(currentStatus(s, acc.conversationId()), acc.messages());
        }

        // Ngoài transaction — xem chú thích lớp
        Optional<AiReply> reply = ai.chat(s.tenantId(), acc.conversationId(), content, acc.history(), traceId);

        // (2) Lưu kết quả AI
        List<MessageDto> out = new ArrayList<>(acc.messages());
        tx.executeWithoutResult(st -> {
            scope.apply(s.tenantId());
            if (reply.isEmpty()) {
                handoffWithNotice(s.tenantId(), acc.conversationId(), "LLM_ERROR", acc.hoursNote(), out);
                return;
            }
            AiReply r = reply.get();
            if (!r.answer().isBlank()) {
                out.add(toDto(repo.insertMessage(s.tenantId(), acc.conversationId(), "BOT", "OUTBOUND",
                        r.answer(), botMetadata(r))));
            }
            if (r.handoff()) {
                // ai-service chỉ báo chuyển giao ở nhánh HANDOFF (khách xin gặp người / khiếu nại) và
                // TOOL_CALL (thao tác cần nhân viên, MCP đã hoãn) — đều là khách CHỦ ĐỘNG cần người;
                // độ tin cậy thấp thì AI hỏi lại chứ không chuyển giao (router.py BRANCH_TO_ROUTE).
                String reason = r.refused() ? "NO_GROUNDING" : "CUSTOMER_REQUEST";
                if (r.answer().isBlank()) {
                    handoffWithNotice(s.tenantId(), acc.conversationId(), reason, acc.hoursNote(), out);
                } else {
                    // AI đã tự nói câu chuyển giao — chỉ thêm tin hệ thống khi cần báo khung giờ (7.2)
                    handoffWithNoticeText(s.tenantId(), acc.conversationId(), reason,
                            acc.hoursNote().strip(), out);
                }
            } else if (r.answer().isBlank()) {
                handoffWithNotice(s.tenantId(), acc.conversationId(), "LLM_ERROR", acc.hoursNote(), out);
            }
        });
        return new TurnResponse(currentStatus(s, acc.conversationId()), out);
    }

    // ── Nút "Gặp nhân viên" ─────────────────────────────────────────────────────

    public TurnResponse requestAgent(String token, String origin) {
        WidgetSession s = tokens.require(token);
        limiter.checkMessage(s.visitorId().toString());
        return tx.execute(st -> {
            scope.apply(s.tenantId());
            BusinessHours hours = requireAccess(s, origin);
            ConversationRow conv = repo.latestConversationOfVisitor(s.tenantId(), s.channelId(), s.visitorId().toString())
                    .filter(c -> !CLOSED.contains(c.status()))
                    .orElseThrow(() -> new AppException(
                            "Bạn gửi một tin nhắn trước để nhân viên biết bạn cần hỗ trợ gì nhé.",
                            HttpStatus.CONFLICT));
            List<MessageDto> out = new ArrayList<>();
            if ("BOT_HANDLING".equals(conv.status())) {
                handoffWithNotice(s.tenantId(), conv.id(), "CUSTOMER_REQUEST",
                        hours.isOpenNow() ? "" : outsideHoursNote(hours), out);
            }
            return new TurnResponse(currentStatus(s, conv.id()), out);
        });
    }

    // ── Hỏi tin mới (nhân viên trả lời, UC013) ──────────────────────────────────

    public TurnResponse poll(String token, String origin, Instant after) {
        WidgetSession s = tokens.require(token);
        return tx.execute(st -> {
            scope.apply(s.tenantId());
            requireAccess(s, origin);
            return repo.latestConversationOfVisitor(s.tenantId(), s.channelId(), s.visitorId().toString())
                    .map(c -> new TurnResponse(c.status(),
                            repo.messages(s.tenantId(), c.id(), after, HISTORY_FOR_WIDGET).stream()
                                    .map(this::toDto).toList()))
                    .orElse(new TurnResponse(null, List.of()));
        });
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    /**
     * Kiểm lại mỗi request, không chỉ lúc mở phiên: token sống 30 ngày, trong lúc đó quản trị viên
     * có thể gỡ tên miền, tắt kênh, hoặc doanh nghiệp bị khoá.
     */
    private BusinessHours requireAccess(WidgetSession s, String origin) {
        ChannelRow ch = repo.channel(s.tenantId(), s.channelId())
                .orElseThrow(() -> new AppException("Widget không còn tồn tại.", HttpStatus.FORBIDDEN));
        if (!WidgetOriginPolicy.allowed(origin, domains(readJson(ch.configJson())))) {
            throw new AppException("Tên miền này chưa được phép nhúng widget.", HttpStatus.FORBIDDEN);
        }
        if (!serviceLive(ch)) {
            throw new AppException("Dịch vụ trò chuyện đang tạm ngừng.", HttpStatus.FORBIDDEN);
        }
        TenantState t = repo.tenantState(s.tenantId()).orElseThrow();
        return new BusinessHours(readJson(t.businessHoursJson()), t.timezone());
    }

    private boolean serviceLive(ChannelRow ch) {
        if (!"ACTIVE".equals(ch.status())) {
            return false;
        }
        return repo.tenantState(ch.tenantId())
                .map(t -> !"SUSPENDED".equals(t.status()) && !"EXPIRED".equals(t.status()) && t.hasLiveSubscription())
                .orElse(false);
    }

    /** Danh tính kênh + hồ sơ khách tên tạm, tạo ở tin ĐẦU TIÊN (không tạo khi chỉ mở widget). */
    private IdentityRow identityOf(WidgetSession s) {
        String ext = s.visitorId().toString();
        Optional<IdentityRow> found = repo.lockIdentity(s.tenantId(), s.channelId(), ext);
        if (found.isEmpty()) {
            repo.insertIdentityIfAbsent(s.tenantId(), s.channelId(), ext, visitorName(s.visitorId()));
            found = repo.lockIdentity(s.tenantId(), s.channelId(), ext);
        }
        IdentityRow id = found.orElseThrow();
        if (id.contactId() == null) {
            UUID contactId = repo.insertVisitorContact(s.tenantId(), visitorName(s.visitorId()));
            repo.linkIdentityContact(s.tenantId(), id.id(), contactId);
            id = new IdentityRow(id.id(), contactId);
        }
        return id;
    }

    static String visitorName(UUID visitorId) {
        return "Khách web #" + visitorId.toString().substring(0, 4).toUpperCase(Locale.ROOT);
    }

    private void handoffWithNotice(UUID tenantId, UUID conversationId, String reason, String hoursNote,
                                   List<MessageDto> out) {
        handoffWithNoticeText(tenantId, conversationId, reason, HANDOFF_TEXT + hoursNote, out);
    }

    /** Chuyển cho nhân viên; {@code notice} rỗng thì không thêm tin hệ thống. */
    private void handoffWithNoticeText(UUID tenantId, UUID conversationId, String reason, String notice,
                                       List<MessageDto> out) {
        if (repo.handoff(tenantId, conversationId, reason) && !notice.isEmpty()) {
            out.add(toDto(repo.insertMessage(tenantId, conversationId, "SYSTEM", "OUTBOUND", notice, "{}")));
        }
    }

    private static String outsideHoursNote(BusinessHours hours) {
        String d = hours.describe();
        return d.isEmpty() ? "" : " Hiện đã ngoài giờ làm việc; nhân viên phản hồi trong khung giờ: " + d + ".";
    }

    private List<Turn> historyForAi(UUID tenantId, UUID conversationId) {
        List<Turn> turns = new ArrayList<>();
        for (MessageRow m : repo.messages(tenantId, conversationId, null, HISTORY_FOR_AI)) {
            switch (m.senderType()) {
                case "CUSTOMER" -> turns.add(new Turn("user", m.content()));
                case "BOT", "AGENT" -> turns.add(new Turn("assistant", m.content()));
                default -> { }
            }
        }
        return turns;
    }

    private String currentStatus(WidgetSession s, UUID conversationId) {
        return tx.execute(st -> {
            scope.apply(s.tenantId());
            return repo.latestConversationOfVisitor(s.tenantId(), s.channelId(), s.visitorId().toString())
                    .filter(c -> c.id().equals(conversationId))
                    .map(ConversationRow::status).orElse(null);
        });
    }

    private static String subjectOf(String content) {
        return content.length() <= 200 ? content : content.substring(0, 199) + "…";
    }

    private String botMetadata(AiReply r) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("route", r.route());
        m.put("refused", r.refused());
        m.put("citations", r.citations().stream().map(c -> {
            Map<String, Object> x = new LinkedHashMap<>();
            x.put("documentId", c.documentId());
            x.put("title", c.title());
            x.put("snippet", c.snippet());
            return x;
        }).toList());
        try {
            return json.writeValueAsString(m);
        } catch (JsonProcessingException e) {
            return "{}";
        }
    }

    private MessageDto toDto(MessageRow m) {
        List<CitationDto> citations = new ArrayList<>();
        for (JsonNode c : readJson(m.metadataJson()).path("citations")) {
            citations.add(new CitationDto(c.path("documentId").asText(null), c.path("title").asText(null),
                    c.path("snippet").asText(null)));
        }
        return new MessageDto(m.id(), m.senderType(), m.content(), citations, m.sentAt());
    }

    private static Appearance appearance(JsonNode c) {
        return new Appearance(text(c, "primaryColor"), c.path("position").asText("BOTTOM_RIGHT"),
                text(c, "greetingMessage"), text(c, "avatarUrl"));
    }

    private static String text(JsonNode c, String field) {
        return c.hasNonNull(field) ? c.get(field).asText() : null;
    }

    private static List<String> domains(JsonNode config) {
        List<String> out = new ArrayList<>();
        config.path("allowedDomains").forEach(d -> out.add(d.asText()));
        return out;
    }

    private JsonNode readJson(String raw) {
        try {
            return raw == null ? json.createObjectNode() : json.readTree(raw);
        } catch (JsonProcessingException e) {
            return json.createObjectNode();
        }
    }
}
