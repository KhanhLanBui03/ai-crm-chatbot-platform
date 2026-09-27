package com.thesis.crm.platform.dto.response;

/**
 * Một mục hạn mức sử dụng (used / quota / percent).
 */
public record MotHanMucDto(
        long used,
        long quota,
        double percent
) {
    public static MotHanMucDto of(long used, long quota) {
        double pct = quota > 0 ? Math.min(100.0, Math.round(((double) used / quota) * 1000.0) / 10.0) : 0.0;
        return new MotHanMucDto(used, quota, pct);
    }
}
