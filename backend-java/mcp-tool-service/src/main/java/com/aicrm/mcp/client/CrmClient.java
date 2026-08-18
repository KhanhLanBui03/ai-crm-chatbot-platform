package com.aicrm.mcp.client;

import com.aicrm.mcp.dto.request.CreateLeadToolRequest;
import com.aicrm.mcp.dto.response.LeadToolResponse;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

@Component
public class CrmClient {

    private final MainBackendClient backendClient;

    public CrmClient(MainBackendClient backendClient) {
        this.backendClient = backendClient;
    }

    public Mono<LeadToolResponse> createLead(CreateLeadToolRequest request) {
        return backendClient.getClient()
                .post()
                .uri("/api/leads")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(LeadToolResponse.class);
    }
}
