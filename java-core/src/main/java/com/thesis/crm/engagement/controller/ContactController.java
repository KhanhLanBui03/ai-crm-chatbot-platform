package com.thesis.crm.engagement.controller;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.engagement.dto.request.CreateContactRequest;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDetailDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.CreateContactResult;
import com.thesis.crm.engagement.service.ContactService;
import com.thesis.crm.security.SecurityUtils;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * UC016 — {@code /api/v1/contacts} (docs/openapi/dashboard-api.yaml).
 *
 * <p>{@code tenantId} LUÔN lấy từ JWT đã xác thực ({@link SecurityUtils}), không bao giờ từ
 * query/body/path — CLAUDE.md luật 1.
 */
@RestController
@RequestMapping("/api/v1/contacts")
public class ContactController {

    private final ContactService contactService;

    public ContactController(ContactService contactService) {
        this.contactService = contactService;
    }

    /** SCR026 — danh bạ. */
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ContactDto>>> search(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) UUID tagId,
            @RequestParam(required = false) Boolean hasConsent,
            @RequestParam(required = false) String sort,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "25") int size) {
        return ResponseEntity.ok(ApiResponse.ok(
                contactService.search(requireTenantId(), q, status, tagId, hasConsent, sort, page, size)));
    }

    /** SCR027 — tạo khách thủ công; trùng thì vẫn tạo, kèm {@code duplicateCandidates}. */
    @PostMapping
    public ResponseEntity<ApiResponse<CreateContactResult>> create(
            @Valid @RequestBody CreateContactRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(contactService.create(requireTenantId(), request)));
    }

    /** SCR024 — hồ sơ khách hàng. */
    @GetMapping("/{contactId}")
    public ResponseEntity<ApiResponse<ContactDetailDto>> getById(@PathVariable UUID contactId) {
        return ResponseEntity.ok(ApiResponse.ok(contactService.getById(requireTenantId(), contactId)));
    }

    /**
     * SCR025 — hợp nhất: CHƯA nằm trong phạm vi lần này. Trả 501 với câu rõ ràng để nút
     * "Hợp nhất" có sẵn trên giao diện báo lỗi dễ hiểu thay vì 404 khó đoán.
     */
    @PostMapping("/{contactId}/merge")
    public ResponseEntity<ApiResponse<Void>> merge(@PathVariable UUID contactId) {
        requireTenantId();
        throw new AppException(
                "Chức năng hợp nhất khách hàng chưa được hỗ trợ ở phiên bản này.", HttpStatus.NOT_IMPLEMENTED);
    }

    private UUID requireTenantId() {
        UUID tenantId = SecurityUtils.getCurrentTenantId();
        if (tenantId == null) {
            throw new AppException(
                    "Phiên làm việc không hợp lệ hoặc thiếu thông tin doanh nghiệp.", HttpStatus.UNAUTHORIZED);
        }
        return tenantId;
    }
}
