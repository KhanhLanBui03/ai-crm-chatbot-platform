package com.aicrm.integration.ai;

import lombok.Data;

@Data
public class AiDocumentProcessRequest {
    private Long documentId;
    private String content;
    private String fileType;
}
