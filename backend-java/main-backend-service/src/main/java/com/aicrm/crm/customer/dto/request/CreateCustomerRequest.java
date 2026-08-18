package com.aicrm.crm.customer.dto.request;

import lombok.Data;

@Data
public class CreateCustomerRequest {
    private String name;
    private String email;
    private String phone;
    private Long businessId;
}
