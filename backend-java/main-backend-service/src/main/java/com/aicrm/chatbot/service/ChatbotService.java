package com.aicrm.chatbot.service;

import com.aicrm.chatbot.dto.request.CreateChatbotRequest;
import com.aicrm.chatbot.dto.request.UpdateChatbotRequest;
import com.aicrm.chatbot.dto.response.ChatbotDetailResponse;
import com.aicrm.chatbot.dto.response.ChatbotResponse;
import com.aicrm.chatbot.entity.Chatbot;
import com.aicrm.chatbot.entity.ChatbotAllowedDomain;
import com.aicrm.chatbot.repository.ChatbotAllowedDomainRepository;
import com.aicrm.chatbot.repository.ChatbotRepository;
import com.aicrm.common.enums.ChatbotStatus;
import com.aicrm.common.exception.ResourceNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class ChatbotService {

    @Autowired
    private ChatbotRepository chatbotRepository;

    @Autowired
    private ChatbotAllowedDomainRepository domainRepository;

    /**
     * Chức năng: Tạo chatbot mới
     * - Lưu thông tin cấu hình ban đầu (tên, thông điệp chào mừng, system prompt, temperature, màu sắc, avatar)
     * - Tự động sinh ra mã embedToken ngẫu nhiên dưới dạng UUID để phục vụ cho việc nhúng widget
     */
    public ChatbotResponse createChatbot(CreateChatbotRequest request) {
        Chatbot chatbot = Chatbot.builder()
                .name(request.getName())
                .businessId(request.getBusinessId())
                .welcomeMessage(request.getWelcomeMessage())
                .systemPrompt(request.getSystemPrompt())
                .temperature(request.getTemperature() != null ? request.getTemperature() : 0.7)
                .primaryColor(request.getPrimaryColor())
                .avatarUrl(request.getAvatarUrl())
                .embedToken(UUID.randomUUID().toString())
                .status(ChatbotStatus.ACTIVE)
                .build();

        Chatbot saved = chatbotRepository.save(chatbot);
        return mapToResponse(saved);
    }

    /**
     * Chức năng: Lấy thông tin chi tiết của chatbot
     * - Truy vấn thông tin của chatbot từ CSDL theo ID
     * - Lấy danh sách các domain được cho phép nhúng widget (allowed domains) tương ứng
     */
    public ChatbotDetailResponse getChatbotDetails(Long id) {
        Chatbot chatbot = chatbotRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Chatbot not found with id: " + id));

        List<String> domains = domainRepository.findByChatbotId(id)
                .stream()
                .map(ChatbotAllowedDomain::getDomain)
                .collect(Collectors.toList());

        return mapToDetailResponse(chatbot, domains);
    }

    /**
     * Chức năng: Cập nhật thông tin chatbot / Cấu hình giao diện chatbot
     * - Cho phép cập nhật linh hoạt các thông số như tên, welcome message, prompt, màu chủ đạo (primaryColor), ảnh đại diện (avatarUrl)
     */
    public ChatbotResponse updateChatbot(Long id, UpdateChatbotRequest request) {
        Chatbot chatbot = chatbotRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Chatbot not found with id: " + id));

        if (request.getName() != null)
            chatbot.setName(request.getName());
        if (request.getWelcomeMessage() != null)
            chatbot.setWelcomeMessage(request.getWelcomeMessage());
        if (request.getSystemPrompt() != null)
            chatbot.setSystemPrompt(request.getSystemPrompt());
        if (request.getTemperature() != null)
            chatbot.setTemperature(request.getTemperature());
        if (request.getPrimaryColor() != null)
            chatbot.setPrimaryColor(request.getPrimaryColor());
        if (request.getAvatarUrl() != null)
            chatbot.setAvatarUrl(request.getAvatarUrl());
        if (request.getStatus() != null)
            chatbot.setStatus(ChatbotStatus.valueOf(request.getStatus().toUpperCase()));

        Chatbot saved = chatbotRepository.save(chatbot);
        return mapToResponse(saved);
    }

    /**
     * Chức năng: Lấy danh sách chatbot của doanh nghiệp
     * - Truy vấn toàn bộ danh sách các chatbot thuộc sở hữu của doanh nghiệp dựa vào businessId
     */
    public List<ChatbotResponse> getChatbotsByBusiness(Long businessId) {
        return chatbotRepository.findByBusinessId(businessId)
                .stream()
                .map(this::mapToResponse)
                .collect(Collectors.toList());
    }

    private ChatbotResponse mapToResponse(Chatbot chatbot) {
        return ChatbotResponse.builder()
                .id(chatbot.getId())
                .businessId(chatbot.getBusinessId())
                .name(chatbot.getName())
                .welcomeMessage(chatbot.getWelcomeMessage())
                .primaryColor(chatbot.getPrimaryColor())
                .avatarUrl(chatbot.getAvatarUrl())
                .embedToken(chatbot.getEmbedToken())
                .status(chatbot.getStatus().name())
                .createdAt(chatbot.getCreatedAt())
                .updatedAt(chatbot.getUpdatedAt())
                .build();
    }

    private ChatbotDetailResponse mapToDetailResponse(Chatbot chatbot, List<String> domains) {
        return ChatbotDetailResponse.builder()
                .id(chatbot.getId())
                .businessId(chatbot.getBusinessId())
                .name(chatbot.getName())
                .systemPrompt(chatbot.getSystemPrompt())
                .temperature(chatbot.getTemperature())
                .welcomeMessage(chatbot.getWelcomeMessage())
                .primaryColor(chatbot.getPrimaryColor())
                .avatarUrl(chatbot.getAvatarUrl())
                .embedToken(chatbot.getEmbedToken())
                .status(chatbot.getStatus().name())
                .allowedDomains(domains)
                .createdAt(chatbot.getCreatedAt())
                .updatedAt(chatbot.getUpdatedAt())
                .build();
    }
}
