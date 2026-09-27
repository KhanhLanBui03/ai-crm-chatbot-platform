package com.thesis.crm.security;

import java.util.Optional;
import java.util.UUID;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;

/**
 * Tenant và người dùng của request hiện tại — đọc từ JWT đã xác minh, KHÔNG từ nơi nào khác.
 *
 * <p>Tên claim theo {@code securitySchemes.tenantJwt} của {@code docs/openapi/dashboard-api.yaml}:
 * {@code sub} (userId), {@code tenantId}, {@code roleCode}.
 *
 * <p>Không có setter, không có ThreadLocal riêng: nguồn duy nhất là {@code SecurityContextHolder},
 * nơi chỉ bộ lọc JWT của Spring Security ghi vào. Một lớp giữ tenant có setter là một lời mời
 * đặt tenant từ body request.
 */
public final class TenantContext {

    public static final String CLAIM_TENANT = "tenantId";
    public static final String CLAIM_ROLE = "roleCode";

    private TenantContext() {
    }

    /** Tenant của request. Rỗng khi không có JWT — job nền, luồng khởi động. */
    public static Optional<UUID> currentTenantId() {
        return currentJwt().map(jwt -> jwt.getToken().getClaimAsString(CLAIM_TENANT))
                .flatMap(TenantContext::parseCanonicalUuid);
    }

    /**
     * Tenant của request, ném nếu thiếu. Bộ kiểm JWT ({@link SecurityConfig}) đã từ chối mọi
     * token không có {@code tenantId} hợp lệ, nên tới được đây mà thiếu là lỗi lập trình — gọi
     * ngoài request có xác thực. Fail-closed: không đoán, không mặc định.
     */
    public static UUID requireTenantId() {
        return currentTenantId().orElseThrow(() -> new IllegalStateException(
                "Không có tenant trong ngữ cảnh bảo mật — thao tác nghiệp vụ phải chạy trong request đã xác thực"));
    }

    /** {@code sub} của JWT nếu nó là UUID. */
    public static Optional<UUID> currentUserId() {
        return currentJwt().map(jwt -> jwt.getToken().getSubject())
                .flatMap(TenantContext::parseCanonicalUuid);
    }

    /**
     * Chỉ nhận UUID ở dạng chuẩn 36 ký tự. {@code UUID.fromString} dễ dãi — nó nhận cả
     * {@code "1-2-3-4-5"} — trong khi ai-service so phân đoạn đầu của key S3 với tenant bằng
     * đúng từng ký tự. Hai dạng viết khác nhau của cùng một tenant thì hai bên hiểu khác nhau.
     */
    static Optional<UUID> parseCanonicalUuid(Object value) {
        if (!(value instanceof String s)) {
            return Optional.empty();
        }
        try {
            UUID uuid = UUID.fromString(s);
            return uuid.toString().equalsIgnoreCase(s) ? Optional.of(uuid) : Optional.empty();
        } catch (IllegalArgumentException e) {
            return Optional.empty();
        }
    }

    private static Optional<JwtAuthenticationToken> currentJwt() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        return auth instanceof JwtAuthenticationToken jwt ? Optional.of(jwt) : Optional.empty();
    }
}
