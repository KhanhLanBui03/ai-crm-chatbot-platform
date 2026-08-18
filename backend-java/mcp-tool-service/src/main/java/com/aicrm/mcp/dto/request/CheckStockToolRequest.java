package com.aicrm.mcp.dto.request;

import lombok.Data;

@Data
public class CheckStockToolRequest {
    private Long productId;
    private Long businessId;
}
