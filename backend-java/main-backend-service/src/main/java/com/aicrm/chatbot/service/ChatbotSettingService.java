package com.aicrm.chatbot.service;

import com.aicrm.chatbot.entity.ChatbotAllowedDomain;
import com.aicrm.chatbot.repository.ChatbotAllowedDomainRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class ChatbotSettingService {

    @Autowired
    private ChatbotAllowedDomainRepository domainRepository;

    public void addAllowedDomain(Long chatbotId, String domain) {
        ChatbotAllowedDomain entity = ChatbotAllowedDomain.builder()
                .chatbotId(chatbotId)
                .domain(domain)
                .build();
        domainRepository.save(entity);
    }
}
