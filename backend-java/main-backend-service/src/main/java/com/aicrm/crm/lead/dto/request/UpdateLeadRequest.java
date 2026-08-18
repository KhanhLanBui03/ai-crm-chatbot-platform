package com.aicrm.crm.lead.dto.request;

import lombok.Data;

@Data
public class UpdateLeadRequest {
    private String name;
    private String email;
    private String phone;
    private String status;
    private String notes;
}
