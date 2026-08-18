package com.aicrm.crm.message.service;

import com.aicrm.crm.message.dto.response.MessageResponse;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class MessageService {

    /**
     * Chức năng: Lưu trữ nội dung tin nhắn mới vào lịch sử cuộc trò chuyện
     */
    public MessageResponse saveMessage(Long conversationId, String content, String sender) {
        // TODO: Dựng function lưu tin nhắn mới
        return null;
    }

    /**
     * Chức năng: Lấy danh sách tin nhắn theo cuộc hội thoại
     */
    public List<MessageResponse> getMessagesByConversation(Long conversationId) {
        // TODO: Dựng function lấy danh sách tin nhắn
        return null;
    }
}
