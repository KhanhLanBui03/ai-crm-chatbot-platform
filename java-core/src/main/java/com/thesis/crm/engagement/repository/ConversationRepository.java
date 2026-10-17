package com.thesis.crm.engagement.repository;

import com.thesis.crm.engagement.entity.Conversation;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * Đọc/ghi {@link Conversation} qua JPA. Mọi hàm tìm đều nhận {@code tenantId} — lọc tường minh trong
 * câu truy vấn, ngoài lớp RLS ở CSDL. Đừng dùng {@code findById(id)} trần cho dữ liệu theo yêu cầu người
 * dùng: thiếu {@code TenantTransactionScope.apply()} thì RLS là lớp chặn duy nhất còn lại.
 */
public interface ConversationRepository extends JpaRepository<Conversation, UUID> {

    Optional<Conversation> findByIdAndTenantId(UUID id, UUID tenantId);
}
