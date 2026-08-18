package com.aicrm.mcp.dto.request;

import lombok.Data;

@Data
public class CreateLeadToolRequest {
    private String name;
    private String email;
    private String phone;
    private String notes;
    private Long businessId;
    private Long conversationId;
}
