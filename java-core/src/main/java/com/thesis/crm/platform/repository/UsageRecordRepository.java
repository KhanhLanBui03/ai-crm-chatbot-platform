package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.UsageRecord;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface UsageRecordRepository extends JpaRepository<UsageRecord, UUID> {

    List<UsageRecord> findBySubscriptionId(UUID subscriptionId);

    Optional<UsageRecord> findBySubscriptionIdAndMetric(UUID subscriptionId, String metric);

    /**
     * Tạo dòng hạn mức của chu kỳ nếu chưa có. {@code quota_value} CHÉP từ gói hiện hành.
     *
     * <p>{@code used_value} ban đầu (ADR-0023 (d)): chỉ số tồn kho ({@code stock = true}) chép mức
     * đang có từ dòng cùng chỉ số của chu kỳ gần nhất TRƯỚC chu kỳ này — tài liệu không biến mất khi
     * sang tháng; chỉ số dòng chảy bắt đầu từ 0. {@code STORAGE_MB} đổi trần của gói từ MB sang
     * BYTE (ADR-0023 (c)).
     *
     * <p>Dòng thường đã có sẵn từ {@code register_tenant} (V118) hoặc lúc đổi gói; câu này là lưới
     * cho chu kỳ chưa có dòng. {@code ON CONFLICT DO NOTHING}: hai lượt đồng thời cùng chèn thì
     * lượt sau chờ lượt trước commit rồi bỏ qua, không nổ trùng khoá. Truy vấn con chạy dưới RLS
     * nên chỉ thấy chu kỳ của chính tenant.
     */
    @Modifying
    @Query(nativeQuery = true, value = """
            INSERT INTO platform.usage_records (tenant_id, subscription_id, metric, used_value, quota_value)
            SELECT s.tenant_id, s.id, :metric,
                   CASE WHEN :stock THEN COALESCE((
                            SELECT u.used_value
                              FROM platform.usage_records u
                              JOIN platform.tenant_subscriptions truoc ON truoc.id = u.subscription_id
                             WHERE u.metric = :metric
                               AND truoc.tenant_id = s.tenant_id
                               AND truoc.period_start < s.period_start
                             ORDER BY truoc.period_start DESC
                             LIMIT 1), 0)
                        ELSE 0
                   END,
                   CASE :metric
                       WHEN 'CONVERSATION' THEN p.conversation_quota
                       WHEN 'AI_TOKEN'     THEN p.ai_token_quota
                       WHEN 'DOCUMENT'     THEN p.max_documents
                       WHEN 'STORAGE_MB'   THEN p.storage_mb::bigint * 1048576
                       WHEN 'USER'         THEN p.max_users
                   END
              FROM platform.tenant_subscriptions s
              JOIN platform.subscription_plans p ON p.id = s.plan_id
             WHERE s.id = :subscriptionId
            ON CONFLICT (subscription_id, metric) DO NOTHING
            """)
    int insertIfAbsent(@Param("subscriptionId") UUID subscriptionId, @Param("metric") String metric,
            @Param("stock") boolean stock);

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
            @Param("metric") String metric);
}
