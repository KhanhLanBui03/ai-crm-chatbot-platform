package com.aicrm.document.service;

import com.aicrm.document.dto.response.DocumentDetailResponse;
import com.aicrm.document.dto.response.DocumentResponse;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@Service
public class DocumentService {

    /**
     * Chức năng: Upload PDF/DOCX
     */
    public DocumentResponse uploadDocument(Long businessId, Long chatbotId, MultipartFile file) {
        // TODO: Xử lý nhận file tải lên từ người dùng
        return null;
    }

    /**
     * Chức năng: Lưu metadata file
     */
    public DocumentResponse saveMetadata(Long businessId, Long chatbotId, String fileName, String fileType, Long fileSize, String filePath) {
        // TODO: Lưu thông tin chi tiết của tài liệu (tên file, loại file, dung lượng, đường dẫn) vào database
        return null;
    }

    /**
     * Chức năng: Lưu trạng thái xử lý tài liệu
     */
    public void updateProcessingStatus(Long documentId, String status) {
        // TODO: Cập nhật trạng thái xử lý (UPLOADED, PROCESSING, EMBEDDED, FAILED) của tài liệu
    }

    public DocumentDetailResponse getDocumentDetails(Long id) {
        return null;
    }

    public List<DocumentResponse> getDocumentsByChatbot(Long chatbotId) {
        return null;
    }

    public void deleteDocument(Long id) {
    }
}
