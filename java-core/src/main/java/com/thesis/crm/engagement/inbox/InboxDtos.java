package com.thesis.crm.engagement.inbox;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import java.time.Instant;
import java.time.OffsetDateTime;
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
     * đầu tiên của CON NGƯỜI (cột {@code first_agent_response_at}, V130), đúng mô tả của hợp đồng.
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
     * {@code NguCanhHoiThoai}. {@code summary} (UC026) đọc năm cột tóm tắt của hội thoại;
     * {@code lastAiInteraction} là lượt mới nhất của hội thoại qua ai-service ({@code LuotXuLyAi}, GD2 —
     * ai-service lỗi thì {@code null}, cột phải vẫn mở). Điểm tiềm năng chưa có nguồn → {@code null}.
     */
    public record ConversationContext(ContactDto contact, SummaryDto summary, Object lastAiInteraction,
                                      Object leadScore, UUID openLeadId) {}

    /**
     * {@code TomTatHoiThoai} — bốn phần có tên (UC026 bước 3) + loại kích hoạt + ảnh chụp phiên bản model.
     * {@code isStale}: đã có tin mới sau lúc sinh — hiện chỉ báo thay vì giấu (mô tả của hợp đồng).
     */
    public record SummaryDto(String trigger, String mainNeed, String providedInfo, String unresolvedIssues,
                             String nextSteps, @JsonProperty("isStale") boolean isStale, String modelVersion,
                             Instant generatedAt) {}

    /** Một tin của {@code GET /internal/conversations/{id}/messages} — khuôn nháp hợp đồng UC026 mục 1. */
    public record InternalMessageDto(String senderType, String content, Instant sentAt,
                                     @JsonProperty("isRedacted") boolean isRedacted) {}

    /**
     * Thân {@code PATCH /internal/conversations/{id}/summary} do ai-service gửi (nháp UC026 mục 2,
     * {@code BanGhiTomTat.thanh_json()}).
     */
    public record WriteSummaryRequest(String trigger, String mainNeed, String providedInfo,
                                      String unresolvedIssues, String nextSteps, String modelVersion,
                                      String summaryText, OffsetDateTime generatedAt) {}

    /** {@code SuKienChuyenGiao}. Chưa có bảng sự kiện chuyển giao riêng — dựng từ thao tác vừa làm. */
    public record HandoffEvent(UUID id, String direction, String reason, String triggeredBy,
                               boolean countsAgainstAiQuality, UUID toUserId, Instant queuedAt,
                               Instant acceptedAt, Instant occurredAt) {}

    // ── yêu cầu ─────────────────────────────────────────────────────────────────

    public record SendMessageRequest(String content, String contentType, UUID cannedResponseId) {}

    public record AssignRequest(UUID assigneeUserId, String reason) {}

    public record HandoffRequest(String direction, String reason) {}

    /** UC015 1a — trả về hàng chờ, bắt nhập lý do. */
    public record ReleaseRequest(String reason) {}

    /** Tên trường theo hợp đồng: {@code closedReason}. */
    public record StatusRequest(String status, String closedReason) {}
}
