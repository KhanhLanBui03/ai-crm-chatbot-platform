package com.thesis.crm.common.exception;

import org.springframework.http.HttpStatus;

/**
 * Gốc của mọi lỗi nghiệp vụ mà java-core chủ động ném ra.
 *
 * <p>Mỗi lỗi mang sẵn mã HTTP và {@code code} nghiệp vụ, nên {@link GlobalExceptionHandler} chỉ
 * việc đóng vỏ {@code ApiResponse} — không có bảng tra mã thứ hai nào để quên cập nhật.
 *
 * <p>{@code message} đi thẳng tới người dùng, nên viết cho người dùng đọc và KHÔNG chứa dữ liệu
 * cá nhân (Nghị định 13). Chi tiết kỹ thuật thì ghi log ở chỗ ném, không nhét vào đây.
 */
public class BusinessException extends RuntimeException {

    private final HttpStatus status;
    private final String code;
    private final transient Object details;

    public BusinessException(HttpStatus status, String code, String message) {
        this(status, code, message, null);
    }

    public BusinessException(HttpStatus status, String code, String message, Object details) {
        super(message);
        this.status = status;
        this.code = code;
        this.details = details;
    }

    public HttpStatus getStatus() {
        return status;
    }

    public String getCode() {
        return code;
    }

    /** Ngữ cảnh cho giao diện, đi vào {@code ApiResponse.data}. Có thể {@code null}. */
    public Object getDetails() {
        return details;
    }
}
