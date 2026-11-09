package com.thesis.crm.platform.audit;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.audit.SafetyEventService.SuKienAnToan;
import java.time.LocalDate;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** UC040 bước 8 — màn "Cảnh báo an toàn" hợp nhất ba nguồn. Chỉ quản trị viên doanh nghiệp. */
@RestController
@RequestMapping("/api/v1/safety-events")
public class SafetyEventController {

    private final SafetyEventService service;

    public SafetyEventController(SafetyEventService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<SuKienAnToan>>> list(
            @RequestParam(required = false) String severity,
            @RequestParam(required = false) String eventType,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "25") int size) {
        return ResponseEntity.ok(ApiResponse.ok(service.list(requireTenantId(), isTenantAdmin(), severity, eventType,
                from, to, page, size)));
    }
}
