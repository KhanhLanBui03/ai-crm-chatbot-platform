package com.thesis.crm.engagement.inbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import com.thesis.crm.engagement.inbox.InboxDtos.CitationDto;
import com.thesis.crm.engagement.inbox.InboxDtos.ConversationContext;
import com.thesis.crm.engagement.inbox.InboxDtos.ConversationDetail;
import com.thesis.crm.engagement.inbox.InboxDtos.ConversationSummary;
import com.thesis.crm.engagement.inbox.InboxDtos.HandoffEvent;
import com.thesis.crm.engagement.inbox.InboxDtos.MessageDto;
import com.thesis.crm.engagement.inbox.InboxDtos.MessagePage;
import com.thesis.crm.engagement.inbox.InboxRepository.ConvRow;
import com.thesis.crm.engagement.inbox.InboxRepository.Filter;
import com.thesis.crm.engagement.inbox.InboxRepository.MsgRow;
import com.thesis.crm.engagement.repository.ContactQueryRepository;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC012 (hộp thư hợp nhất) + UC013 (nhân viên trả lời), kèm các thao tác khép vòng của UC014/UC015.
 *
 * <p>Quy tắc quyền đã chốt: mọi nhân viên XEM mọi hội thoại của doanh nghiệp; GỬI tin vào hội thoại
 * chưa ai nhận là tự nhận; hội thoại đã có người giữ thì chỉ người đó hoặc quản trị viên được gửi,
 * đóng, trả lại AI; giao cho người khác chỉ quản trị viên làm được.
 */
@Service
public class InboxService {

    /** Người đang thao tác — lấy từ JWT ở controller. */
    public record Actor(UUID userId, boolean admin) {}

    static final int MAX_CONTENT = 4000;
    static final int DEFAULT_MESSAGES = 30;
    static final String CLOSING_TEXT = "Cuộc trò chuyện đã kết thúc. Bạn cần thêm gì cứ nhắn tiếp nhé.";
    private static final Set<String> CLOSED = Set.of("RESOLVED", "CLOSED");
    private static final Set<String> STATUSES =
            Set.of("BOT_HANDLING", "PENDING_AGENT", "AGENT_HANDLING", "RESOLVED", "CLOSED");
    private static final Set<String> REASONS = Set.of("CUSTOMER_REQUEST", "LOW_CONFIDENCE", "NO_GROUNDING",
            "NEGATIVE_SENTIMENT", "REPEATED_FAILURE", "WRITE_TOOL_APPROVAL", "QUOTA_EXCEEDED", "LLM_ERROR");

    private final InboxRepository repo;
    private final ContactQueryRepository contacts;
    private final TenantTransactionScope scope;
    private final AuditLogWriter audit;
    private final ObjectMapper json;

    public InboxService(InboxRepository repo, ContactQueryRepository contacts, TenantTransactionScope scope,
                        AuditLogWriter audit, ObjectMapper json) {
        this.repo = repo;
        this.contacts = contacts;
        this.scope = scope;
        this.audit = audit;
        this.json = json;
    }

