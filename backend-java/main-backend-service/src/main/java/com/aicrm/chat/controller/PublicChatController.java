package com.aicrm.chat.controller;

import com.aicrm.common.response.ApiResponse;
import com.aicrm.chat.dto.request.PublicChatRequest;
import com.aicrm.chat.dto.response.PublicChatResponse;
import com.aicrm.chat.service.PublicChatService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/public")
public class PublicChatController {

    @Autowired
    private PublicChatService publicChatService;

    @PostMapping("/chat/message")
    public ResponseEntity<ApiResponse<PublicChatResponse>> handleMessage(@RequestBody PublicChatRequest request) {
        PublicChatResponse response = publicChatService.handleMessage(request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/chatbot/{chatbotId}/settings")
    public ResponseEntity<ApiResponse<Object>> getChatbotSettings(@PathVariable Long chatbotId) {
        Object response = publicChatService.getChatbotSettings(chatbotId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
