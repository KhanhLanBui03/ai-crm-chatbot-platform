package com.aicrm.mcp.service;

import com.aicrm.mcp.client.CrmClient;
import com.aicrm.mcp.dto.request.CreateLeadToolRequest;
import com.aicrm.mcp.dto.response.LeadToolResponse;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class CrmToolService {

    private final CrmClient crmClient;

    public CrmToolService(CrmClient crmClient) {
        this.crmClient = crmClient;
    }

    public Mono<LeadToolResponse> createLead(CreateLeadToolRequest request) {
        return crmClient.createLead(request);
    }
}
