package com.thesis.crm.platform.service;

import com.thesis.crm.platform.dto.request.UploadDocumentRequest;
import com.thesis.crm.platform.dto.response.DocumentUploadResponse;
import org.springframework.web.multipart.MultipartFile;

/**
 * Mặt tiền kho tri thức phía java-core — ADR-0014: dashboard không gọi thẳng ai-service.
 *
 * <p>Ở context {@code platform} chứ không phải context riêng: phần việc của java-core trong UC018
 * là hạn mức gói, ghi tệp và outbox — cả ba đều là của {@code platform}. Nội dung tài liệu thuộc
 * schema {@code knowledge} của Track B, java-core chỉ giữ URI.
 */
public interface KnowledgeDocumentService {

    /**
     * UC018 — nhận tệp, ghi lên kho S3, nhờ ai-service tạo bản ghi {@code PENDING}, cộng hạn mức
     * và ghi sự kiện {@code DocumentUploaded}. Kết thúc ngay khi tài liệu được xếp hàng, không chờ
     * lập chỉ mục (UC019 chạy nền).
     */
    DocumentUploadResponse upload(MultipartFile file, UploadDocumentRequest request);
}
