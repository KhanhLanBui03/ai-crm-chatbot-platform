package com.thesis.crm.security;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import com.thesis.crm.platform.entity.Role;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.*;

@Component
public class JwtTokenProvider {

    private static final Logger log = LoggerFactory.getLogger(JwtTokenProvider.class);
    private static final Duration ACCESS_TOKEN_TTL = Duration.ofMinutes(15);
    private static final Duration REFRESH_TOKEN_TTL = Duration.ofDays(7);

    private final RsaKeyProperties rsaKeyProperties;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    public JwtTokenProvider(RsaKeyProperties rsaKeyProperties, StringRedisTemplate redisTemplate, ObjectMapper objectMapper) {
        this.rsaKeyProperties = rsaKeyProperties;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    public String generateAccessToken(UUID userId, UUID tenantId, String email, String scope, List<Role> roles) {
        try {
            Instant now = Instant.now();
            Instant expiry = now.plus(ACCESS_TOKEN_TTL);

            Set<String> allPermissions = new HashSet<>();
            String primaryRole = "AGENT";
            if ("PLATFORM".equalsIgnoreCase(scope)) {
                primaryRole = "PLATFORM_ADMIN";
                allPermissions.addAll(List.of(
                        "platform.tenants.read",
                        "platform.tenants.write",
                        "platform.plans.read",
                        "platform.plans.write",
                        "platform.ai-usage.read",
                        "platform.audit.read"
                ));
            }
            for (Role role : roles) {
                if ("TENANT_ADMIN".equalsIgnoreCase(role.getCode()) || "PLATFORM_ADMIN".equalsIgnoreCase(role.getCode())) {
                    primaryRole = role.getCode();
                }
                if (role.getPermissions() != null) {
                    try {
                        List<String> perms = objectMapper.readValue(role.getPermissions(), new TypeReference<List<String>>() {});
                        allPermissions.addAll(perms);
                    } catch (Exception ignored) {}
                }
            }

            JWTClaimsSet claimsSet = new JWTClaimsSet.Builder()
                    .subject(userId.toString())
                    .issuer("java-core")
                    .issueTime(Date.from(now))
                    .expirationTime(Date.from(expiry))
                    .jwtID(UUID.randomUUID().toString())
                    .claim("tenant_id", tenantId != null ? tenantId.toString() : null)
                    .claim("scope", scope)
                    .claim("email", email)
                    .claim("role", primaryRole)
                    .claim("permissions", new ArrayList<>(allPermissions))
                    .build();

            JWSHeader header = new JWSHeader.Builder(JWSAlgorithm.RS256)
                    .keyID(rsaKeyProperties.getKeyId())
                    .build();

            SignedJWT signedJWT = new SignedJWT(header, claimsSet);
            RSASSASigner signer = new RSASSASigner(rsaKeyProperties.getPrivateKey());
            signedJWT.sign(signer);

            return signedJWT.serialize();
        } catch (Exception e) {
            log.error("Lỗi khi sinh access token", e);
            throw new IllegalStateException("Không thể tạo access token", e);
        }
    }

    public String createRefreshToken(UUID userId, UUID tenantId) {
        String token = UUID.randomUUID().toString().replace("-", "") + UUID.randomUUID().toString().replace("-", "");
        String redisKey = "auth:refresh:" + token;
        Map<String, String> sessionData = new HashMap<>();
        sessionData.put("userId", userId.toString());
        if (tenantId != null) {
            sessionData.put("tenantId", tenantId.toString());
        }
        sessionData.put("createdAt", Instant.now().toString());

        try {
            redisTemplate.opsForValue().set(redisKey, objectMapper.writeValueAsString(sessionData), REFRESH_TOKEN_TTL);
        } catch (Exception e) {
            log.error("Lỗi lưu refresh token vào Redis", e);
            throw new IllegalStateException("Không thể lưu phiên đăng nhập", e);
        }
        return token;
    }
}
