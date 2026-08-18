package com.aicrm.mcp.dto.request;

import lombok.Data;

@Data
public class CheckPriceToolRequest {
    private Long productId;
    private Long businessId;
}
