package com.thesis.crm.engagement.repository;

import com.thesis.crm.engagement.entity.Message;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/** Đọc/ghi {@link Message} qua JPA — mọi hàm tìm đều lọc {@code tenantId} (xem {@link ConversationRepository}). */
public interface MessageRepository extends JpaRepository<Message, UUID> {

    Optional<Message> findByIdAndTenantId(UUID id, UUID tenantId);

    /** Cả hội thoại theo thứ tự gửi — dùng cho tóm tắt (UC026) và xuất dữ liệu (UC041). */
    List<Message> findByTenantIdAndConversationIdOrderBySentAtAsc(UUID tenantId, UUID conversationId);
}
