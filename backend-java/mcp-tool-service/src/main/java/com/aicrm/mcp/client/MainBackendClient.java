package com.aicrm.mcp.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

@Component
public class MainBackendClient {

    private final WebClient webClient;

    public MainBackendClient(WebClient.Builder webClientBuilder, @Value("${main-backend.url}") String backendUrl) {
        this.webClient = webClientBuilder.baseUrl(backendUrl).build();
    }

    public WebClient getClient() {
        return this.webClient;
    }
}
