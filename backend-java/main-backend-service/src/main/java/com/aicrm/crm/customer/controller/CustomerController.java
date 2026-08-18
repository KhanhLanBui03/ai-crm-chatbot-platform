package com.aicrm.crm.customer.controller;

import com.aicrm.common.response.ApiResponse;
import com.aicrm.crm.customer.dto.request.CreateCustomerRequest;
import com.aicrm.crm.customer.dto.request.UpdateCustomerRequest;
import com.aicrm.crm.customer.dto.response.CustomerDetailResponse;
import com.aicrm.crm.customer.dto.response.CustomerResponse;
import com.aicrm.crm.customer.service.CustomerService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/customers")
public class CustomerController {

    @Autowired
    private CustomerService customerService;

    @PostMapping
    public ResponseEntity<ApiResponse<CustomerResponse>> create(@RequestBody CreateCustomerRequest request) {
        CustomerResponse response = customerService.createCustomer(request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<CustomerResponse>> update(
            @PathVariable Long id,
            @RequestBody UpdateCustomerRequest request) {
        CustomerResponse response = customerService.updateCustomer(id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<CustomerDetailResponse>> getById(@PathVariable Long id) {
        CustomerDetailResponse response = customerService.getCustomerById(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/business/{businessId}")
    public ResponseEntity<ApiResponse<List<CustomerResponse>>> getByBusiness(@PathVariable Long businessId) {
        List<CustomerResponse> list = customerService.getCustomersByBusiness(businessId);
        return ResponseEntity.ok(ApiResponse.success(list));
    }
}
