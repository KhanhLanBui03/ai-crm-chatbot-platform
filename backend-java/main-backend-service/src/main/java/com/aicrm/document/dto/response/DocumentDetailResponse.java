package com.aicrm.document.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DocumentDetailResponse {
    private Long id;
    private Long businessId;
    private Long chatbotId;
    private String fileName;
    private String fileType;
    private Long fileSize;
    private String filePath;
    private String status;
    private List<DocumentChunkResponse> chunks;
    private LocalDateTime uploadedAt;
    private LocalDateTime processedAt;
}
