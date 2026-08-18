package com.aicrm.chatbot.controller;

import com.aicrm.chatbot.dto.request.AddAllowedDomainRequest;
import com.aicrm.chatbot.dto.request.CreateChatbotRequest;
import com.aicrm.chatbot.dto.request.UpdateChatbotRequest;
import com.aicrm.chatbot.dto.response.ChatbotDetailResponse;
import com.aicrm.chatbot.dto.response.ChatbotResponse;
import com.aicrm.chatbot.dto.response.EmbedCodeResponse;
import com.aicrm.chatbot.service.ChatbotService;
import com.aicrm.chatbot.service.ChatbotSettingService;
import com.aicrm.chatbot.service.EmbedCodeService;
import com.aicrm.common.response.ApiResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/chatbots")
public class ChatbotController {

    @Autowired
    private ChatbotService chatbotService;

    @Autowired
    private EmbedCodeService embedCodeService;

    @Autowired
    private ChatbotSettingService settingService;

    @PostMapping
    public ResponseEntity<ApiResponse<ChatbotResponse>> createChatbot(@RequestBody CreateChatbotRequest request) {
        ChatbotResponse response = chatbotService.createChatbot(request);
        return ResponseEntity.ok(ApiResponse.success(response, "Chatbot created successfully"));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<ChatbotDetailResponse>> getChatbot(@PathVariable Long id) {
        ChatbotDetailResponse response = chatbotService.getChatbotDetails(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<ChatbotResponse>> updateChatbot(
            @PathVariable Long id,
            @RequestBody UpdateChatbotRequest request) {
        ChatbotResponse response = chatbotService.updateChatbot(id, request);
        return ResponseEntity.ok(ApiResponse.success(response, "Chatbot parameters saved"));
    }

    @GetMapping("/business/{businessId}")
    public ResponseEntity<ApiResponse<List<ChatbotResponse>>> getBusinessChatbots(@PathVariable Long businessId) {
        List<ChatbotResponse> list = chatbotService.getChatbotsByBusiness(businessId);
        return ResponseEntity.ok(ApiResponse.success(list));
    }

    @GetMapping("/{id}/embed")
    public ResponseEntity<ApiResponse<EmbedCodeResponse>> getEmbedCode(@PathVariable Long id) {
        EmbedCodeResponse response = embedCodeService.getEmbedCode(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/{id}/domains")
    public ResponseEntity<ApiResponse<Void>> addDomain(
            @PathVariable Long id,
            @RequestBody AddAllowedDomainRequest request) {
        settingService.addAllowedDomain(id, request.getDomain());
        return ResponseEntity.ok(ApiResponse.success(null, "Domain registered successfully"));
    }
}
