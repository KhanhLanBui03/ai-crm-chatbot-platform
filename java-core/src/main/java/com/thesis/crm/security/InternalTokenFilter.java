package com.thesis.crm.security;

import com.thesis.crm.config.InternalApiProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Xác thực lời gọi {@code /internal/**} của ai-service bằng {@code X-Internal-Token} (Q3, GD3) — thay
 * cho JWT người dùng, vì ai-service gọi từ worker (UC026) hay giữa một lượt xoá (UC041), không có
 * người đăng nhập nào đứng sau.
 *
 * <p>Khớp token thì đặt quyền {@code ROLE_INTERNAL_SERVICE}; không khớp thì để trống, chuỗi bảo mật
 * trả 401. So bằng {@link MessageDigest#isEqual} (thời gian hằng) — so chuỗi thường để lộ độ dài
 * phần khớp qua thời gian phản hồi. Chưa cấu hình token thì KHÔNG token nào khớp, kể cả chuỗi rỗng.
 *
 * <p>Cố ý không phải {@code @Component}: Spring Boot tự đăng ký mọi bean {@code Filter} vào chuỗi
 * servlet chung, tức là chạy cho cả {@code /api/**}. Lớp này chỉ được gắn vào chuỗi của
 * {@code /internal/**} ở {@link SecurityConfig}.
 *
 * <p>Tenant KHÔNG đặt ở đây: controller đọc {@code X-Tenant-Id} qua {@link InternalCaller} và service
 * gọi {@code TenantTransactionScope.apply()} trong transaction của nó (CLAUDE.md luật 3).
 */
public class InternalTokenFilter extends OncePerRequestFilter {

    public static final String ROLE = "INTERNAL_SERVICE";

    private final InternalApiProperties props;

    public InternalTokenFilter(InternalApiProperties props) {
        this.props = props;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (khop(request.getHeader(InternalApiProperties.HEADER))) {
            SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                    "ai-service", null, List.of(new SimpleGrantedAuthority("ROLE_" + ROLE))));
        }
        chain.doFilter(request, response);
    }

    private boolean khop(String guiLen) {
        if (!props.configured() || guiLen == null || guiLen.isEmpty()) {
            return false;
        }
        return MessageDigest.isEqual(guiLen.getBytes(StandardCharsets.UTF_8),
                props.apiToken().getBytes(StandardCharsets.UTF_8));
    }
}
