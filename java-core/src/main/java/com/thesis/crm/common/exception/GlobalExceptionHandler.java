package com.thesis.crm.common.exception;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.security.TraceIdFilter;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.validation.BindException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;

/**
 * Chỗ DUY NHẤT dịch ngoại lệ thành phản hồi HTTP. Mọi lỗi ra ngoài đều là {@code ApiResponse}
 * có {@code traceId}, để một dòng lỗi trên giao diện tra ngược được đúng dòng log.
 *
 * <p>Hai lỗi của Spring Security phải khai tường minh ở đây: {@code @PreAuthorize} ném
 * {@link AccessDeniedException} từ BÊN TRONG controller, nên nó tới advice này trước khi tới
 * {@code ExceptionTranslationFilter}. Không khai thì nhánh {@code Exception} bên dưới nuốt mất
 * và người dùng thiếu quyền nhận 500 thay vì 403.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /** Mã validate chung. Đặc tả UC018 gọi lỗi siêu dữ liệu là INVALID_METADATA. */
    static final String INVALID_METADATA = "INVALID_METADATA";

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResponse<Object>> handleBusiness(BusinessException ex) {
        if (ex.getStatus().is5xxServerError()) {
            log.error("Lỗi nghiệp vụ {} — {}", ex.getCode(), ex.getMessage(), ex);
        }
        return body(ex.getStatus(), ex.getCode(), ex.getMessage(), ex.getDetails());
    }

    /**
     * Tệp vượt {@code spring.servlet.multipart.max-file-size}. Nổ lúc servlet đọc multipart —
     * TRƯỚC khi Spring bind form, nên 413 luôn đứng trước 422 (hợp đồng UC018 mục 1.3).
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ApiResponse<Object>> handleTooLarge(MaxUploadSizeExceededException ex) {
        return body(HttpStatus.PAYLOAD_TOO_LARGE, "FILE_TOO_LARGE",
                "Tệp vượt quá 20 MB. Hãy tách nhỏ rồi tải lên từng phần.", null);
    }

    /**
     * Lỗi bind/validate form. Chỉ trả TÊN trường và lý do, không lặp lại giá trị người dùng đã
     * gửi — mô tả tài liệu có thể dài và chứa dữ liệu cá nhân.
     */
    @ExceptionHandler(BindException.class)
    public ResponseEntity<ApiResponse<Object>> handleBind(BindException ex) {
        String chiTiet = ex.getFieldErrors().stream()
                .map(e -> e.getField() + ": " + e.getDefaultMessage())
                .sorted()
                .collect(Collectors.joining("; "));
        return body(HttpStatus.UNPROCESSABLE_ENTITY, INVALID_METADATA,
                "Dữ liệu gửi lên không hợp lệ — " + chiTiet, null);
    }

    @ExceptionHandler({MissingServletRequestPartException.class,
            MissingServletRequestParameterException.class})
    public ResponseEntity<ApiResponse<Object>> handleMissingPart(Exception ex) {
        return body(HttpStatus.UNPROCESSABLE_ENTITY, INVALID_METADATA,
                "Thiếu trường bắt buộc: " + tenTruongThieu(ex), null);
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiResponse<Object>> handleDenied(AccessDeniedException ex) {
        return body(HttpStatus.FORBIDDEN, "FORBIDDEN",
                "Vai trò hiện tại không được thực hiện thao tác này", null);
    }

    @ExceptionHandler(AuthenticationException.class)
    public ResponseEntity<ApiResponse<Object>> handleUnauthenticated(AuthenticationException ex) {
        return body(HttpStatus.UNAUTHORIZED, "UNAUTHORIZED", "Chưa đăng nhập hoặc phiên đã hết hạn", null);
    }

    /** Lỗi chưa lường trước. Chi tiết chỉ vào log; phía gọi nhận thông điệp chung. */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Object>> handleUnexpected(Exception ex) {
        log.error("Lỗi chưa phân loại", ex);
        return body(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Lỗi nội bộ", null);
    }

    private static String tenTruongThieu(Exception ex) {
        if (ex instanceof MissingServletRequestPartException e) {
            return e.getRequestPartName();
        }
        return ((MissingServletRequestParameterException) ex).getParameterName();
    }

    private static ResponseEntity<ApiResponse<Object>> body(
            HttpStatus status, String code, String message, Object details) {
        return ResponseEntity.status(status)
                .body(ApiResponse.error(code, message, details, MDC.get(TraceIdFilter.MDC_KEY)));
    }
}
