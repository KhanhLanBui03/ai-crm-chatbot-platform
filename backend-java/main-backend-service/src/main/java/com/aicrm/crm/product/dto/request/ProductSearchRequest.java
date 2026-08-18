package com.aicrm.crm.product.dto.request;

import lombok.Data;

@Data
public class ProductSearchRequest {
    private String name;
    private String sku;
    private String status;
    private Long businessId;
}
