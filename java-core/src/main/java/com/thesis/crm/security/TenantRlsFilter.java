package com.thesis.crm.security;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
public class TenantRlsFilter extends OncePerRequestFilter {

    private final TenantContextExecutor tenantContextExecutor;

    public TenantRlsFilter(TenantContextExecutor tenantContextExecutor) {
        this.tenantContextExecutor = tenantContextExecutor;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        // JWT đã xác thực LUÔN thắng header: header là thứ client tự gửi được, JWT thì không giả được.
        // Trước đây header được đọc trước — X-Tenant-Id giả đi kèm JWT thật vẫn đổi được tenant của
        // phiên (CLAUDE.md luật 1). Header chỉ còn dùng khi không có JWT (gọi nội bộ giữa service).
        String tenantId = null;
        String role = null;
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
            tenantId = jwt.getClaimAsString("tenant_id");
            role = jwt.getClaimAsString("role");
        } else {
            tenantId = request.getHeader("X-Tenant-Id");
        }

        boolean isPlatformAdmin = "PLATFORM_ADMIN".equalsIgnoreCase(role);

        if (isPlatformAdmin) {
            try {
                tenantContextExecutor.setPlatformAdminContext();
            } catch (Exception ignored) {
            }
        } else if (tenantId != null && !tenantId.isBlank()) {
            try {
                java.util.UUID parsed = java.util.UUID.fromString(tenantId.trim());
                tenantContextExecutor.setTenantContext(parsed);
                request.setAttribute("app.tenant_id", tenantId);
            } catch (Exception ignored) {
            }
        }

        try {
            filterChain.doFilter(request, response);
        } finally {
            if (isPlatformAdmin) {
                tenantContextExecutor.clearPlatformAdminContext();
            } else if (tenantId != null && !tenantId.isBlank()) {
                tenantContextExecutor.clearTenantContext();
            }
        }
    }
}
