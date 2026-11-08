package com.thesis.crm.analytics.controller;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;

import com.thesis.crm.analytics.dto.response.AiPerformanceDtos.HieuQuaAi;
import com.thesis.crm.analytics.dto.response.TopicDtos.ThongKeChuDe;
import com.thesis.crm.analytics.service.AiPerformanceService;
import com.thesis.crm.analytics.service.TopicReportService;
import com.thesis.crm.common.response.ApiResponse;
import java.time.LocalDate;
import java.util.List;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** UC039 — SCR051 hiệu quả và chi phí của tác tử AI · UC038 — SCR052 chủ đề hội thoại. Ngày tính theo múi giờ doanh nghiệp; mặc định 30 ngày qua. */
@RestController
@RequestMapping("/api/v1/analytics")
public class AiPerformanceController {

    private final AiPerformanceService service;
    private final TopicReportService topics;

    public AiPerformanceController(AiPerformanceService service, TopicReportService topics) {
        this.service = service;
        this.topics = topics;
    }

    @GetMapping("/ai-performance")
    public ResponseEntity<ApiResponse<HieuQuaAi>> aiPerformance(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(required = false) String modelVersion) {
        return ResponseEntity.ok(ApiResponse.ok(service.report(requireTenantId(), isTenantAdmin(), from, to,
                modelVersion)));
    }

    /** UC038 — SCR052 thống kê chủ đề hội thoại. Mặc định lớp {@code INTENT}, 30 ngày gần nhất. */
    @GetMapping("/topics")
    public ResponseEntity<ApiResponse<List<ThongKeChuDe>>> topics(
            @RequestParam(required = false) String dimension,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        return ResponseEntity.ok(ApiResponse.ok(topics.report(requireTenantId(), isTenantAdmin(), dimension, from,
                to)));
    }
}
