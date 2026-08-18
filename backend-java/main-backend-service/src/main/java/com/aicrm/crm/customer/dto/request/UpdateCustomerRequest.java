package com.aicrm.crm.customer.dto.request;

import lombok.Data;

@Data
public class UpdateCustomerRequest {
    private String name;
    private String email;
    private String phone;
    private String status;
}
