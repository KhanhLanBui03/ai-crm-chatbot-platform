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

    /** UC006 — thuê bao trạng thái còn hiệu lực mới nhất, không xét hạn chu kỳ (cùng cách widget đếm hội thoại). */
    Optional<TenantSubscription> findFirstByTenantIdAndStatusInOrderByPeriodStartDesc(UUID tenantId,
            Collection<String> statuses);

    /**
     * UC006 — doanh nghiệp có chu kỳ đã hết hạn mà chưa đóng, cho job nền mở chu kỳ mới.
     *
     * <p>Native có chủ đích: job chạy ngoài mọi ngữ cảnh tenant nên RLS chặn sạch bảng này. Hàm
     * {@code SECURITY DEFINER} (V140) chỉ trả MÃ doanh nghiệp, không trả một cột dữ liệu nào.
     */
    @Query(value = "SELECT platform.tenants_with_expired_subscription(:now)", nativeQuery = true)
    List<UUID> tenantsWithExpiredSubscription(@Param("now") Instant now);

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
