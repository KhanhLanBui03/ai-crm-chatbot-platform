package com.aicrm.business.controller;

import com.aicrm.business.dto.request.UpdateBusinessRequest;
import com.aicrm.business.dto.response.BusinessResponse;
import com.aicrm.business.service.BusinessService;
import com.aicrm.common.response.ApiResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/businesses")
public class BusinessController {

    @Autowired
    private BusinessService businessService;

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<BusinessResponse>> getBusiness(@PathVariable Long id) {
        BusinessResponse response = businessService.getBusinessById(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<BusinessResponse>> updateBusiness(
            @PathVariable Long id,
            @RequestBody UpdateBusinessRequest request) {
        BusinessResponse response = businessService.updateBusiness(id, request);
        return ResponseEntity.ok(ApiResponse.success(response, "Business updated successfully"));
    }
}
