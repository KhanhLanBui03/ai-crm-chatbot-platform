package com.thesis.crm.common.response;

import java.time.Instant;

/**
 * Vỏ phản hồi dùng chung cho mọi endpoint của java-core.
 *
 * <p>Có {@code traceId} để nối một phản hồi lỗi với dòng log tương ứng — gateway gắn
 * {@code X-Trace-Id} cho mọi request và giá trị đó đi xuyên suốt mọi chặng (kế hoạch mục 4.5).
 *
 * @param <T> kiểu dữ liệu trả về
 */
public record ApiResponse<T>(
        boolean success,
        T data,
        String message,
        String traceId,
        Instant timestamp) {

    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, data, null, null, Instant.now());
    }

    public static <T> ApiResponse<T> error(String message, String traceId) {
        return new ApiResponse<>(false, null, message, traceId, Instant.now());
    }
}
