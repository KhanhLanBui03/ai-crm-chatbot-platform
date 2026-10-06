package com.thesis.crm.engagement.widget;

import com.thesis.crm.common.exception.AppException;
import java.time.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

/**
 * Chống spam trên API công khai của widget: ai cũng gọi được, và mỗi tin có thể tốn một lượt LLM.
 * Gateway đã giới hạn theo IP cho mọi request ẩn danh; lớp này giới hạn sát nghiệp vụ hơn —
 * 10 tin/phút mỗi phiên khách, 20 lần mở phiên/phút mỗi IP.
 *
 * <p>Cửa sổ cố định 60 giây bằng {@code INCR} + {@code EXPIRE} trên Redis. Redis lỗi thì cho qua
 * (fail-open) và ghi cảnh báo: mất chống spam vài phút còn hơn khách không chat được.
 */
@Component
public class WidgetRateLimiter {

    private static final Logger log = LoggerFactory.getLogger(WidgetRateLimiter.class);
    static final int MESSAGES_PER_MINUTE = 10;
    static final int SESSIONS_PER_MINUTE = 20;

    private final StringRedisTemplate redis;

    public WidgetRateLimiter(StringRedisTemplate redis) {
        this.redis = redis;
    }

    public void checkMessage(String visitorId) {
        check("widget:msg:" + visitorId, MESSAGES_PER_MINUTE);
    }

    public void checkSession(String clientIp) {
        check("widget:session:" + clientIp, SESSIONS_PER_MINUTE);
    }

    private void check(String key, int limit) {
        Long count;
        try {
            count = redis.opsForValue().increment(key);
            if (count != null && count == 1L) {
                redis.expire(key, Duration.ofSeconds(60));
            }
        } catch (RuntimeException e) {
            log.warn("Redis lỗi, tạm bỏ qua chống spam widget: {}", e.getMessage());
            return;
        }
        if (count != null && count > limit) {
            throw new AppException("Bạn gửi quá nhanh, vui lòng chờ một chút rồi thử lại.",
                    HttpStatus.TOO_MANY_REQUESTS);
        }
    }
}
