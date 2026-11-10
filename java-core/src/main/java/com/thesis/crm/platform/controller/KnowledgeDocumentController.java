package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.request.UpdateDocumentRequest;
import com.thesis.crm.platform.dto.request.UploadDocumentRequest;
import com.thesis.crm.platform.dto.response.CongViecNapResponse;
import com.thesis.crm.platform.dto.response.DoanTaiLieuResponse;
import com.thesis.crm.platform.dto.response.DocumentUploadResponse;
import com.thesis.crm.platform.dto.response.TaiLieuChiTietResponse;
import com.thesis.crm.platform.dto.response.TaiLieuResponse;
import com.thesis.crm.platform.service.KnowledgeDocumentService;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * Kho tri thức — SCR029–SCR032, UC018 + UC020. Chỉ nhận, validate, gọi service.
 *
 * <p>Quyền {@code TENANT_ADMIN} cho mọi thao tác GHI kiểm ở {@code security/SecurityConfig} theo
 * URL, không bằng {@code @PreAuthorize} ở đây — để người thiếu quyền bị chặn trước khi servlet đọc
 * tệp hay bind thân. Thao tác đọc mở cho mọi nhân viên của doanh nghiệp.
 *
 * <p>{@code size} mặc định 10 theo đặc tả UC020 ("phân trang mặc định 10 bản ghi"), không phải 25
 * của tham số chung {@code CoSize} trong hợp đồng.
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

    /** UC020 bước 2 — tìm không phân biệt hoa thường và dấu (ai-service chuẩn hoá). */
    @GetMapping
    public ApiResponse<PageResponse<TaiLieuResponse>> list(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String sourceType,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ApiResponse.ok(documentService.list(q, status, sourceType, page, size));
    }

    @GetMapping("/{documentId}")
    public ApiResponse<TaiLieuChiTietResponse> get(@PathVariable UUID documentId) {
        return ApiResponse.ok(documentService.get(documentId));
    }

    @GetMapping("/{documentId}/chunks")
    public ApiResponse<PageResponse<DoanTaiLieuResponse>> chunks(
            @PathVariable UUID documentId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ApiResponse.ok(documentService.chunks(documentId, page, size));
    }

    /** UC020 bước 5 — sửa siêu dữ liệu. Nháp hợp đồng: {@code docs/contracts/giao-dien-gd.md}. */
    @PatchMapping("/{documentId}")
    public ApiResponse<TaiLieuChiTietResponse> update(
            @PathVariable UUID documentId,
            @Valid @RequestBody UpdateDocumentRequest request) {
        return ApiResponse.ok(documentService.update(documentId, request));
    }

    /** UC020 bước 6 — 202 + việc nạp của BẢN BÓNG (id mới, ADR-0031). */
    @PostMapping("/{documentId}/reindex")
    public ResponseEntity<ApiResponse<CongViecNapResponse>> reindex(@PathVariable UUID documentId) {
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.ok(documentService.reindex(documentId)));
    }

    /** UC020 bước 7 — gỡ khỏi chỉ mục; tài liệu chuyển {@code ARCHIVED}, không xoá vật lý. */
    @DeleteMapping("/{documentId}")
    public ApiResponse<Void> archive(@PathVariable UUID documentId) {
        documentService.archive(documentId);
        return ApiResponse.ok(null);
    }
}
