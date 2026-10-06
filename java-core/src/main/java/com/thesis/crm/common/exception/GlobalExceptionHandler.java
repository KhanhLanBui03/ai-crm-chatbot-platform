package com.thesis.crm.common.exception;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.security.TraceIdFilter;
import jakarta.servlet.http.HttpServletRequest;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.util.StringUtils;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;

/**
 * Chỗ DUY NHẤT dịch ngoại lệ thành phản hồi HTTP. Mọi lỗi ra ngoài đều là {@code ApiResponse} có
 * {@code traceId}, để một dòng lỗi trên giao diện tra ngược được đúng dòng log.
 *
 * <p>Mỗi loại ngoại lệ chỉ được map MỘT lần — Spring từ chối khởi động nếu hai handler cùng khai
 * một loại ("Ambiguous @ExceptionHandler").
 *
 * <p>Hai lỗi của Spring Security phải khai tường minh ở đây: {@code @PreAuthorize} ném
 * {@link AccessDeniedException} từ BÊN TRONG controller, nên nó tới advice này trước khi tới
 * {@code ExceptionTranslationFilter}. Không khai thì nhánh {@code Exception} bên dưới nuốt mất và
 * người dùng thiếu quyền nhận 500 thay vì 403.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /** Mã validate chung. Đặc tả UC018 gọi lỗi siêu dữ liệu là INVALID_METADATA. */
    static final String INVALID_METADATA = "INVALID_METADATA";

    @ExceptionHandler(AppException.class)
    public ResponseEntity<ApiResponse<Object>> handleAppException(AppException ex, HttpServletRequest request) {
        log.warn("AppException [{}]: {}", ex.getStatus(), ex.getMessage());
        return ResponseEntity.status(ex.getStatus()).body(ApiResponse.error(ex.getMessage(), traceId(request)));
    }

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResponse<Object>> handleBusiness(BusinessException ex, HttpServletRequest request) {
        if (ex.getStatus().is5xxServerError()) {
            log.error("Lỗi nghiệp vụ {} — {}", ex.getCode(), ex.getMessage(), ex);
        }
        return body(ex.getStatus(), ex.getCode(), ex.getMessage(), ex.getDetails(), request);
    }

    /**
     * Tệp vượt {@code spring.servlet.multipart.max-file-size}. Nổ lúc servlet đọc multipart —
     * TRƯỚC khi Spring bind form, nên 413 luôn đứng trước 422 (hợp đồng UC018 mục 1.3).
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ApiResponse<Object>> handleTooLarge(MaxUploadSizeExceededException ex,
            HttpServletRequest request) {
        return body(HttpStatus.PAYLOAD_TOO_LARGE, "FILE_TOO_LARGE",
                "Tệp vượt quá 20 MB. Hãy tách nhỏ rồi tải lên từng phần.", null, request);
    }

    /**
     * Lỗi bind/validate — cả JSON ({@code @RequestBody}) lẫn form ({@code @ModelAttribute}). Một
     * handler cho cả hai vì {@code MethodArgumentNotValidException} là lớp con của
     * {@link BindException}, và từ Spring 6.1 lỗi validate {@code @ModelAttribute} cũng ném lớp con
     * đó: tách hai handler thì handler cụ thể hơn thắng và lỗi form UC018 mất mã nghiệp vụ.
     *
     * <p>Chỉ trả thông điệp của ràng buộc, không lặp lại giá trị người dùng đã gửi — mô tả tài liệu
     * hay ghi chú có thể dài và chứa dữ liệu cá nhân.
     */
    @ExceptionHandler(BindException.class)
    public ResponseEntity<ApiResponse<Object>> handleBind(BindException ex, HttpServletRequest request) {
        String message = ex.getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        return body(HttpStatus.UNPROCESSABLE_ENTITY, INVALID_METADATA,
                StringUtils.hasText(message) ? message : "Dữ liệu gửi lên không hợp lệ", null, request);
    }

    /** Thiếu phần tệp của form multipart — UC018 gọi đây là lỗi siêu dữ liệu (422). */
    @ExceptionHandler(MissingServletRequestPartException.class)
    public ResponseEntity<ApiResponse<Object>> handleMissingPart(MissingServletRequestPartException ex,
            HttpServletRequest request) {
        return body(HttpStatus.UNPROCESSABLE_ENTITY, INVALID_METADATA,
                "Thiếu trường bắt buộc: " + ex.getRequestPartName(), null, request);
    }

    /**
     * Tham số sai kiểu ({@code ?tagId=abc}, {@code /contacts/abc}), thiếu tham số bắt buộc, hoặc thân
     * JSON hỏng — lỗi của bên gọi, phải là 400 kèm câu dễ hiểu. Trước đây rơi xuống
     * {@link #handleGeneralException} thành 500 "lỗi hệ thống" (phát hiện khi rà soát UC016).
     */
    @ExceptionHandler({
            MethodArgumentTypeMismatchException.class,
            MissingServletRequestParameterException.class,
            HttpMessageNotReadableException.class
    })
    public ResponseEntity<ApiResponse<Object>> handleBadRequest(Exception ex, HttpServletRequest request) {
        String message = ex instanceof MethodArgumentTypeMismatchException m
                ? "Tham số '" + m.getName() + "' không đúng định dạng."
                : ex instanceof MissingServletRequestParameterException m
                        ? "Thiếu tham số bắt buộc '" + m.getParameterName() + "'."
                        : "Dữ liệu gửi lên không đúng định dạng JSON hoặc sai kiểu trường.";
        log.warn("Bad request: {}", ex.getMessage());
        return ResponseEntity.badRequest().body(ApiResponse.error(message, traceId(request)));
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiResponse<Object>> handleDenied(AccessDeniedException ex, HttpServletRequest request) {
        return body(HttpStatus.FORBIDDEN, "FORBIDDEN",
                "Vai trò hiện tại không được thực hiện thao tác này", null, request);
    }

    @ExceptionHandler(AuthenticationException.class)
    public ResponseEntity<ApiResponse<Object>> handleUnauthenticated(AuthenticationException ex,
            HttpServletRequest request) {
        return body(HttpStatus.UNAUTHORIZED, "UNAUTHORIZED", "Chưa đăng nhập hoặc phiên đã hết hạn", null,
                request);
    }

    /** Lỗi chưa lường trước. Chi tiết chỉ vào log; phía gọi nhận thông điệp chung. */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Object>> handleGeneralException(Exception ex, HttpServletRequest request) {
        log.error("Unhandled exception: ", ex);
        return body(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR",
                "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.", null, request);
    }

    /**
     * traceId do {@link TraceIdFilter} đặt vào MDC — đã kiểm định dạng, và chính là giá trị nằm
     * trong log. Header thô chỉ là phương án dự phòng khi request không đi qua filter đó.
     */
    private static String traceId(HttpServletRequest request) {
        String mdc = MDC.get(TraceIdFilter.MDC_KEY);
        return mdc != null ? mdc : request.getHeader("X-Trace-Id");
    }

    private static ResponseEntity<ApiResponse<Object>> body(
            HttpStatus status, String code, String message, Object details, HttpServletRequest request) {
        return ResponseEntity.status(status)
                .body(ApiResponse.error(code, message, details, traceId(request)));
    }
}
