package com.aicrm.crm.conversation.controller;

import com.aicrm.common.response.ApiResponse;
import com.aicrm.crm.conversation.dto.response.ConversationDetailResponse;
import com.aicrm.crm.conversation.dto.response.ConversationResponse;
import com.aicrm.crm.conversation.service.ConversationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/conversations")
public class ConversationController {

    @Autowired
    private ConversationService conversationService;

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<ConversationDetailResponse>> getById(@PathVariable Long id) {
        ConversationDetailResponse response = conversationService.getConversationDetails(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/chatbot/{chatbotId}")
    public ResponseEntity<ApiResponse<List<ConversationResponse>>> getByChatbot(@PathVariable Long chatbotId) {
        List<ConversationResponse> response = conversationService.getConversationsByChatbot(chatbotId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
