package com.thesis.crm.sales.lead;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.security.InternalCaller;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * UC041 — {@code DELETE /internal/contacts/{id}/lead-scores}, CHỈ ai-service gọi ({@code X-Internal-Token})
 * giữa lượt xoá dữ liệu cá nhân. Trả {@code {deleted: n}}; khách không có điểm thì 200 với 0. Nháp hợp
 * đồng: {@code docs/contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md} mục 3.
 */
@RestController
@RequestMapping("/internal/contacts")
public class InternalLeadScoreController {

    private final LeadScoreErasureService service;

    public InternalLeadScoreController(LeadScoreErasureService service) {
        this.service = service;
    }

    @DeleteMapping("/{contactId}/lead-scores")
    public ResponseEntity<ApiResponse<Map<String, Integer>>> deleteScores(
            @RequestHeader(value = "X-Tenant-Id", required = false) String tenant,
            @PathVariable UUID contactId) {
        int n = service.deleteScoresOfContact(InternalCaller.requireTenantId(tenant), contactId);
        return ResponseEntity.ok(ApiResponse.ok(Map.of("deleted", n)));
    }
}
