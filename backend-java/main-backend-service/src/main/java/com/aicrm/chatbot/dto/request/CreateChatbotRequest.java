package com.aicrm.chatbot.dto.request;

import lombok.Data;

@Data
public class CreateChatbotRequest {
    private String name;
    private Long businessId;
    private String welcomeMessage;
    private String systemPrompt;
    private Double temperature;
    private String primaryColor;
    private String avatarUrl;
}
