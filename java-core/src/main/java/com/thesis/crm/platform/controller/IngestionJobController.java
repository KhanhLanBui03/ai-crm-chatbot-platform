package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.response.CongViecNapResponse;
import com.thesis.crm.platform.service.KnowledgeDocumentService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * SCR033 — hàng đợi nạp, UC019 bước 12. Hình chiếu từ {@code knowledge_documents.status} phía
 * ai-service (đặc tả UC019: "không phải một bảng ingestion_jobs riêng"); java-core chỉ chuyển tiếp.
 */
@RestController
@RequestMapping("/api/v1/ingestion-jobs")
public class IngestionJobController {

    private final KnowledgeDocumentService documentService;

    public IngestionJobController(KnowledgeDocumentService documentService) {
        this.documentService = documentService;
    }

    @GetMapping
    public ApiResponse<PageResponse<CongViecNapResponse>> list(
            @RequestParam(required = false) String state,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ApiResponse.ok(documentService.ingestionJobs(state, page, size));
    }
}
