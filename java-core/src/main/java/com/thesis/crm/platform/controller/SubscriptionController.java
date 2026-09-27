package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.platform.dto.request.ChangePlanRequest;
import com.thesis.crm.platform.dto.response.GoiDichVuResponse;
import com.thesis.crm.platform.dto.response.HanMucSuDungResponse;
import com.thesis.crm.platform.dto.response.ThueBaoResponse;
import com.thesis.crm.platform.service.SubscriptionService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Controller quản lý Gói dịch vụ, Thuê bao và Hạn mức sử dụng (SCR012 · SCR013 · SCR014).
 */
@RestController
@RequestMapping("/api/v1")
public class SubscriptionController {

    private final SubscriptionService subscriptionService;

    public SubscriptionController(SubscriptionService subscriptionService) {
        this.subscriptionService = subscriptionService;
    }

    @GetMapping("/plans")
    public ResponseEntity<ApiResponse<List<GoiDichVuResponse>>> getPlans() {
        return ResponseEntity.ok(ApiResponse.ok(subscriptionService.getPlans()));
    }

    @GetMapping("/subscription")
    public ResponseEntity<ApiResponse<ThueBaoResponse>> getCurrentSubscription() {
        return ResponseEntity.ok(ApiResponse.ok(subscriptionService.getCurrentSubscription()));
    }

    @PostMapping("/subscription/change")
    public ResponseEntity<ApiResponse<ThueBaoResponse>> changePlan(
            @Valid @RequestBody ChangePlanRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(subscriptionService.changePlan(request)));
    }

    @GetMapping("/usage")
    public ResponseEntity<ApiResponse<HanMucSuDungResponse>> getCurrentUsage() {
        return ResponseEntity.ok(ApiResponse.ok(subscriptionService.getCurrentUsage()));
    }
}
