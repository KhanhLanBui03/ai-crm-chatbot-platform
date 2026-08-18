package com.aicrm.mcp.service;

import com.aicrm.mcp.client.ProductClient;
import com.aicrm.mcp.dto.response.ProductToolResponse;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Service
public class ProductToolService {

    private final ProductClient productClient;

    public ProductToolService(ProductClient productClient) {
        this.productClient = productClient;
    }

    public Flux<ProductToolResponse> searchProducts(String query, Long businessId) {
        return productClient.searchProducts(query, businessId);
    }

    public Mono<ProductToolResponse> getProduct(Long id, Long businessId) {
        return productClient.getProduct(id, businessId);
    }
}
