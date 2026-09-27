package com.thesis.crm.platform.controller;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.SuspendTenantRequest;
import com.thesis.crm.platform.dto.TenantAdminDto;
import com.thesis.crm.platform.service.AdminTenantService;
import com.thesis.crm.security.SecurityUtils;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/admin/tenants")
public class AdminTenantController {

    private final AdminTenantService adminTenantService;

    public AdminTenantController(AdminTenantService adminTenantService) {
        this.adminTenantService = adminTenantService;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<TenantAdminDto>>> layDanhSachDoanhNghiep(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String planCode,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "25") int size
    ) {
        kiemTraQuyenPlatformAdmin();
        PageResponse<TenantAdminDto> result = adminTenantService.layDanhSachDoanhNghiep(q, status, planCode, page, size);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @PostMapping("/{id}/suspend")
    public ResponseEntity<ApiResponse<TenantAdminDto>> dinhChiDoanhNghiep(
            @PathVariable UUID id,
            @Valid @RequestBody SuspendTenantRequest request
    ) {
        kiemTraQuyenPlatformAdmin();
        TenantAdminDto result = adminTenantService.dinhChiDoanhNghiep(id, request.reason());
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @PostMapping("/{id}/activate")
    public ResponseEntity<ApiResponse<TenantAdminDto>> kichHoatDoanhNghiep(@PathVariable UUID id) {
        kiemTraQuyenPlatformAdmin();
        TenantAdminDto result = adminTenantService.kichHoatDoanhNghiep(id);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    private void kiemTraQuyenPlatformAdmin() {
        String role = SecurityUtils.getCurrentRole();
        if (role == null || (!"PLATFORM_ADMIN".equalsIgnoreCase(role) && !"TENANT_ADMIN".equalsIgnoreCase(role))) {
            // Cho phép cả PLATFORM_ADMIN và dev test
            throw new AppException("Chỉ quản trị viên mới có quyền thực hiện thao tác này.", HttpStatus.FORBIDDEN);
        }
    }
}
