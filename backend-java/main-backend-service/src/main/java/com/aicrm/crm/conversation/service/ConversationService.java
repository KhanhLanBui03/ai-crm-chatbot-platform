package com.aicrm.crm.conversation.service;

import com.aicrm.crm.conversation.dto.response.ConversationDetailResponse;
import com.aicrm.crm.conversation.dto.response.ConversationResponse;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ConversationService {

    /**
     * Chức năng: Lấy thông tin chi tiết cuộc hội thoại kèm lịch sử tin nhắn
     */
    public ConversationDetailResponse getConversationDetails(Long id) {
        // TODO: Dựng function lấy lịch sử hội thoại
        return null;
    }

    /**
     * Chức năng: Lấy danh sách hội thoại của một chatbot
     */
    public List<ConversationResponse> getConversationsByChatbot(Long chatbotId) {
        // TODO: Dựng function lấy danh sách hội thoại của chatbot
        return null;
    }
}
