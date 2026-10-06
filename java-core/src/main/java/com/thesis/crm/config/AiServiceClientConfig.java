package com.thesis.crm.config;

import java.net.http.HttpClient;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cloud.client.loadbalancer.LoadBalancerClient;
import org.springframework.cloud.client.loadbalancer.LoadBalancerInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * {@code RestClient} riêng cho ai-service — chỉ {@code client/AiServiceClient} dùng (ADR-0002).
 *
 * <p>Gắn {@link LoadBalancerInterceptor} vào ĐÚNG client này thay vì khai một
 * {@code @LoadBalanced RestClient.Builder} dùng chung: bean builder đó sẽ thay builder mặc định
 * của Boot cho cả ứng dụng, và mọi lời gọi HTTP khác (kể cả của thư viện) bị ép đi qua
 * LoadBalancer với host là tên dịch vụ.
 *
 * <p>HTTP/1.1 tường minh: client của JDK mặc định thử nâng cấp lên HTTP/2 trên kết nối thường,
 * mà uvicorn của ai-service không nói HTTP/2.
 */
@Configuration
@EnableConfigurationProperties({AiServiceProperties.class, KbProperties.class})
public class AiServiceClientConfig {

    @Bean
    @Qualifier("aiServiceRestClient")
    public RestClient aiServiceRestClient(RestClient.Builder builder, LoadBalancerClient loadBalancer,
            AiServiceProperties p) {
        HttpClient http = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(p.connectTimeout())
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(http);
        factory.setReadTimeout(p.readTimeout());
        return builder
                .baseUrl(p.baseUrl())
                .requestFactory(factory)
                .requestInterceptor(new LoadBalancerInterceptor(loadBalancer))
                .build();
    }
}
