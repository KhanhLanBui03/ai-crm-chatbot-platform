package com.thesis.crm.platform.dto.response;

import java.time.Instant;
import java.util.UUID;

/**
 * {@code KhoangTrongTriThuc} — SCR034, UC025 bước 8. Truy vấn gộp phía ai-service, không có bảng riêng.
 *
 * @param distinctContactCount XẤP XỈ bằng số hội thoại khác nhau: {@code ai_interactions} không có
 *                             {@code contact_id} (liên làn) — ghi ở "giảm độ sâu" của báo cáo
 * @param priority             bậc 1–3 do java-core chiếu từ {@code distinctContactCount}, để giao diện tô
 *                             màu mà không tự đặt ngưỡng
 */
public record KhoangTrongTriThucResponse(
        UUID id,
        String questionText,
        String gapType,
        int occurrenceCount,
        int distinctContactCount,
        int priority,
        Instant firstSeenAt,
        Instant lastSeenAt) {
}
