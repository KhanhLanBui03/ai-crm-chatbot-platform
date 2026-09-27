package com.thesis.crm.platform.repository;

import com.thesis.crm.common.enums.SubscriptionStatus;
import com.thesis.crm.platform.entity.TenantSubscription;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/** Không lọc tenant — RLS lo (ADR-0001). */
@Repository
public interface TenantSubscriptionRepository extends JpaRepository<TenantSubscription, UUID> {

    /**
     * Các thuê bao đang hiệu lực tại {@code now}, mới nhất trước. {@code UNIQUE (tenant_id,
     * period_start)} không cấm hai chu kỳ chồng nhau, nên trả danh sách và lấy phần tử đầu thay vì
     * {@code Optional} — dữ liệu chồng chu kỳ không làm vỡ luồng tải lên.
     */
    @Query("""
            select s from TenantSubscription s
             where s.status in :statuses
               and s.periodStart <= :now and s.periodEnd > :now
             order by s.periodStart desc
            """)
    List<TenantSubscription> findEffective(@Param("statuses") Collection<SubscriptionStatus> statuses,
            @Param("now") Instant now);
}
