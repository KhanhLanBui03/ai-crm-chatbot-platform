package com.thesis.crm;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Modular monolith — 4 bounded context: platform, engagement, sales, analytics.
 *
 * <p>Ranh giới context thể hiện bằng package. Luật đặt file: xem README.md.
 *
 * <p>{@code @EnableScheduling} cần cho tiến trình phát Outbox chạy mỗi 500ms (ADR-0003).
 */
@SpringBootApplication
@EnableScheduling
public class JavaCoreApplication {

    public static void main(String[] args) {
        SpringApplication.run(JavaCoreApplication.class, args);
    }
}
