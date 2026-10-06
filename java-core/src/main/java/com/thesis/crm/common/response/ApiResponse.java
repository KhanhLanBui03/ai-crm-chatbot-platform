package com.thesis.crm.common.response;

import java.time.Instant;

/**
 * Vỏ phản hồi dùng chung cho mọi endpoint của java-core.
 *
 * <p>Có {@code traceId} để nối một phản hồi lỗi với dòng log tương ứng — gateway gắn
 * {@code X-Trace-Id} cho mọi request và giá trị đó đi xuyên suốt mọi chặng (kế hoạch mục 4.5).
 *
 * <p>{@code code} là mã nghiệp vụ của lỗi ({@code DOCUMENT_QUOTA_EXCEEDED}, …) — giao diện rẽ
 * nhánh theo nó, không theo {@code message}. Mã HTTP không đủ: một 409 có thể là hết hạn mức
 * hoặc hết thuê bao, và hai trường hợp đó dẫn người dùng tới hai màn khác nhau. Thêm ở UC018,
 * đề xuất vá {@code dashboard-api.yaml} ở {@code docs/contracts/uc018-tai-tai-lieu.md} mục 9.
 *
 * @param <T> kiểu dữ liệu trả về
 */
public record ApiResponse<T>(
        boolean success,
        T data,
        String message,
        String code,
        String traceId,
        Instant timestamp) {

    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, data, null, null, null, Instant.now());
    }

    public static <T> ApiResponse<T> error(String message, String traceId) {
        return new ApiResponse<>(false, null, message, null, traceId, Instant.now());
    }

    /** Lỗi có mã nghiệp vụ. {@code data} mang ngữ cảnh cho giao diện — ví dụ mức hạn mức khi 409. */
    public static <T> ApiResponse<T> error(String code, String message, T data, String traceId) {
        return new ApiResponse<>(false, data, message, code, traceId, Instant.now());
    }
}
