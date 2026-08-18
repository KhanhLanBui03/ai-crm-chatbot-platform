package com.aicrm.mcp.client;

import com.aicrm.mcp.dto.response.ProductToolResponse;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Component
public class ProductClient {

    private final MainBackendClient backendClient;

    public ProductClient(MainBackendClient backendClient) {
        this.backendClient = backendClient;
    }

    public Flux<ProductToolResponse> searchProducts(String query, Long businessId) {
        return backendClient.getClient()
                .get()
                .uri(uriBuilder -> uriBuilder
                        .path("/api/products/search")
                        .queryParam("query", query)
                        .queryParam("businessId", businessId)
                        .build())
                .retrieve()
                .bodyToFlux(ProductToolResponse.class);
    }

    public Mono<ProductToolResponse> getProduct(Long id, Long businessId) {
        return backendClient.getClient()
                .get()
                .uri(uriBuilder -> uriBuilder
                        .path("/api/products/{id}")
                        .queryParam("businessId", businessId)
                        .build(id))
                .retrieve()
                .bodyToMono(ProductToolResponse.class);
    }
}