    // ── UC012: đọc ──────────────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public PageResponse<ConversationSummary> list(UUID tenantId, Actor actor, String scopeParam,
                                                  List<String> statuses, String channelType, UUID tagId,
                                                  String keyword, int page, int size) {
        scope.apply(tenantId);
        String sc = scopeParam == null ? "all" : scopeParam;
        if (!Set.of("all", "mine", "unassigned").contains(sc)) {
            throw invalid("scope chỉ nhận all, mine hoặc unassigned.");
        }
        if (statuses != null && !STATUSES.containsAll(statuses)) {
            throw invalid("Trạng thái hội thoại không hợp lệ.");
        }
        if (channelType != null && !Set.of("WEB_WIDGET", "ZALO", "FACEBOOK").contains(channelType)) {
            throw invalid("Loại kênh không hợp lệ.");
        }
        int p = Math.max(0, page);
        int s = Math.min(Math.max(1, size), 100);
        Filter f = new Filter(sc, actor.userId(), statuses, channelType, tagId, keyword, p, s);
        List<ConvRow> rows = repo.search(tenantId, f);
        Map<UUID, List<TagDto>> tags = repo.tagsOf(tenantId,
                rows.stream().map(ConvRow::contactId).filter(Objects::nonNull).toList());
        return PageResponse.of(rows.stream().map(r -> summary(r, tags)).toList(), p, s, repo.count(tenantId, f));
    }

    @Transactional(readOnly = true)
    public ConversationDetail detail(UUID tenantId, UUID conversationId) {
        scope.apply(tenantId);
        ConvRow r = require(tenantId, conversationId);
        MessagePage page = messagePage(tenantId, conversationId, null, DEFAULT_MESSAGES);
        List<TagDto> tags = r.contactId() == null ? List.of()
                : repo.tagsOf(tenantId, List.of(r.contactId())).getOrDefault(r.contactId(), List.of());
        return new ConversationDetail(r.id(), r.contactId(), r.contactName(), r.channelType(), r.status(),
                r.assignedUserId(), r.assignedUserName(), priority(r.priority()), r.lastMessageAt(), r.preview(),
                r.messageCount(), r.unreadCount(), tags, r.startedAt(),
                "BOT_HANDLING".equals(r.status()), null, 0,
                r.firstAgentResponseAt(), r.resolvedAt(), r.closedReason(),
                page.items(), page.hasMore());
    }

    @Transactional(readOnly = true)
    public MessagePage messages(UUID tenantId, UUID conversationId, Instant before, int size) {
        scope.apply(tenantId);
        require(tenantId, conversationId);
        return messagePage(tenantId, conversationId, before, Math.min(Math.max(1, size), 100));
    }

    @Transactional(readOnly = true)
    public ConversationContext context(UUID tenantId, UUID conversationId) {
        scope.apply(tenantId);
        ConvRow r = require(tenantId, conversationId);
        ContactDto contact = r.contactId() == null ? null : contacts.findById(tenantId, r.contactId()).orElse(null);
        // Tóm tắt (UC026), lượt AI gần nhất (UC039) và điểm tiềm năng (UC030) chưa có nguồn dữ liệu
        return new ConversationContext(contact, null, null, null, null);
    }

    /** UC012 bước 10. Không ghi nhật ký: chỉ là trạng thái hiển thị, không phải thao tác nghiệp vụ. */
    @Transactional
    public void markRead(UUID tenantId, UUID conversationId) {
        scope.apply(tenantId);
        require(tenantId, conversationId);
        repo.markRead(tenantId, conversationId);
    }

    // ── UC013: nhân viên trả lời ────────────────────────────────────────────────

    @Transactional
    public MessageDto send(UUID tenantId, Actor actor, UUID conversationId, String rawContent, String contentType) {
        scope.apply(tenantId);
        String content = rawContent == null ? "" : rawContent.strip();
        if (content.isEmpty()) {
            throw invalid("Tin nhắn không được để trống.");
        }
        if (content.length() > MAX_CONTENT) {
            throw invalid("Tin nhắn tối đa 4.000 ký tự.");
        }
        if (contentType != null && !"TEXT".equals(contentType)) {
            throw invalid("Hiện chỉ gửi được tin dạng chữ.");
        }
        ConvRow r = repo.lock(tenantId, conversationId).orElseThrow(InboxService::notFound);
        if (CLOSED.contains(r.status())) {
            throw new AppException("Hội thoại đã đóng — đợi khách nhắn lại.", HttpStatus.CONFLICT);
        }
        if (r.assignedUserId() == null) {
            // Gửi tin vào hội thoại chưa ai nhận = tự nhận; AI ngừng tự trả lời
            repo.assign(tenantId, conversationId, actor.userId());
            audit.recordUserAction(tenantId, actor.userId(), "CONVERSATION_ASSIGNED", "CONVERSATION",
                    conversationId, Map.of("assigneeUserId", actor.userId().toString(), "via", "FIRST_REPLY"));
        } else if (!r.assignedUserId().equals(actor.userId()) && !actor.admin()) {
            throw new AppException("Hội thoại đang do " + nameOr(r.assignedUserName()) + " phụ trách.",
                    HttpStatus.FORBIDDEN);
        } else if (!"AGENT_HANDLING".equals(r.status())) {
            repo.assign(tenantId, conversationId, r.assignedUserId());
        }
        // Kênh duy nhất đang chạy là widget: khách nhận qua lần hỏi tin mới kế tiếp → coi như đã giao.
        // Zalo/Facebook cần bộ chuyển đổi kênh gửi ra ngoài (chưa có) → để PENDING cho tiến trình gửi.
        String delivery = "WEB_WIDGET".equals(r.channelType()) ? "DELIVERED" : "PENDING";
        return toDto(repo.insertMessage(tenantId, conversationId, "AGENT", actor.userId(), content, delivery));
    }

    // ── UC015 / UC014: phân công, chuyển giao, đóng ─────────────────────────────

    @Transactional
    public ConversationSummary assign(UUID tenantId, Actor actor, UUID conversationId, UUID assigneeUserId) {
        scope.apply(tenantId);
        ConvRow r = repo.lock(tenantId, conversationId).orElseThrow(InboxService::notFound);
        if (CLOSED.contains(r.status())) {
            throw new AppException("Hội thoại đã đóng.", HttpStatus.CONFLICT);
        }
        UUID target = assigneeUserId == null ? actor.userId() : assigneeUserId;
        if (!actor.admin()) {
            if (!target.equals(actor.userId())) {
                throw new AppException("Chỉ quản trị viên được giao hội thoại cho người khác.", HttpStatus.FORBIDDEN);
            }
            if (r.assignedUserId() != null && !r.assignedUserId().equals(actor.userId())) {
                throw new AppException("Hội thoại đang do " + nameOr(r.assignedUserName()) + " phụ trách.",
                        HttpStatus.FORBIDDEN);
            }
        }
        if (repo.activeUserName(tenantId, target).isEmpty()) {
            throw invalid("Người được giao không thuộc doanh nghiệp hoặc đã bị khoá.");
        }
        repo.assign(tenantId, conversationId, target);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("assigneeUserId", target.toString());
        data.put("previousAssigneeUserId", r.assignedUserId() == null ? null : r.assignedUserId().toString());
        audit.recordUserAction(tenantId, actor.userId(), "CONVERSATION_ASSIGNED", "CONVERSATION", conversationId, data);
        ConvRow after = require(tenantId, conversationId);
        return summary(after, repo.tagsOf(tenantId, after.contactId() == null ? List.of() : List.of(after.contactId())));
    }

    @Transactional
    public HandoffEvent handoff(UUID tenantId, Actor actor, UUID conversationId, String direction, String reason) {
        scope.apply(tenantId);
        if (reason == null || !REASONS.contains(reason)) {
            throw invalid("Lý do chuyển giao không hợp lệ.");
        }
        ConvRow r = repo.lock(tenantId, conversationId).orElseThrow(InboxService::notFound);
        if (CLOSED.contains(r.status())) {
            throw new AppException("Hội thoại đã đóng.", HttpStatus.CONFLICT);
        }
        Instant now = Instant.now();
        if ("AGENT_TO_BOT".equals(direction)) {
            requireHolderOrAdmin(r, actor);
            if ("BOT_HANDLING".equals(r.status())) {
                throw new AppException("Tác tử AI đang giữ hội thoại này rồi.", HttpStatus.CONFLICT);
            }
            repo.returnToBot(tenantId, conversationId);
        } else if ("BOT_TO_AGENT".equals(direction)) {
            if (!"BOT_HANDLING".equals(r.status())) {
                throw new AppException("Hội thoại đã ở phía nhân viên.", HttpStatus.CONFLICT);
            }
            repo.handoffToAgent(tenantId, conversationId, reason);
        } else {
            throw invalid("direction chỉ nhận BOT_TO_AGENT hoặc AGENT_TO_BOT.");
        }
        audit.recordUserAction(tenantId, actor.userId(), "CONVERSATION_HANDOFF", "CONVERSATION", conversationId,
                Map.of("direction", direction, "reason", reason));
        // Hết hạn mức không phải lỗi của AI — không tính vào chất lượng (hợp đồng SuKienChuyenGiao)
        boolean countsAgainstAi = "BOT_TO_AGENT".equals(direction) && !"QUOTA_EXCEEDED".equals(reason);
        return new HandoffEvent(UUID.randomUUID(), direction, reason, "AGENT", countsAgainstAi, null,
                "BOT_TO_AGENT".equals(direction) ? now : null, null, now);
    }

    @Transactional
    public ConversationSummary changeStatus(UUID tenantId, Actor actor, UUID conversationId, String status,
                                            String reason) {
        scope.apply(tenantId);
        if (!CLOSED.contains(status == null ? "" : status)) {
            throw invalid("Chỉ chuyển được sang RESOLVED hoặc CLOSED.");
        }
        if (reason != null && reason.length() > 50) {
            throw invalid("Lý do đóng tối đa 50 ký tự.");
        }
        ConvRow r = repo.lock(tenantId, conversationId).orElseThrow(InboxService::notFound);
        if (CLOSED.contains(r.status())) {
            throw new AppException("Hội thoại đã đóng rồi.", HttpStatus.CONFLICT);
        }
        requireHolderOrAdmin(r, actor);
        repo.close(tenantId, conversationId, status, reason);
        // Khách thấy câu kết thúc ở lần hỏi tin mới kế tiếp; nhắn tiếp thì widget mở hội thoại mới
        repo.insertMessage(tenantId, conversationId, "SYSTEM", null, CLOSING_TEXT, "DELIVERED");
        audit.recordUserAction(tenantId, actor.userId(), "CONVERSATION_STATUS_CHANGED", "CONVERSATION",
                conversationId, Map.of("from", r.status(), "to", status));
        ConvRow after = require(tenantId, conversationId);
        return summary(after, repo.tagsOf(tenantId, after.contactId() == null ? List.of() : List.of(after.contactId())));
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    /** Đã có người giữ thì chỉ người đó hoặc quản trị viên; chưa ai giữ thì nhân viên nào cũng được. */
    private static void requireHolderOrAdmin(ConvRow r, Actor actor) {
        if (r.assignedUserId() != null && !r.assignedUserId().equals(actor.userId()) && !actor.admin()) {
            throw new AppException("Hội thoại đang do " + nameOr(r.assignedUserName()) + " phụ trách.",
                    HttpStatus.FORBIDDEN);
        }
    }

    private MessagePage messagePage(UUID tenantId, UUID conversationId, Instant before, int limit) {
        List<MsgRow> rows = repo.messages(tenantId, conversationId, before, limit + 1);
        boolean hasMore = rows.size() > limit;
        List<MsgRow> page = new ArrayList<>(hasMore ? rows.subList(0, limit) : rows);
        java.util.Collections.reverse(page);     // tăng dần theo thời gian để hiển thị
        Instant cursor = hasMore && !page.isEmpty() ? page.get(0).sentAt() : null;
        return new MessagePage(page.stream().map(this::toDto).toList(), hasMore, cursor);
    }

    private ConvRow require(UUID tenantId, UUID conversationId) {
        return repo.find(tenantId, conversationId).orElseThrow(InboxService::notFound);
    }

    private static ConversationSummary summary(ConvRow r, Map<UUID, List<TagDto>> tags) {
        return new ConversationSummary(r.id(), r.contactId(), r.contactName(), r.channelType(), r.status(),
                r.assignedUserId(), r.assignedUserName(), priority(r.priority()), r.lastMessageAt(), r.preview(),
                r.messageCount(), r.unreadCount(),
                r.contactId() == null ? List.of() : tags.getOrDefault(r.contactId(), List.of()), r.startedAt());
    }

    /** CSDL lưu chữ (LOW…URGENT), hợp đồng khai số nguyên để sắp xếp được. */
    static int priority(String p) {
        return switch (p == null ? "NORMAL" : p) {
            case "LOW" -> 0;
            case "HIGH" -> 2;
            case "URGENT" -> 3;
            default -> 1;
        };
    }

    private MessageDto toDto(MsgRow m) {
        List<CitationDto> citations = new ArrayList<>();
        for (JsonNode c : readJson(m.metadataJson()).path("citations")) {
            String title = c.path("title").asText(null);
            citations.add(new CitationDto(c.path("chunkId").asText(null), c.path("documentId").asText(null),
                    title == null ? "Tài liệu không tên" : title, null, c.path("snippet").asText(null)));
        }
        List<Object> attachments = new ArrayList<>();
        readJson(m.attachmentsJson()).forEach(attachments::add);
        return new MessageDto(m.id(), m.senderType(), m.senderUserId(), m.senderName(), m.content(),
                m.contentType(), m.deliveryStatus(), null, attachments, m.aiInteractionId(), citations,
                m.createdAt(), m.sentAt());
    }

    private JsonNode readJson(String raw) {
        try {
            return raw == null ? json.createObjectNode() : json.readTree(raw);
        } catch (JsonProcessingException e) {
            return json.createObjectNode();
        }
    }

    private static String nameOr(String name) {
        return name == null || name.isBlank() ? "một nhân viên khác" : name;
    }

    private static AppException notFound() {
        return new AppException("Không tìm thấy hội thoại.", HttpStatus.NOT_FOUND);
    }

    private static AppException invalid(String msg) {
        return new AppException(msg, HttpStatus.UNPROCESSABLE_ENTITY);
    }
}
