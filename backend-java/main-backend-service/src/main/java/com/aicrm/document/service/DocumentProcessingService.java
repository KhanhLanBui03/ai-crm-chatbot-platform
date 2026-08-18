package com.aicrm.document.service;

import org.springframework.stereotype.Service;

@Service
public class DocumentProcessingService {

    /**
     * Chức năng: Gọi Python AI Service để xử lý RAG
     * - Gửi request tới python-ai-service với thông tin file để thực hiện đọc văn bản,
     *   chia tách câu (chunking), sinh embeddings và lập chỉ mục vào Qdrant.
     */
    public void triggerAiProcessing(Long documentId) {
        // TODO: Gửi yêu cầu RAG processing sang Python FastAPI service
    }

    public void processDocument(Long documentId) {
    }
}
