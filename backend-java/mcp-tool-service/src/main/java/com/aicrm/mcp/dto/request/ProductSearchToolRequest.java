package com.aicrm.mcp.dto.request;

import lombok.Data;

@Data
public class ProductSearchToolRequest {
    private String query;
    private Long businessId;
}
