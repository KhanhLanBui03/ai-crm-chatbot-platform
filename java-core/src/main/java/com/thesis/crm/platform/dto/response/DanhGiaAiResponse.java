package com.thesis.crm.platform.dto.response;

import java.time.Instant;
import java.util.UUID;

/**
 * {@code DanhGiaAi} — một đánh giá của người cho một lượt (UC027).
 *
 * @param ratedByUserId   mã nhân viên — giao diện nhận ra đánh giá của chính mình; {@code null} với khách
 * @param ratedByName     tên nhân viên ({@code platform.users}); {@code null} với đánh giá của khách
 * @param correctedAnswer câu trả lời đúng do nhân viên sửa — nguồn phát hiện khoảng trống tri thức
 * @param createdAt       lần ghi gần nhất: đánh giá lại (luồng phụ 2.1) cập nhật dòng cũ và đẩy mốc này
 */
public record DanhGiaAiResponse(
        UUID id,
        String rating,
        String reasonCode,
        String comment,
        String correctedAnswer,
        String ratedByType,
        UUID ratedByUserId,
        String ratedByName,
        Instant createdAt) {
}
