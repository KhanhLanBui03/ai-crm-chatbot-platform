package com.aicrm.crm.product.controller;

import com.aicrm.common.response.ApiResponse;
import com.aicrm.crm.product.dto.response.PriceResponse;
import com.aicrm.crm.product.dto.response.StockResponse;
import com.aicrm.crm.product.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/internal/products")
public class InternalProductController {

    @Autowired
    private ProductService productService;

    @GetMapping("/{id}/price")
    public ResponseEntity<ApiResponse<PriceResponse>> getPrice(@PathVariable Long id) {
        PriceResponse response = productService.getProductPrice(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/{id}/stock")
    public ResponseEntity<ApiResponse<StockResponse>> getStock(@PathVariable Long id) {
        StockResponse response = productService.getProductStock(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PutMapping("/{id}/stock")
    public ResponseEntity<ApiResponse<StockResponse>> updateStock(
            @PathVariable Long id,
            @RequestParam Integer quantity) {
        StockResponse response = productService.updateProductStock(id, quantity);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
