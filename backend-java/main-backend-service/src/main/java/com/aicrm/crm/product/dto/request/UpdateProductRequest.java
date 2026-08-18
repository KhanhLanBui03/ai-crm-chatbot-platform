package com.aicrm.crm.product.dto.request;

import java.math.BigDecimal;
import lombok.Data;

@Data
public class UpdateProductRequest {
    private String name;
    private String sku;
    private String description;
    private BigDecimal price;
    private Integer stockQuantity;
    private String status;
}
