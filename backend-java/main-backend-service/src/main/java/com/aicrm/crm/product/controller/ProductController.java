package com.aicrm.crm.product.controller;

import com.aicrm.common.response.ApiResponse;
import com.aicrm.crm.product.dto.request.CreateProductRequest;
import com.aicrm.crm.product.dto.request.ProductSearchRequest;
import com.aicrm.crm.product.dto.request.UpdateProductRequest;
import com.aicrm.crm.product.dto.response.ProductDetailResponse;
import com.aicrm.crm.product.dto.response.ProductResponse;
import com.aicrm.crm.product.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    @Autowired
    private ProductService productService;

    @PostMapping
    public ResponseEntity<ApiResponse<ProductResponse>> create(@RequestBody CreateProductRequest request) {
        ProductResponse response = productService.createProduct(request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<ProductResponse>> update(
            @PathVariable Long id,
            @RequestBody UpdateProductRequest request) {
        ProductResponse response = productService.updateProduct(id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<ProductDetailResponse>> getById(@PathVariable Long id) {
        ProductDetailResponse response = productService.getProductById(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/business/{businessId}")
    public ResponseEntity<ApiResponse<List<ProductResponse>>> getByBusiness(@PathVariable Long businessId) {
        List<ProductResponse> list = productService.getProductsByBusiness(businessId);
        return ResponseEntity.ok(ApiResponse.success(list));
    }

    @GetMapping("/search")
    public ResponseEntity<ApiResponse<List<ProductResponse>>> search(ProductSearchRequest request) {
        List<ProductResponse> list = productService.searchProducts(request);
        return ResponseEntity.ok(ApiResponse.success(list));
    }
}
