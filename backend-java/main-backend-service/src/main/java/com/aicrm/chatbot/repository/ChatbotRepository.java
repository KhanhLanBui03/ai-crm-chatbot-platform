package com.aicrm.chatbot.repository;

import com.aicrm.chatbot.entity.Chatbot;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ChatbotRepository extends JpaRepository<Chatbot, Long> {
    List<Chatbot> findByBusinessId(Long businessId);
    Optional<Chatbot> findByEmbedToken(String embedToken);
}
