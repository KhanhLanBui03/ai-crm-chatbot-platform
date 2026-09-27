package com.thesis.crm.platform.dto.response;

import com.thesis.crm.platform.entity.UsageRecord;
import java.time.Instant;

/**
 * Trạng thái một hạn mức — hình {@code MotHanMuc} của {@code dashboard-api.yaml} cộng hai mốc
 * {@code warnedAt}/{@code blockedAt} (V116).
 *
 * @param percent {@code used × 100 / quota}, làm tròn một chữ số thập phân; quota 0 thì 100
 */
public record QuotaUsageResponse(
        long used,
        long quota,
        double percent,
        Instant warnedAt,
        Instant blockedAt) {

    public static QuotaUsageResponse from(UsageRecord r) {
        double percent = r.getQuotaValue() == 0
                ? 100.0
                : Math.round(r.getUsedValue() * 1000.0 / r.getQuotaValue()) / 10.0;
        return new QuotaUsageResponse(r.getUsedValue(), r.getQuotaValue(), percent,
                r.getWarnedAt(), r.getBlockedAt());
    }
}
