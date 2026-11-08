package com.thesis.crm.platform.dto.response;

import java.time.Instant;

/**
 * Một mục hạn mức sử dụng (used / quota / percent) kèm hai mốc thật của chu kỳ (V128, UC006 4.1–4.2).
 *
 * @param warnedAt lần đầu chạm 80% trong chu kỳ — đọc từ {@code usage_records.warned_at}, không tính lại
 * @param blockedAt lần đầu chạm 100% trong chu kỳ
 */
public record MotHanMucDto(
        long used,
        long quota,
        double percent,
        Instant warnedAt,
        Instant blockedAt
) {
    public static MotHanMucDto of(long used, long quota) {
        return of(used, quota, null, null);
    }

    public static MotHanMucDto of(long used, long quota, Instant warnedAt, Instant blockedAt) {
        double pct = quota > 0 ? Math.min(100.0, Math.round(((double) used / quota) * 1000.0) / 10.0) : 0.0;
        return new MotHanMucDto(used, quota, pct, warnedAt, blockedAt);
    }
}
