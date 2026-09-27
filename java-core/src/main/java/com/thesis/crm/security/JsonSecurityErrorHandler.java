package com.thesis.crm.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.response.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

/**
 * Viết 401/403 của tầng filter thành {@code ApiResponse} — cùng hình dạng với mọi lỗi khác.
 *
 * <p>Lỗi xác thực xảy ra trong chuỗi filter, TRƯỚC {@code DispatcherServlet}, nên
 * {@code GlobalExceptionHandler} không bắt được. Để mặc định thì Spring trả thân rỗng, và giao
 * diện phải xử lý hai hình dạng lỗi khác nhau.
 */
@Component
public class JsonSecurityErrorHandler implements AuthenticationEntryPoint, AccessDeniedHandler {

    private final ObjectMapper objectMapper;

    public JsonSecurityErrorHandler(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response,
            AuthenticationException ex) throws IOException {
        // RFC 6750: 401 của bearer token phải kèm WWW-Authenticate.
        response.setHeader(HttpHeaders.WWW_AUTHENTICATE, "Bearer");
        viet(response, HttpStatus.UNAUTHORIZED, "UNAUTHORIZED", "Chưa đăng nhập hoặc phiên đã hết hạn");
    }

    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response,
            AccessDeniedException ex) throws IOException {
        viet(response, HttpStatus.FORBIDDEN, "FORBIDDEN", "Vai trò hiện tại không được thực hiện thao tác này");
    }

    private void viet(HttpServletResponse response, HttpStatus status, String code, String message)
            throws IOException {
        response.setStatus(status.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        objectMapper.writeValue(response.getOutputStream(),
                ApiResponse.error(code, message, null, MDC.get(TraceIdFilter.MDC_KEY)));
    }
}
