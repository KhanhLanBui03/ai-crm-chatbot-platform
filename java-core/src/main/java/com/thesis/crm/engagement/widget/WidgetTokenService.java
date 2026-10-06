package com.thesis.crm.engagement.widget;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.MACSigner;
import com.nimbusds.jose.crypto.MACVerifier;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import com.thesis.crm.common.exception.AppException;
import java.nio.charset.StandardCharsets;
import java.text.ParseException;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

/**
 * Token phiên của khách vãng lai trên widget (UC009 bước 11, 11.3–11.4).
 *
 * <p><b>Ký bằng khoá HMAC RIÊNG</b>, không dùng cặp khoá RSA của JWT dashboard: gateway và java-core
 * chấp nhận mọi JWT RS256 hợp lệ ở {@code /api/v1/**}, nên nếu token widget ký bằng khoá đó thì một
 * khách vãng lai cầm token của mình gọi được API dành cho nhân viên. Thêm {@code aud} để token này
 * không bao giờ bị hiểu nhầm sang ngữ cảnh khác.
 *
 * <p>Tenant, kênh và mã khách nằm TRONG chữ ký — trình duyệt không sửa được để đọc hội thoại của
 * người khác hay đổi doanh nghiệp (CLAUDE.md luật 1).
 */
@Component
public class WidgetTokenService {

    static final String AUDIENCE = "crm-widget";
    private static final Duration TTL = Duration.ofDays(30);

    /** Phiên đã xác thực chữ ký. */
    public record WidgetSession(UUID tenantId, UUID channelId, UUID visitorId) {}

    private final byte[] secret;

    public WidgetTokenService(@Value("${widget.token-secret}") String secret) {
        byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
        if (bytes.length < 32) {
            throw new IllegalStateException("widget.token-secret phải dài tối thiểu 32 byte (HS256).");
        }
        this.secret = bytes;
    }

    public String issue(WidgetSession s) {
        Instant now = Instant.now();
        JWTClaimsSet claims = new JWTClaimsSet.Builder()
                .subject(s.visitorId().toString())
                .audience(AUDIENCE)
                .claim("tid", s.tenantId().toString())
                .claim("chid", s.channelId().toString())
                .issueTime(Date.from(now))
                .expirationTime(Date.from(now.plus(TTL)))
                .build();
        try {
            SignedJWT jwt = new SignedJWT(new JWSHeader(JWSAlgorithm.HS256), claims);
            jwt.sign(new MACSigner(secret));
            return jwt.serialize();
        } catch (JOSEException e) {
            throw new IllegalStateException("Không ký được token widget", e);
        }
    }

    /** Rỗng khi token thiếu, sai chữ ký, hết hạn hoặc không dành cho widget. */
    public Optional<WidgetSession> parse(String token) {
        if (token == null || token.isBlank()) {
            return Optional.empty();
        }
        try {
            SignedJWT jwt = SignedJWT.parse(token.trim());
            if (!JWSAlgorithm.HS256.equals(jwt.getHeader().getAlgorithm())
                    || !jwt.verify(new MACVerifier(secret))) {
                return Optional.empty();
            }
            JWTClaimsSet c = jwt.getJWTClaimsSet();
            List<String> aud = c.getAudience();
            if (aud == null || !aud.contains(AUDIENCE)
                    || c.getExpirationTime() == null || c.getExpirationTime().before(new Date())) {
                return Optional.empty();
            }
            return Optional.of(new WidgetSession(
                    UUID.fromString(c.getStringClaim("tid")),
                    UUID.fromString(c.getStringClaim("chid")),
                    UUID.fromString(c.getSubject())));
        } catch (ParseException | JOSEException | IllegalArgumentException | NullPointerException e) {
            return Optional.empty();
        }
    }

    public WidgetSession require(String token) {
        return parse(token).orElseThrow(() -> new AppException(
                "Phiên trò chuyện không hợp lệ hoặc đã hết hạn — vui lòng tải lại trang.",
                HttpStatus.UNAUTHORIZED));
    }
}
