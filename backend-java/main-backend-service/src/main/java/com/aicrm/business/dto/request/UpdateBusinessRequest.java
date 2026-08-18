package com.aicrm.business.dto.request;

import lombok.Data;

@Data
public class UpdateBusinessRequest {
    private String name;
    private String email;
    private String phone;
    private String address;
    private String website;
}
