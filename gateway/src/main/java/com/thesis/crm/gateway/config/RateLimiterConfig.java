package com.thesis.crm.gateway.config;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.oauth2.jwt.Jwt;
import reactor.core.publisher.Mono;

@Configuration
public class RateLimiterConfig {

    @Bean
    @Primary
    public KeyResolver userOrIpKeyResolver() {
        return exchange -> ReactiveSecurityContextHolder.getContext()
                .map(SecurityContext::getAuthentication)
                .flatMap(auth -> {
                    if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
                        String tenantId = jwt.getClaimAsString("tenant_id");
                        if (tenantId != null && !tenantId.isBlank()) {
                            return Mono.just("tenant:" + tenantId);
                        }
                        return Mono.just("user:" + jwt.getSubject());
                    }
                    return Mono.empty();
                })
                .switchIfEmpty(Mono.defer(() -> {
                    var remoteAddress = exchange.getRequest().getRemoteAddress();
                    if (remoteAddress != null && remoteAddress.getAddress() != null) {
                        return Mono.just("ip:" + remoteAddress.getAddress().getHostAddress());
                    }
                    return Mono.just("ip:anonymous");
                }));
    }
}
