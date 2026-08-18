package com.aicrm.document.repository;

import com.aicrm.document.entity.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findByChatbotId(Long chatbotId);
    List<Document> findByBusinessId(Long businessId);
}
