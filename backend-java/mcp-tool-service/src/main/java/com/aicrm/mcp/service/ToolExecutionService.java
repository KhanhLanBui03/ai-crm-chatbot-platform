package com.aicrm.mcp.service;

import com.aicrm.mcp.dto.request.CreateLeadToolRequest;
import com.aicrm.mcp.dto.request.ToolCallRequest;
import com.aicrm.mcp.exception.ToolNotFoundException;
import com.aicrm.mcp.model.ToolResult;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class ToolExecutionService {

    private final ProductToolService productToolService;
    private final CrmToolService crmToolService;

    public ToolExecutionService(ProductToolService productToolService, CrmToolService crmToolService) {
        this.productToolService = productToolService;
        this.crmToolService = crmToolService;
    }

    public Mono<ToolResult> execute(ToolCallRequest request) {
        String name = request.getName();
        if ("SEARCH_PRODUCTS".equalsIgnoreCase(name)) {
            String query = (String) request.getArguments().get("query");
            Long businessId = Long.valueOf(request.getArguments().get("businessId").toString());
            return productToolService.searchProducts(query, businessId)
                    .collectList()
                    .map(list -> ToolResult.builder().isError(false).output(list.toString()).build());
        } else if ("CHECK_STOCK".equalsIgnoreCase(name)) {
            Long productId = Long.valueOf(request.getArguments().get("productId").toString());
            Long businessId = Long.valueOf(request.getArguments().get("businessId").toString());
            return productToolService.getProduct(productId, businessId)
                    .map(p -> ToolResult.builder().isError(false).output(String.valueOf(p.getStock())).build())
                    .defaultIfEmpty(ToolResult.builder().isError(true).output("Product not found").build());
        } else if ("CHECK_PRICE".equalsIgnoreCase(name)) {
            Long productId = Long.valueOf(request.getArguments().get("productId").toString());
            Long businessId = Long.valueOf(request.getArguments().get("businessId").toString());
            return productToolService.getProduct(productId, businessId)
                    .map(p -> ToolResult.builder().isError(false).output(p.getPrice().toPlainString()).build())
                    .defaultIfEmpty(ToolResult.builder().isError(true).output("Product not found").build());
        } else if ("CREATE_LEAD".equalsIgnoreCase(name)) {
            CreateLeadToolRequest leadReq = new CreateLeadToolRequest();
            leadReq.setName((String) request.getArguments().get("name"));
            leadReq.setEmail((String) request.getArguments().get("email"));
            leadReq.setPhone((String) request.getArguments().get("phone"));
            leadReq.setNotes((String) request.getArguments().get("notes"));
            leadReq.setBusinessId(Long.valueOf(request.getArguments().get("businessId").toString()));
            leadReq.setConversationId(Long.valueOf(request.getArguments().get("conversationId").toString()));
            return crmToolService.createLead(leadReq)
                    .map(res -> ToolResult.builder().isError(false).output("Created Lead: " + res.getId()).build())
                    .onErrorReturn(ToolResult.builder().isError(true).output("Error creating lead").build());
        } else {
            return Mono.error(new ToolNotFoundException("Tool " + name + " is not registered"));
        }
    }
}
