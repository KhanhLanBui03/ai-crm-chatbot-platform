package com.thesis.crm.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Kho tệp S3 — ADR-0022. Cùng bộ biến môi trường {@code S3_*} với ai-service.
 *
 * @param endpoint  {@code host:cổng}, không có scheme (giống ai-service). Trống = AWS S3 theo region
 * @param secure    {@code true} thì nói HTTPS với {@code endpoint}
 * @param accessKey trống thì SDK tự lấy quyền qua chuỗi mặc định của AWS (IAM role/IRSA trên EKS)
 */
@ConfigurationProperties(prefix = "crm.storage.s3")
public record S3Properties(
        String endpoint,
        boolean secure,
        String region,
        String bucket,
        String accessKey,
        String secretKey) {
}
