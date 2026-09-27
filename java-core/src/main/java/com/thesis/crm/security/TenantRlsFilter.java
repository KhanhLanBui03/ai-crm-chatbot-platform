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
        String tenantId = request.getHeader("X-Tenant-Id");

        String role = null;
        if (tenantId == null || tenantId.isBlank()) {
            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
                tenantId = jwt.getClaimAsString("tenant_id");
                role = jwt.getClaimAsString("role");
            }
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
