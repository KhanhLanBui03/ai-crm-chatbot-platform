package com.aicrm.chatbot.dto.response;

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
public class ChatbotDetailResponse {
    private Long id;
    private Long businessId;
    private String name;
    private String systemPrompt;
    private Double temperature;
    private String welcomeMessage;
    private String primaryColor;
    private String avatarUrl;
    private String embedToken;
    private String status;
    private List<String> allowedDomains;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
