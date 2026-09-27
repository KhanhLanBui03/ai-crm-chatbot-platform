package com.thesis.crm.config;

import java.net.URI;
import java.time.Duration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.checksums.RequestChecksumCalculation;
import software.amazon.awssdk.core.checksums.ResponseChecksumValidation;
import software.amazon.awssdk.http.apache.ApacheHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3ClientBuilder;

/**
 * Client S3 cho kho tệp tài liệu — RustFS ở dev, AWS S3 trên cloud (ADR-0019).
 *
 * <p>Ba chỗ cấu hình khác mặc định của SDK, mỗi chỗ vì một lý do:
 *
 * <ol>
 *   <li><b>Path-style khi có endpoint riêng.</b> Mặc định SDK đặt bucket vào tên miền
 *       ({@code kb-tai-lieu.rustfs:9000}) — tên đó không phân giải được trong mạng Docker.
 *   <li><b>Checksum chỉ khi bắt buộc.</b> Từ 2.30 SDK tự thêm CRC32 và gửi thân dạng
 *       {@code aws-chunked} cho MỌI PutObject; không phải máy chủ S3 tương thích nào cũng hiểu.
 *       AWS S3 vẫn kiểm toàn vẹn bằng Content-MD5/ETag như trước.
 *   <li><b>Ghim thời gian chờ.</b> Kho chết thì lỗi nổi lên nhanh thành 503, không treo request —
 *       cùng con số với ai-service ({@code object_storage.tao_client}: connect 3 s, read 30 s).
 * </ol>
 */
@Configuration
@EnableConfigurationProperties(S3Properties.class)
public class ObjectStorageConfig {

    @Bean(destroyMethod = "close")
    public S3Client s3Client(S3Properties p) {
        S3ClientBuilder builder = S3Client.builder()
                .region(Region.of(p.region()))
                .httpClientBuilder(ApacheHttpClient.builder()
                        .connectionTimeout(Duration.ofSeconds(3))
                        .socketTimeout(Duration.ofSeconds(30)))
                .requestChecksumCalculation(RequestChecksumCalculation.WHEN_REQUIRED)
                .responseChecksumValidation(ResponseChecksumValidation.WHEN_REQUIRED);

        if (StringUtils.hasText(p.endpoint())) {
            builder.endpointOverride(URI.create((p.secure() ? "https://" : "http://") + p.endpoint()))
                    .forcePathStyle(true);
        }
        if (StringUtils.hasText(p.accessKey())) {
            builder.credentialsProvider(StaticCredentialsProvider.create(
                    AwsBasicCredentials.create(p.accessKey(), p.secretKey())));
        } else {
            builder.credentialsProvider(DefaultCredentialsProvider.create());
        }
        return builder.build();
    }
}
