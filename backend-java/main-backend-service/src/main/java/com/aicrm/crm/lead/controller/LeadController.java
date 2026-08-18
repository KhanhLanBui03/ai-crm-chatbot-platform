package com.aicrm.crm.lead.controller;

import com.aicrm.common.response.ApiResponse;
import com.aicrm.crm.lead.dto.request.CreateLeadRequest;
import com.aicrm.crm.lead.dto.request.UpdateLeadRequest;
import com.aicrm.crm.lead.dto.response.LeadResponse;
import com.aicrm.crm.lead.service.LeadService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/leads")
public class LeadController {

    @Autowired
    private LeadService leadService;

    @PostMapping
    public ResponseEntity<ApiResponse<LeadResponse>> create(@RequestBody CreateLeadRequest request) {
        LeadResponse response = leadService.createLead(request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<LeadResponse>> update(
            @PathVariable Long id,
            @RequestBody UpdateLeadRequest request) {
        LeadResponse response = leadService.updateLead(id, request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/business/{businessId}")
    public ResponseEntity<ApiResponse<List<LeadResponse>>> getByBusiness(@PathVariable Long businessId) {
        List<LeadResponse> list = leadService.getLeadsByBusiness(businessId);
        return ResponseEntity.ok(ApiResponse.success(list));
    }
}
