package com.thesis.crm.sales.deal;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.sales.deal.DealDtos.CreateDealRequest;
import com.thesis.crm.sales.deal.DealDtos.DealDetail;
import com.thesis.crm.sales.deal.DealDtos.DealDto;
import com.thesis.crm.sales.deal.DealDtos.MoveStageRequest;
import com.thesis.crm.sales.deal.DealDtos.PipelineDto;
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
 * UC034 — SCR044 bảng phễu, SCR045 chi tiết deal, SCR046 tạo deal thủ công. Tenant và người thao tác
 * chỉ lấy từ JWT (luật 1). Chuyển lead thành deal (UC033) ở {@code POST /api/v1/leads/{id}/convert}.
 */
@RestController
@RequestMapping("/api/v1")
public class DealController {

    private final DealService service;

    public DealController(DealService service) {
        this.service = service;
    }

    @GetMapping("/pipelines")
    public ResponseEntity<ApiResponse<List<PipelineDto>>> pipelines(
            @RequestParam(defaultValue = "false") boolean includeInactive) {
        return ResponseEntity.ok(ApiResponse.ok(service.pipelines(requireTenantId(), includeInactive)));
    }

    @GetMapping("/deals")
    public ResponseEntity<ApiResponse<PageResponse<DealDto>>> list(
            @RequestParam(required = false) UUID pipelineId,
            @RequestParam(required = false) UUID stageId,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) UUID ownerUserId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "200") int size) {
        return ResponseEntity.ok(ApiResponse.ok(
                service.list(requireTenantId(), pipelineId, stageId, status, ownerUserId, page, size)));
    }

    @PostMapping("/deals")
    public ResponseEntity<ApiResponse<DealDto>> create(@RequestBody CreateDealRequest body) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(service.create(requireTenantId(), actor(), body)));
    }

    @GetMapping("/deals/{dealId}")
    public ResponseEntity<ApiResponse<DealDetail>> detail(@PathVariable UUID dealId) {
        return ResponseEntity.ok(ApiResponse.ok(service.detail(requireTenantId(), dealId)));
    }

    @PatchMapping("/deals/{dealId}")
    public ResponseEntity<ApiResponse<DealDetail>> update(@PathVariable UUID dealId, @RequestBody JsonNode body) {
        return ResponseEntity.ok(ApiResponse.ok(service.update(requireTenantId(), actor(), dealId, body)));
    }

    @PostMapping("/deals/{dealId}/stage")
    public ResponseEntity<ApiResponse<DealDetail>> stage(@PathVariable UUID dealId,
                                                         @RequestBody MoveStageRequest body) {
        return ResponseEntity.ok(ApiResponse.ok(service.moveStage(
                requireTenantId(), actor(), dealId, body.stageId(), body.closeReason())));
    }

    private static Actor actor() {
        return new Actor(requireUserId(), isTenantAdmin());
    }
}
