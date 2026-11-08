package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.service.UsageDailyService;
import com.thesis.crm.platform.service.UsageDailyService.DiemSuDungNgay;
import com.thesis.crm.security.CurrentActor;
import java.time.LocalDate;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.RequestParam;
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
    private final UsageDailyService usageDaily;

    public SubscriptionController(SubscriptionService subscriptionService, UsageDailyService usageDaily) {
        this.subscriptionService = subscriptionService;
        this.usageDaily = usageDaily;
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

    /** UC006 bước 5–7 — SCR015: mức sử dụng theo ngày, tách theo kênh HOẶC theo nhánh. Chỉ quản trị viên. */
    @GetMapping("/usage/daily")
    public ResponseEntity<ApiResponse<PageResponse<DiemSuDungNgay>>> getDailyUsage(
            @RequestParam(defaultValue = "channel") String groupBy,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(required = false) String sort,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "30") int size) {
        return ResponseEntity.ok(ApiResponse.ok(usageDaily.daily(CurrentActor.requireTenantId(),
                CurrentActor.isTenantAdmin(), groupBy, from, to, sort, page, size)));
    }
}
