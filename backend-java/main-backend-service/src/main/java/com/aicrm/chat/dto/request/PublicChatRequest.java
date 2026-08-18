package com.aicrm.chat.dto.request;

import lombok.Data;

@Data
public class PublicChatRequest {
    private String message;
    private String sessionId;
    private Long chatbotId;
}
