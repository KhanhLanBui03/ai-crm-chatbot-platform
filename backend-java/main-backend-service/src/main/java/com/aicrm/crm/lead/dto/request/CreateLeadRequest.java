package com.aicrm.crm.lead.dto.request;

import lombok.Data;

@Data
public class CreateLeadRequest {
    private String name;
    private String email;
    private String phone;
    private String notes;
    private Long businessId;
    private Long conversationId;
}
