package com.thesis.crm.engagement.inbox;

import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** Hình dạng dữ liệu của {@code /api/v1/conversations/**} — khớp schema trong dashboard-api.yaml. */
public final class InboxDtos {

    private InboxDtos() {}

    /** {@code HoiThoaiTomTat} — một dòng của danh sách hộp thư. */
    public record ConversationSummary(
            UUID id, UUID contactId, String contactName, String channelType, String status,
            UUID assignedUserId, String assignedUserName, int priority, Instant lastMessageAt,
            String lastMessagePreview, int messageCount, int unreadCount, List<TagDto> tags,
            Instant startedAt) {}

    /** {@code TrichDan}. */
    public record CitationDto(String chunkId, String documentId, String documentTitle, String sectionPath,
                              String snippet) {}

    /** {@code TinNhan}. */
    public record MessageDto(
            UUID id, String senderType, UUID senderUserId, String senderName, String content,
            String contentType, String deliveryStatus, String failureReason, List<Object> attachments,
            UUID aiInteractionId, List<CitationDto> citations, Instant createdAt, Instant sentAt) {}

    /** {@code CursorPage} của tin nhắn. {@code nextCursor} truyền vào {@code before} lần sau. */
    public record MessagePage(List<MessageDto> items, boolean hasMore, Instant nextCursor) {}

    /**
     * {@code HoiThoaiChiTiet} — tóm tắt + trang tin mới nhất. {@code firstResponseAt} là phản hồi
     * đầu tiên của CON NGƯỜI (cột {@code first_agent_response_at}, V128), đúng mô tả của hợp đồng.
     */
    public record ConversationDetail(
            UUID id, UUID contactId, String contactName, String channelType, String status,
            UUID assignedUserId, String assignedUserName, int priority, Instant lastMessageAt,
            String lastMessagePreview, int messageCount, int unreadCount, List<TagDto> tags,
            Instant startedAt,
            boolean autoReplyEnabled, Boolean botResolved, int consecutiveRefusals,
            Instant firstResponseAt, Instant resolvedAt, String closedReason,
            List<MessageDto> messages, boolean hasMoreMessages) {}

    /**
     * {@code NguCanhHoiThoai}. Tóm tắt (UC026), lượt AI gần nhất và điểm tiềm năng chưa có nguồn
     * dữ liệu → {@code null}; giao diện hiện "Chưa có".
     */
    public record ConversationContext(ContactDto contact, Object summary, Object lastAiInteraction,
                                      Object leadScore, UUID openLeadId) {}

    /** {@code SuKienChuyenGiao}. Chưa có bảng sự kiện chuyển giao riêng — dựng từ thao tác vừa làm. */
    public record HandoffEvent(UUID id, String direction, String reason, String triggeredBy,
                               boolean countsAgainstAiQuality, UUID toUserId, Instant queuedAt,
                               Instant acceptedAt, Instant occurredAt) {}

    // ── yêu cầu ─────────────────────────────────────────────────────────────────

    public record SendMessageRequest(String content, String contentType, UUID cannedResponseId) {}

    public record AssignRequest(UUID assigneeUserId, String reason) {}

    public record HandoffRequest(String direction, String reason) {}

    public record StatusRequest(String status, String reason) {}
}
