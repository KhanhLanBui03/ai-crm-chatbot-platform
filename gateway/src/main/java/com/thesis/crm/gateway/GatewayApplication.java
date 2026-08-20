package com.thesis.crm.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Điểm vào duy nhất cho widget, dashboard và webhook kênh.
 *
 * <p>Trách nhiệm: xác thực JWT RS256, rate limit theo tenant, gắn {@code X-Trace-Id},
 * định tuyến qua {@code lb://} (Eureka phân giải — ADR-0004).
 *
 * <p>Gateway CHỈ xác thực token, không phát hành. java-core phát hành và công bố khoá công
 * khai ở {@code /.well-known/jwks.json}.
 */
@SpringBootApplication
public class GatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
