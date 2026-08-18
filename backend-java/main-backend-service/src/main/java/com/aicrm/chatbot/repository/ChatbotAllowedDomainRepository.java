package com.aicrm.chatbot.repository;

import com.aicrm.chatbot.entity.ChatbotAllowedDomain;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatbotAllowedDomainRepository extends JpaRepository<ChatbotAllowedDomain, Long> {
    List<ChatbotAllowedDomain> findByChatbotId(Long chatbotId);
}
