package com.thesis.crm.security;

import java.io.IOException;
import java.io.InputStream;
import java.security.interfaces.RSAPublicKey;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ResourceLoader;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.converter.RsaKeyConverters;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.util.StringUtils;

/**
 * java-core là resource server JWT RS256. Gateway đã xác minh token một lần; java-core xác minh
 * LẠI — gọi thẳng vào cổng 8081 (trong mạng Docker, qua port-forward) không đi qua gateway.
 *
 * <p>Phân quyền theo URL, không theo {@code @PreAuthorize}: kiểm ở chuỗi filter thì người thiếu
 * quyền nhận 403 TRƯỚC khi servlet đọc tệp 20 MiB và trước khi form được validate. Để ở
 * {@code @PreAuthorize} thì quyền chỉ được kiểm sau khi bind xong — người thiếu quyền gửi tiêu
 * đề sai nhận 422, tức là được biết luật validate của một thao tác mình không được làm.
 *
 * <p>Chưa có luồng phát hành token (UC002 đăng nhập). Khoá công khai đọc từ
 * {@code crm.security.jwt.public-key-location}; khi java-core phát hành token, cặp khoá của nó
 * thay vào đúng chỗ này.
 */
@Configuration
public class SecurityConfig {

    private static final Logger log = LoggerFactory.getLogger(SecurityConfig.class);

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, JsonSecurityErrorHandler loi) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)          // không cookie phiên → không có CSRF
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(a -> a
                        .requestMatchers("/actuator/health", "/actuator/health/**",
                                "/actuator/info", "/actuator/prometheus").permitAll()
                        // UC018 tiền điều kiện: "có vai trò quản trị của doanh nghiệp".
                        .requestMatchers(HttpMethod.POST, "/api/v1/documents").hasRole("TENANT_ADMIN")
                        .anyRequest().authenticated())
                .oauth2ResourceServer(o -> o
                        .jwt(j -> j.jwtAuthenticationConverter(jwtAuthenticationConverter()))
                        .authenticationEntryPoint(loi)
                        .accessDeniedHandler(loi))
                .exceptionHandling(e -> e.authenticationEntryPoint(loi).accessDeniedHandler(loi));
        return http.build();
    }

    /**
     * Giải mã và kiểm token. Ngoài chữ ký và hạn dùng, token PHẢI có {@code tenantId} là UUID dạng
     * chuẩn — thiếu thì 401 ngay ở cửa, không để lọt tới chỗ nào cần tenant rồi mới vỡ.
     *
     * <p>Chưa cấu hình khoá thì từ chối MỌI token (fail-closed) thay vì làm ứng dụng không khởi
     * động được: health check và Flyway vẫn chạy, chỉ API nghiệp vụ trả 401.
     */
    @Bean
    JwtDecoder jwtDecoder(@Value("${crm.security.jwt.public-key-location:}") String viTriKhoa,
            ResourceLoader resourceLoader) throws IOException {
        if (!StringUtils.hasText(viTriKhoa)) {
            log.warn("Chưa cấu hình crm.security.jwt.public-key-location — mọi request cần xác thực sẽ bị 401. "
                    + "Dev: chạy scripts/dev-jwt.sh");
            return token -> {
                throw new BadJwtException("Chưa cấu hình khoá công khai JWT");
            };
        }
        RSAPublicKey khoa;
        try (InputStream in = resourceLoader.getResource(viTriKhoa).getInputStream()) {
            khoa = RsaKeyConverters.x509().convert(in);
        }
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withPublicKey(khoa)
                .signatureAlgorithm(SignatureAlgorithm.RS256)
                .build();
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
                JwtValidators.createDefault(),
                new JwtClaimValidator<Object>(TenantContext.CLAIM_TENANT,
                        v -> TenantContext.parseCanonicalUuid(v).isPresent())));
        return decoder;
    }

    /** {@code roleCode} → quyền {@code ROLE_<roleCode>}, để dùng được {@code hasRole(...)}. */
    private static JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            String vaiTro = jwt.getClaimAsString(TenantContext.CLAIM_ROLE);
            List<GrantedAuthority> quyen = StringUtils.hasText(vaiTro)
                    ? List.of(new SimpleGrantedAuthority("ROLE_" + vaiTro))
                    : List.of();
            return quyen;
        });
        return converter;
    }
}
