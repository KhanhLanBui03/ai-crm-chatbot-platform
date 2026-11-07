package com.thesis.crm.analytics.controller;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;

import com.thesis.crm.analytics.dto.response.AiPerformanceDtos.HieuQuaAi;
import com.thesis.crm.analytics.service.AiPerformanceService;
import com.thesis.crm.common.response.ApiResponse;
import java.time.LocalDate;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** UC039 — SCR051 hiệu quả và chi phí của tác tử AI. Ngày tính theo múi giờ doanh nghiệp; mặc định 30 ngày qua. */
@RestController
@RequestMapping("/api/v1/analytics")
public class AiPerformanceController {

    private final AiPerformanceService service;

    public AiPerformanceController(AiPerformanceService service) {
        this.service = service;
    }

    @GetMapping("/ai-performance")
    public ResponseEntity<ApiResponse<HieuQuaAi>> aiPerformance(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(required = false) String modelVersion) {
        return ResponseEntity.ok(ApiResponse.ok(service.report(requireTenantId(), isTenantAdmin(), from, to,
                modelVersion)));
    }
}
