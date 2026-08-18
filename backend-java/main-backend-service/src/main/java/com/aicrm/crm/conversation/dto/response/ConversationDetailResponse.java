package com.aicrm.crm.conversation.dto.response;

import com.aicrm.crm.message.dto.response.MessageResponse;
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
public class ConversationDetailResponse {
    private Long id;
    private String sessionId;
    private String status;
    private Long customerId;
    private Long chatbotId;
    private List<MessageResponse> messages;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
