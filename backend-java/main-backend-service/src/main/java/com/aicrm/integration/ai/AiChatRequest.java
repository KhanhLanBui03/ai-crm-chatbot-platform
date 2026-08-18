package com.aicrm.integration.ai;

import lombok.Data;

@Data
public class AiChatRequest {
    private String message;
    private String sessionId;
    private Long chatbotId;
}
