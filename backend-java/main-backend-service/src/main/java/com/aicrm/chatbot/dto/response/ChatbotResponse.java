package com.aicrm.chatbot.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ChatbotResponse {
    private Long id;
    private Long businessId;
    private String name;
    private String welcomeMessage;
    private String primaryColor;
    private String avatarUrl;
    private String embedToken;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
