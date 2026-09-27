package com.thesis.crm.platform.controller;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.InviteUserRequest;
import com.thesis.crm.platform.dto.UpdateUserRequest;
import com.thesis.crm.platform.dto.UserDto;
import com.thesis.crm.platform.service.UserService;
import com.thesis.crm.security.SecurityUtils;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<UserDto>>> layDanhSachNguoiDung(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String roleCode,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String sort
    ) {
        UUID tenantId = requireTenantId();
        PageResponse<UserDto> result = userService.layDanhSachNguoiDung(tenantId, q, status, roleCode, page, size, sort);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<UserDto>> moiNguoiDung(@Valid @RequestBody InviteUserRequest request) {
        UUID tenantId = requireTenantId();
        UUID currentUserId = SecurityUtils.getCurrentUserId();
        UserDto created = userService.moiNguoiDung(tenantId, currentUserId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(created));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<UserDto>> layChiTietNguoiDung(@PathVariable UUID id) {
        UUID tenantId = requireTenantId();
        UserDto dto = userService.layChiTietNguoiDung(tenantId, id);
        return ResponseEntity.ok(ApiResponse.ok(dto));
    }

    @PatchMapping("/{id}")
    public ResponseEntity<ApiResponse<UserDto>> capNhatNguoiDung(
            @PathVariable UUID id,
            @Valid @RequestBody UpdateUserRequest request
    ) {
        UUID tenantId = requireTenantId();
        UserDto updated = userService.capNhatNguoiDung(tenantId, id, request);
        return ResponseEntity.ok(ApiResponse.ok(updated));
    }

    @PostMapping("/{id}/disable")
    public ResponseEntity<ApiResponse<UserDto>> voHieuHoaNguoiDung(@PathVariable UUID id) {
        UUID tenantId = requireTenantId();
        UserDto result = userService.voHieuHoaNguoiDung(tenantId, id);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @PostMapping("/{id}/enable")
    public ResponseEntity<ApiResponse<UserDto>> kichHoatNguoiDung(@PathVariable UUID id) {
        UUID tenantId = requireTenantId();
        UserDto result = userService.kichHoatNguoiDung(tenantId, id);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @PostMapping("/{id}/resend-invitation")
    public ResponseEntity<ApiResponse<Void>> guiLaiLoiMoi(@PathVariable UUID id) {
        UUID tenantId = requireTenantId();
        userService.guiLaiLoiMoi(tenantId, id);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> xoaNguoiDung(@PathVariable UUID id) {
        UUID tenantId = requireTenantId();
        userService.xoaNguoiDung(tenantId, id);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    private UUID requireTenantId() {
        UUID tenantId = SecurityUtils.getCurrentTenantId();
        if (tenantId == null) {
            throw new AppException("Phiên làm việc không hợp lệ hoặc thiếu thông tin doanh nghiệp.", HttpStatus.UNAUTHORIZED);
        }
        return tenantId;
    }
}
