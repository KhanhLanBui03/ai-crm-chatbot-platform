package com.thesis.crm.platform.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.math.BigDecimal;
import java.time.Instant;

/**
 * Hạn mức sử dụng trong chu kỳ hiện tại (SCR014, UC006).
 *
 * @param costVnd chi phí AI từ đầu chu kỳ tới nay — cộng từ sự kiện {@code ai.turn.completed} vào
 *     {@code analytics.metrics_daily} (UC039), không gọi đồng bộ sang ai-service
 * @param warnedAt mốc chạm 80% SỚM NHẤT trong bốn chỉ số
 * @param blockedAt mốc chạm 100% sớm nhất của hội thoại hoặc token AI — hai chỉ số làm tác tử ngừng trả lời
 *     tự động. Tài liệu và người dùng chạm trần chỉ chặn việc THÊM mới, không chặn tác tử.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record HanMucSuDungResponse(
        String periodStart,
        String periodEnd,
        MotHanMucDto conversations,
        MotHanMucDto tokens,
        MotHanMucDto users,
        MotHanMucDto documents,
        BigDecimal costVnd,
        Instant warnedAt,
        Instant blockedAt
) {}
