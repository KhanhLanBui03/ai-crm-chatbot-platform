package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.platform.dto.request.UploadDocumentRequest;
import com.thesis.crm.platform.dto.response.DocumentUploadResponse;
import com.thesis.crm.platform.service.KnowledgeDocumentService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * Kho tri thức — SCR029, UC018. Chỉ nhận, validate, gọi service.
 *
 * <p>Quyền {@code TENANT_ADMIN} kiểm ở {@code security/SecurityConfig} theo URL, không bằng
 * {@code @PreAuthorize} ở đây — để người thiếu quyền bị chặn trước khi servlet đọc tệp.
 */
@RestController
@RequestMapping("/api/v1/documents")
public class KnowledgeDocumentController {

    private final KnowledgeDocumentService documentService;

    public KnowledgeDocumentController(KnowledgeDocumentService documentService) {
        this.documentService = documentService;
    }

    /** 202 chứ không 201: tài liệu mới ở {@code PENDING}, việc nạp và lập chỉ mục chạy nền. */
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<ApiResponse<DocumentUploadResponse>> upload(
            @RequestPart("file") MultipartFile file,
            @Valid @ModelAttribute UploadDocumentRequest request) {
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(ApiResponse.ok(documentService.upload(file, request)));
    }
}
