package com.thesis.crm.gateway.filter;

import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.server.reactive.ServerHttpRequestDecorator;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Optional;
import java.util.UUID;

@Component
public class TokenRelayGatewayFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String existingTraceId = exchange.getRequest().getHeaders().getFirst("X-Trace-Id");
        String traceId = (existingTraceId != null && !existingTraceId.isBlank())
                ? existingTraceId
                : UUID.randomUUID().toString();

        return ReactiveSecurityContextHolder.getContext()
                .map(SecurityContext::getAuthentication)
                .map(auth -> {
                    if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
                        return Optional.of(jwt);
                    }
                    return Optional.<Jwt>empty();
                })
                .defaultIfEmpty(Optional.empty())
                .flatMap(optJwt -> {
                    Jwt jwt = optJwt.orElse(null);
                    ServerHttpRequestDecorator decorated = new ServerHttpRequestDecorator(exchange.getRequest()) {
                        @Override
                        public HttpHeaders getHeaders() {
                            HttpHeaders headers = new HttpHeaders();
                            headers.putAll(super.getHeaders());
                            // Header danh tính CHỈ do gateway gắn từ JWT đã xác thực. Client tự gửi
                            // X-Tenant-Id thì phải bỏ — trước đây request không có JWT (hoặc JWT
                            // không có tenant_id) mang nguyên header giả xuống java-core (CLAUDE.md luật 1).
                            headers.remove("X-Tenant-Id");
                            headers.remove("X-User-Id");
                            headers.remove("X-User-Scope");
                            headers.set("X-Trace-Id", traceId);
                            if (jwt != null) {
                                String tenantId = jwt.getClaimAsString("tenant_id");
                                String userId = jwt.getSubject();
                                String scope = jwt.getClaimAsString("scope");
                                if (tenantId != null) headers.set("X-Tenant-Id", tenantId);
                                if (userId != null) headers.set("X-User-Id", userId);
                                if (scope != null) headers.set("X-User-Scope", scope);
                            }
                            return headers;
                        }
                    };
                    return chain.filter(exchange.mutate().request(decorated).build());
                });
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 10;
    }
}
