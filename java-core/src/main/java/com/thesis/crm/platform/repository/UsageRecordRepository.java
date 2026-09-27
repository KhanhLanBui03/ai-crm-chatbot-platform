package com.thesis.crm.platform.repository;

import com.thesis.crm.common.enums.UsageMetric;
import com.thesis.crm.platform.entity.UsageRecord;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/** Không lọc tenant — RLS lo (ADR-0001). */
@Repository
public interface UsageRecordRepository extends JpaRepository<UsageRecord, UUID> {

    /**
     * Tạo dòng hạn mức của chu kỳ nếu chưa có, {@code quota_value} CHÉP từ gói.
     *
     * <p>Lẽ ra dòng này sinh lúc mở chu kỳ (UC005) — luồng đó chưa có, nên người tiêu thụ đầu
     * tiên tạo. {@code ON CONFLICT DO NOTHING}: hai lượt đồng thời cùng chèn thì lượt sau chờ
     * lượt trước commit rồi bỏ qua, không nổ trùng khoá.
     */
    @Modifying
    @Query(nativeQuery = true, value = """
            INSERT INTO platform.usage_records (tenant_id, subscription_id, metric, used_value, quota_value)
            SELECT s.tenant_id, s.id, :metric, 0,
                   CASE :metric
                       WHEN 'CONVERSATION' THEN p.conversation_quota
                       WHEN 'AI_TOKEN'     THEN p.ai_token_quota
                       WHEN 'DOCUMENT'     THEN p.max_documents
                       WHEN 'STORAGE_MB'   THEN p.storage_mb
                       WHEN 'USER'         THEN p.max_users
                   END
              FROM platform.tenant_subscriptions s
              JOIN platform.subscription_plans p ON p.id = s.plan_id
             WHERE s.id = :subscriptionId
            ON CONFLICT (subscription_id, metric) DO NOTHING
            """)
    int insertIfAbsent(@Param("subscriptionId") UUID subscriptionId, @Param("metric") String metric);

    /**
     * Đọc VÀ KHOÁ dòng hạn mức tới hết transaction ({@code SELECT … FOR NO KEY UPDATE}).
     *
     * <p>Không có khoá này thì hai lượt tải đồng thời lúc {@code used = quota − 1} cùng đọc thấy
     * còn chỗ, cùng được nhận, và hạn mức bị vượt. Lượt thứ hai CHỜ ở đây tới khi lượt đầu commit
     * rồi đọc lại giá trị mới (READ COMMITTED).
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select u from UsageRecord u where u.subscriptionId = :subscriptionId and u.metric = :metric")
    Optional<UsageRecord> findForUpdate(@Param("subscriptionId") UUID subscriptionId,
            @Param("metric") UsageMetric metric);
}
