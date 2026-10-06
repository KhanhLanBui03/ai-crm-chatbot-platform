package com.thesis.crm.security;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.util.StringUtils;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final RsaKeyProperties rsaKeyProperties;
    private final TenantRlsFilter tenantRlsFilter;

    public SecurityConfig(RsaKeyProperties rsaKeyProperties, TenantRlsFilter tenantRlsFilter) {
        this.rsaKeyProperties = rsaKeyProperties;
        this.tenantRlsFilter = tenantRlsFilter;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public JwtDecoder jwtDecoder() {
        return NimbusJwtDecoder.withPublicKey(rsaKeyProperties.getPublicKey()).build();
    }

    @Bean
    @org.springframework.core.annotation.Order(1)
    public SecurityFilterChain publicSecurityFilterChain(HttpSecurity http) throws Exception {
        http
                .securityMatcher(
                        "/api/v1/auth/**",
                        "/.well-known/jwks.json",
                        "/actuator/**",
                        "/ws/**"
                )
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }

    /**
     * Phân quyền UC018 đặt ở chuỗi filter, không ở {@code @PreAuthorize}: kiểm ở đây thì người
     * thiếu quyền nhận 403 TRƯỚC khi servlet đọc tệp 20 MiB và trước khi form được validate. Để ở
     * controller thì quyền chỉ được kiểm sau khi bind xong — người thiếu quyền gửi tiêu đề sai nhận
     * 422, tức là được biết luật validate của một thao tác mình không được làm.
     *
     * <p>{@code loi} viết 401/403 thành {@code ApiResponse} có {@code traceId}, cùng hình dạng với
     * mọi lỗi khác thay vì thân rỗng.
     */
    @Bean
    @org.springframework.core.annotation.Order(2)
    public SecurityFilterChain authenticatedSecurityFilterChain(HttpSecurity http, JsonSecurityErrorHandler loi)
            throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // UC018 tiền điều kiện: "có vai trò quản trị của doanh nghiệp".
                        .requestMatchers(HttpMethod.POST, "/api/v1/documents").hasRole("TENANT_ADMIN")
                        .anyRequest().authenticated())
                .oauth2ResourceServer(oauth2 -> oauth2
                        .jwt(jwt -> jwt.decoder(jwtDecoder()).jwtAuthenticationConverter(jwtAuthenticationConverter()))
                        .authenticationEntryPoint(loi)
                        .accessDeniedHandler(loi))
                .exceptionHandling(e -> e.authenticationEntryPoint(loi).accessDeniedHandler(loi))
                .addFilterAfter(tenantRlsFilter, org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter.class);

        return http.build();
    }

    /**
     * Claim {@code role} → quyền {@code ROLE_<role>} để dùng được {@code hasRole(...)}, GỘP với
     * {@code SCOPE_*} mặc định lấy từ claim {@code scope} — không thay thế, để chỗ nào kiểm theo scope
     * vẫn chạy như cũ.
     */
    private static JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtGrantedAuthoritiesConverter scope = new JwtGrantedAuthoritiesConverter();
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            Collection<GrantedAuthority> quyen = new ArrayList<>(scope.convert(jwt));
            String vaiTro = jwt.getClaimAsString("role");
            if (StringUtils.hasText(vaiTro)) {
                quyen.add(new SimpleGrantedAuthority("ROLE_" + vaiTro));
            }
            return List.copyOf(quyen);
        });
        return converter;
    }
}
