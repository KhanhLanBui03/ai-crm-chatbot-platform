package com.thesis.crm.sales.lead;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.sales.deal.DealDtos.ConvertRequest;
import com.thesis.crm.sales.deal.DealDtos.ConvertResult;
import com.thesis.crm.sales.lead.LeadDtos.CreateLeadRequest;
import com.thesis.crm.sales.lead.LeadDtos.LeadDetail;
import com.thesis.crm.sales.lead.LeadDtos.LeadDto;
import com.thesis.crm.sales.lead.LeadDtos.ScoreDto;
import com.thesis.crm.sales.lead.LeadService.Actor;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * UC032 — SCR041 danh sách, SCR042 chi tiết, SCR043 tạo lead thủ công. Tenant và người thao tác chỉ lấy
 * từ JWT (luật 1); body không nhận {@code tenantId}, {@code source} hay điểm số.
 */
@RestController
@RequestMapping("/api/v1/leads")
public class LeadController {

    private final LeadService service;

    public LeadController(LeadService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<LeadDto>>> list(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String source,
            @RequestParam(required = false) UUID ownerUserId,
            @RequestParam(required = false) Integer minScore,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(ApiResponse.ok(
                service.list(requireTenantId(), q, status, source, ownerUserId, minScore, page, size)));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<LeadDto>> create(@RequestBody CreateLeadRequest body) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(service.create(requireTenantId(), actor(), body)));
    }

    @GetMapping("/{leadId}")
    public ResponseEntity<ApiResponse<LeadDetail>> detail(@PathVariable UUID leadId) {
        return ResponseEntity.ok(ApiResponse.ok(service.detail(requireTenantId(), leadId)));
    }

    @PatchMapping("/{leadId}")
    public ResponseEntity<ApiResponse<LeadDetail>> update(@PathVariable UUID leadId, @RequestBody JsonNode body) {
        return ResponseEntity.ok(ApiResponse.ok(service.update(requireTenantId(), actor(), leadId, body)));
    }

    /** UC033 — chuyển lead thành deal. */
    @PostMapping("/{leadId}/convert")
    public ResponseEntity<ApiResponse<ConvertResult>> convert(@PathVariable UUID leadId,
                                                              @RequestBody(required = false) ConvertRequest body) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(service.convert(requireTenantId(), actor(), leadId, body)));
    }

    @GetMapping("/{leadId}/scores")
    public ResponseEntity<ApiResponse<List<ScoreDto>>> scores(@PathVariable UUID leadId) {
        return ResponseEntity.ok(ApiResponse.ok(service.scores(requireTenantId(), leadId)));
    }

    private static Actor actor() {
        return new Actor(requireUserId(), isTenantAdmin());
    }
}
