package com.aicrm.chat.service;

import com.aicrm.chat.dto.request.PublicChatRequest;
import com.aicrm.chat.dto.response.PublicChatResponse;
import org.springframework.stereotype.Service;

@Service
public class PublicChatService {

    /**
     * Nhận tin nhắn từ widget, xác định chatbotId, gọi Python AI Service, lưu hội thoại vào CRM và trả câu trả lời về widget.
     */
    public PublicChatResponse handleMessage(PublicChatRequest request) {
        return null;
    }

    /**
     * Lấy cài đặt chatbot public dựa trên chatbotId.
     */
    public Object getChatbotSettings(Long chatbotId) {
        return null;
    }
}
