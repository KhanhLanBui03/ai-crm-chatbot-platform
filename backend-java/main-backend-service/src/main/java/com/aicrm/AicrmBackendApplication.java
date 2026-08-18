package com.aicrm;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
public class AicrmBackendApplication {
    public static void main(String[] args) {
        SpringApplication.run(AicrmBackendApplication.class, args);
    }
}
