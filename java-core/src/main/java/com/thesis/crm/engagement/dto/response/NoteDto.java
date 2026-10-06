package com.thesis.crm.engagement.dto.response;

import java.time.Instant;
import java.util.UUID;

/**
 * {@code GhiChu} (docs/openapi/dashboard-api.yaml) — ghi chú nội bộ, KHÔNG BAO GIỜ hiện cho khách.
 *
 * @param flaggedSensitive có dấu hiệu dữ liệu cá nhân nhạy cảm — hệ thống nhắc, không chặn
 * @param canEdit          người đang xem là tác giả hoặc quản trị viên
 * @param editedAt         lần sửa NỘI DUNG gần nhất ({@code edited_at}, V125) — ghim không tính
 */
public record NoteDto(
        UUID id,
        String content,
        UUID conversationId,
        UUID authorUserId,
        String authorName,
        boolean isPinned,
        boolean flaggedSensitive,
        boolean canEdit,
        Instant editedAt,
        Instant createdAt) {}
