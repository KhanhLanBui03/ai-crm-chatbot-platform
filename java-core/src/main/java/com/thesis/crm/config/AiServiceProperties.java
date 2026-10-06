package com.thesis.crm.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Đích gọi ai-service.
 *
 * @param baseUrl tên dịch vụ ({@code http://ai-service}), LoadBalancer đổi thành địa chỉ thật
 */
@ConfigurationProperties(prefix = "crm.ai-service")
public record AiServiceProperties(String baseUrl, Duration connectTimeout, Duration readTimeout) {
}
