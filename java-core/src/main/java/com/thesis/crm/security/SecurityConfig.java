package com.thesis.crm.security;

import com.thesis.crm.security.RsaKeyProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.web.SecurityFilterChain;

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

    @Bean
    @org.springframework.core.annotation.Order(2)
    public SecurityFilterChain authenticatedSecurityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> jwt.decoder(jwtDecoder())))
                .addFilterAfter(tenantRlsFilter, org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter.class);

        return http.build();
    }
}
