package com.aicrm.crm.conversation.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ConversationResponse {
    private Long id;
    private String sessionId;
    private String status;
    private Long customerId;
    private Long chatbotId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
