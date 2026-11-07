package com.thesis.crm.platform.audit;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.thesis.crm.common.enums.AuditSeverity;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.audit.AuditLogDtos.AuditLogDto;
import com.thesis.crm.platform.audit.AuditLogDtos.RevealRequest;
import java.time.LocalDate;
import java.util.UUID;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * UC040 — SCR054 nhật ký kiểm toán. Không có endpoint sửa hay xoá: hai thao tác đó không tồn tại ở tầng quyền
 * ({@code crm_app} bị thu hồi UPDATE/DELETE trên bảng, V111) nên cũng không có đường nào từ ứng dụng.
 */
@RestController
@RequestMapping("/api/v1/audit-logs")
public class AuditLogController {

    private final AuditLogService service;

    public AuditLogController(AuditLogService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<AuditLogDto>>> list(
            @RequestParam(required = false) String action,
            @RequestParam(required = false) UUID actorId,
            @RequestParam(required = false) AuditSeverity severity,
            @RequestParam(required = false) String entityType,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "25") int size) {
        return ResponseEntity.ok(ApiResponse.ok(service.list(requireTenantId(), isTenantAdmin(),
                new AuditLogService.Filter(action, actorId, severity, entityType, from, to, page, size))));
    }

    @PostMapping("/{logId}/reveal")
    public ResponseEntity<ApiResponse<AuditLogDto>> reveal(@PathVariable long logId,
                                                           @RequestBody(required = false) RevealRequest body) {
        return ResponseEntity.ok(ApiResponse.ok(service.reveal(requireTenantId(), requireUserId(), isTenantAdmin(),
                logId, body == null ? null : body.reason())));
    }
}
