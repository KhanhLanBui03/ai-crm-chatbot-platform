package com.thesis.crm.common.exception;

import com.thesis.crm.common.response.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(AppException.class)
    public ResponseEntity<ApiResponse<Void>> handleAppException(AppException ex, HttpServletRequest request) {
        String traceId = request.getHeader("X-Trace-Id");
        log.warn("AppException [{}]: {}", ex.getStatus(), ex.getMessage());
        return ResponseEntity.status(ex.getStatus())
                .body(ApiResponse.error(ex.getMessage(), traceId));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidationException(MethodArgumentNotValidException ex, HttpServletRequest request) {
        String traceId = request.getHeader("X-Trace-Id");
        String errorMessage = ex.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
                .body(ApiResponse.error(errorMessage, traceId));
    }

    /**
     * Tham số sai kiểu ({@code ?tagId=abc}, {@code /contacts/abc}), thiếu tham số bắt buộc, hoặc thân
     * JSON hỏng — lỗi của bên gọi, phải là 400 kèm câu dễ hiểu. Trước đây rơi xuống
     * {@link #handleGeneralException} thành 500 "lỗi hệ thống" (phát hiện khi rà soát UC016).
     */
    @ExceptionHandler({
            org.springframework.web.method.annotation.MethodArgumentTypeMismatchException.class,
            org.springframework.web.bind.MissingServletRequestParameterException.class,
            org.springframework.http.converter.HttpMessageNotReadableException.class
    })
    public ResponseEntity<ApiResponse<Void>> handleBadRequest(Exception ex, HttpServletRequest request) {
        String traceId = request.getHeader("X-Trace-Id");
        String message = ex instanceof org.springframework.web.method.annotation.MethodArgumentTypeMismatchException m
                ? "Tham số '" + m.getName() + "' không đúng định dạng."
                : ex instanceof org.springframework.web.bind.MissingServletRequestParameterException m
                        ? "Thiếu tham số bắt buộc '" + m.getParameterName() + "'."
                        : "Dữ liệu gửi lên không đúng định dạng JSON hoặc sai kiểu trường.";
        log.warn("Bad request: {}", ex.getMessage());
        return ResponseEntity.badRequest().body(ApiResponse.error(message, traceId));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneralException(Exception ex, HttpServletRequest request) {
        String traceId = request.getHeader("X-Trace-Id");
        log.error("Unhandled exception: ", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error("Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.", traceId));
    }
}
