package com.thesis.crm.platform.controller;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.platform.dto.RoleDto;
import com.thesis.crm.platform.service.RoleService;
import com.thesis.crm.security.SecurityUtils;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/roles")
public class RoleController {

    private final RoleService roleService;

    public RoleController(RoleService roleService) {
        this.roleService = roleService;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<List<RoleDto>>> layDanhSachVaiTro() {
        UUID tenantId = SecurityUtils.getCurrentTenantId();
        if (tenantId == null) {
            throw new AppException("Phiên làm việc không hợp lệ hoặc thiếu thông tin doanh nghiệp.", HttpStatus.UNAUTHORIZED);
        }
        List<RoleDto> roles = roleService.layDanhSachVaiTro(tenantId);
        return ResponseEntity.ok(ApiResponse.ok(roles));
    }
}
