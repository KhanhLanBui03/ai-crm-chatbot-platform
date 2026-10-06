package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.TenantSubscription;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface TenantSubscriptionRepository extends JpaRepository<TenantSubscription, UUID> {

    Optional<TenantSubscription> findFirstByTenantIdOrderByCreatedAtDesc(UUID tenantId);

    /**
     * Các thuê bao của {@code tenantId} đang hiệu lực tại {@code now}, mới nhất trước — UC018 tiêu
     * thụ hạn mức. {@code UNIQUE (tenant_id, period_start)} không cấm hai chu kỳ chồng nhau, nên trả
     * danh sách và lấy phần tử đầu thay vì {@code Optional}.
     *
     * <p>Lọc {@code tenantId} ngay trong truy vấn dù RLS đã lọc: một kết nối mang cờ
     * {@code app.is_platform_admin} sót từ request trước thì RLS cho thấy mọi tenant, và luồng tải
     * lên sẽ tiêu thụ hạn mức của thuê bao người khác.
     */
    @Query("""
            select s from TenantSubscription s
             where s.tenantId = :tenantId
               and s.status in :statuses
               and s.periodStart <= :now and s.periodEnd > :now
             order by s.periodStart desc
            """)
    List<TenantSubscription> findEffective(@Param("tenantId") UUID tenantId,
            @Param("statuses") Collection<String> statuses, @Param("now") Instant now);
}
