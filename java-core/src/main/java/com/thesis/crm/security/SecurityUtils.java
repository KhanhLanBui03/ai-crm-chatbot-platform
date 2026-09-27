package com.thesis.crm.security;

import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;

import java.util.UUID;

/**
 * Tiện ích truy xuất thông tin từ JWT Security Context hiện tại.
 */
public final class SecurityUtils {

    private SecurityUtils() {}

    public static UUID getCurrentTenantId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
            String tenantIdStr = jwt.getClaimAsString("tenant_id");
            if (tenantIdStr != null && !tenantIdStr.isBlank()) {
                try {
                    return UUID.fromString(tenantIdStr.trim());
                } catch (IllegalArgumentException ignored) {}
            }
        }
        return null;
    }

    public static UUID getCurrentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
            String subject = jwt.getSubject();
            if (subject != null && !subject.isBlank()) {
                try {
                    return UUID.fromString(subject.trim());
                } catch (IllegalArgumentException ignored) {}
            }
        }
        return null;
    }

    public static String getCurrentUserEmail() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
            return jwt.getClaimAsString("email");
        }
        return null;
    }

    public static String getCurrentRole() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
            return jwt.getClaimAsString("role");
        }
        return null;
    }

    public static boolean isTenantAdmin() {
        String role = getCurrentRole();
        return "TENANT_ADMIN".equalsIgnoreCase(role) || "PLATFORM_ADMIN".equalsIgnoreCase(role);
    }
}
