package com.aicrm.crm.conversation.repository;

import com.aicrm.crm.conversation.entity.Conversation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConversationRepository extends JpaRepository<Conversation, Long> {
    Optional<Conversation> findBySessionId(String sessionId);
    List<Conversation> findByChatbotId(Long chatbotId);
}
