package com.thesis.crm.gateway.security;

import org.springframework.http.HttpMethod;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.security.web.server.util.matcher.ServerWebExchangeMatchers;

@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    @Bean
    @Order(1)
    public SecurityWebFilterChain publicFilterChain(ServerHttpSecurity http) {
        return http
                .securityMatcher(ServerWebExchangeMatchers.pathMatchers(
                        "/api/v1/auth/**",
                        "/actuator/**",
                        "/ai/v1/widget/**",
                        // UC009/UC010 — khách vãng lai, java-core tự xác thực bằng token widget
                        "/api/v1/widget/**",
                        "/ws/**"
                ))
                .csrf(ServerHttpSecurity.CsrfSpec::disable)
                .authorizeExchange(exchanges -> exchanges.anyExchange().permitAll())
                .build();
    }

    @Bean
    @Order(2)
    public SecurityWebFilterChain authenticatedFilterChain(ServerHttpSecurity http) {
        return http
                .csrf(ServerHttpSecurity.CsrfSpec::disable)
                .authorizeExchange(exchanges -> exchanges
                        // Bảng giá trên trang chủ công khai (chỉ đọc). Có token thì vẫn kiểm và chuyển tiếp để
                        // java-core đánh dấu gói hiện tại của doanh nghiệp đăng nhập.
                        .pathMatchers(HttpMethod.GET, "/api/v1/plans").permitAll()
                        // UC040: cảnh báo an toàn chỉ java-core gọi trong mạng nội bộ — ai-service không kiểm vai
                        // trò, để lộ qua /ai/v1/** là nhân viên thường đọc được màn dành cho quản trị viên.
                        .pathMatchers("/ai/v1/safety-events", "/ai/v1/safety-events/**").denyAll()
                        // UC038: cụm chủ đề cũng chỉ java-core gọi — thống kê chủ đề là màn của quản trị viên
                        .pathMatchers("/ai/v1/topic-clusters", "/ai/v1/topic-clusters/**").denyAll()
                        // UC041: xoá dữ liệu cá nhân phía AI chỉ java-core gọi, SAU bước xác minh danh tính. Mở qua
                        // /ai/v1/** là nhân viên bất kỳ xoá vĩnh viễn được dữ liệu khách mà bỏ qua cổng xác minh.
                        // X-Internal-Token ở ai-service là lớp chặn thứ hai, không phải lớp duy nhất.
                        .pathMatchers("/ai/v1/ai/privacy/**").denyAll()
                        // UC026: tóm tắt đồng bộ cũng chỉ java-core gọi (nút "Tóm tắt lại" đi qua /api/v1/**)
                        .pathMatchers("/ai/v1/ai/summarize").denyAll()
                        .anyExchange().authenticated())
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> {}))
                .build();
    }
}
