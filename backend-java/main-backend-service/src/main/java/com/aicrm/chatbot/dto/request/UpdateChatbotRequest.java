package com.aicrm.chatbot.dto.request;

import lombok.Data;

@Data
public class UpdateChatbotRequest {
    private String name;
    private String welcomeMessage;
    private String systemPrompt;
    private Double temperature;
    private String primaryColor;
    private String avatarUrl;
    private String status;
}
