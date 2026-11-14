package com.thesis.crm.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Bí mật dùng chung giữa java-core và ai-service cho các lời gọi nội bộ (Q3, GD3 — một token cả hai
 * chiều, header {@code X-Internal-Token}).
 *
 * @param apiToken rỗng/{@code null} = bề mặt nội bộ đóng hẳn, không có giá trị mặc định nào mở được nó
 */
@ConfigurationProperties(prefix = "crm.internal")
public record InternalApiProperties(String apiToken) {

    public static final String HEADER = "X-Internal-Token";

    public boolean configured() {
        return apiToken != null && !apiToken.isBlank();
    }
}
