package com.aicrm.document.controller;

import com.aicrm.common.response.ApiResponse;
import com.aicrm.document.dto.request.ProcessDocumentRequest;
import com.aicrm.document.dto.response.DocumentDetailResponse;
import com.aicrm.document.dto.response.DocumentResponse;
import com.aicrm.document.service.DocumentProcessingService;
import com.aicrm.document.service.DocumentService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    @Autowired
    private DocumentService documentService;

    @Autowired
    private DocumentProcessingService processingService;

    @PostMapping("/upload")
    public ResponseEntity<ApiResponse<DocumentResponse>> uploadFile(
            @RequestParam("businessId") Long businessId,
            @RequestParam("chatbotId") Long chatbotId,
            @RequestParam("file") MultipartFile file) {
        DocumentResponse response = documentService.uploadDocument(businessId, chatbotId, file);
        return ResponseEntity.ok(ApiResponse.success(response, "Document uploaded successfully"));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<DocumentDetailResponse>> getDocument(@PathVariable Long id) {
        DocumentDetailResponse response = documentService.getDocumentDetails(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/chatbot/{chatbotId}")
    public ResponseEntity<ApiResponse<List<DocumentResponse>>> getChatbotDocuments(@PathVariable Long chatbotId) {
        List<DocumentResponse> response = documentService.getDocumentsByChatbot(chatbotId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/process")
    public ResponseEntity<ApiResponse<Void>> processDocument(@RequestBody ProcessDocumentRequest request) {
        processingService.processDocument(request.getDocumentId());
        return ResponseEntity.ok(ApiResponse.success(null, "Document parsing initiated"));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteDocument(@PathVariable Long id) {
        documentService.deleteDocument(id);
        return ResponseEntity.ok(ApiResponse.success(null, "Document deleted successfully"));
    }
}
