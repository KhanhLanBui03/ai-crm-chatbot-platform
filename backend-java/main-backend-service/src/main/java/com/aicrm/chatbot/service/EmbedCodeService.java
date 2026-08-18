package com.aicrm.chatbot.service;

import com.aicrm.chatbot.dto.response.EmbedCodeResponse;
import com.aicrm.chatbot.entity.Chatbot;
import com.aicrm.chatbot.repository.ChatbotRepository;
import com.aicrm.common.exception.ResourceNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class EmbedCodeService {

    @Autowired
    private ChatbotRepository chatbotRepository;

    /**
     * Chức năng: Sinh mã nhúng widget (Embed code)
     * - Trả về một đoạn mã HTML/JavaScript mẫu chứa token bảo mật của chatbot
     * - Khách hàng có thể copy đoạn script này để nhúng khung chat vào website của họ
     */
    public EmbedCodeResponse getEmbedCode(Long chatbotId) {
        Chatbot chatbot = chatbotRepository.findById(chatbotId)
                .orElseThrow(() -> new ResourceNotFoundException("Chatbot not found with id: " + chatbotId));

        String code = String.format(
                "<script>\n" +
                        "  window.AICRM_CHATBOT_CONFIG = {\n" +
                        "    token: \"%s\"\n" +
                        "  };\n" +
                        "</script>\n" +
                        "<script src=\"http://localhost:5173/widget.js\" defer></script>",
                chatbot.getEmbedToken());

        return EmbedCodeResponse.builder().embedCode(code).build();
    }
}
