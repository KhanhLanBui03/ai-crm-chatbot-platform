package com.thesis.crm.eureka;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.netflix.eureka.server.EnableEurekaServer;

/**
 * Service registry. Gateway định tuyến qua {@code lb://} nhờ đăng ký ở đây (ADR-0004).
 *
 * <p>Service này chỉ có một lớp và không cần sub-package: toàn bộ hành vi đến từ
 * {@code @EnableEurekaServer} và {@code application.yml}.
 */
@SpringBootApplication
@EnableEurekaServer
public class EurekaServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(EurekaServerApplication.class, args);
    }
}
