package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.platform.dto.request.UpdateTenantProfileRequest;
import com.thesis.crm.platform.dto.response.TenantProfileResponse;
import com.thesis.crm.platform.service.TenantService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * Controller quản lý Hồ sơ doanh nghiệp (SCR007).
 *
 * <p>GET /api/v1/tenant: xem hồ sơ doanh nghiệp (mọi thành viên trong tenant).
 * <p>PATCH /api/v1/tenant: cập nhật hồ sơ (chỉ TENANT_ADMIN).
 */
@RestController
@RequestMapping("/api/v1/tenant")
public class TenantController {

    private final TenantService tenantService;

    public TenantController(TenantService tenantService) {
        this.tenantService = tenantService;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<TenantProfileResponse>> getProfile() {
        return ResponseEntity.ok(ApiResponse.ok(tenantService.getProfile()));
    }

    @PatchMapping
    public ResponseEntity<ApiResponse<TenantProfileResponse>> updateProfile(
            @Valid @RequestBody UpdateTenantProfileRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(tenantService.updateProfile(request)));
    }
}
