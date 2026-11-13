package com.thesis.crm.platform.scheduler;

import com.thesis.crm.platform.repository.TenantSubscriptionRepository;
import com.thesis.crm.platform.service.SubscriptionCycleService;
import com.thesis.crm.platform.service.SubscriptionCycleService.KetQua;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Instant;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * UC006 — mở chu kỳ thuê bao mới khi chu kỳ cũ hết hạn (đặc tả 2.2: hạ gói hiệu lực từ chu kỳ sau).
 *
 * <p>Job không có ngữ cảnh tenant: lấy danh sách doanh nghiệp qua hàm SECURITY DEFINER chỉ trả ID
 * (V140), rồi mỗi doanh nghiệp một transaction có {@code app.tenant_id} — RLS vẫn áp như mọi truy vấn
 * khác. Cùng khuôn {@code HandoffWatchdog}.
 *
 * <p>Nhịp 10 phút là đủ: ranh giới chu kỳ tính theo ngày, trễ vài phút không ai thấy. Một doanh nghiệp
 * hỏng không chặn doanh nghiệp còn lại — mỗi bên một transaction riêng.
 */
@Component
public class SubscriptionCycleScheduler {

    private static final Logger log = LoggerFactory.getLogger(SubscriptionCycleScheduler.class);

    private final TenantSubscriptionRepository thueBao;
    private final SubscriptionCycleService chuKy;
    private final TenantTransactionScope scope;
    private final TransactionTemplate tx;
    private final boolean enabled;

    public SubscriptionCycleScheduler(TenantSubscriptionRepository thueBao, SubscriptionCycleService chuKy,
            TenantTransactionScope scope, TransactionTemplate tx,
            @Value("${subscription.cycle.enabled:true}") boolean enabled) {
        this.thueBao = thueBao;
        this.chuKy = chuKy;
        this.scope = scope;
        this.tx = tx;
        this.enabled = enabled;
    }

    @Scheduled(fixedDelay = 600_000, initialDelay = 30_000)
    public void scheduled() {
        if (!enabled) {
            return;   // test tắt lịch và gọi runOnce() trực tiếp để kết quả xác định
        }
        try {
            runOnce(Instant.now());
        } catch (RuntimeException e) {
            log.warn("Job chu kỳ thuê bao lỗi, lần sau chạy lại: {}", e.toString());
        }
    }

    public int runOnce(Instant now) {
        int xong = 0;
        for (UUID tenantId : thueBao.tenantsWithExpiredSubscription(now)) {
            try {
                KetQua kq = tx.execute(st -> {
                    scope.apply(tenantId);
                    return chuKy.lanChuKy(tenantId, now);
                });
                if (kq != null && (kq.soChuKyMoMoi() > 0 || kq.daDongVanDungThu())) {
                    xong++;
                }
            } catch (RuntimeException e) {
                // Một doanh nghiệp hỏng (gói đã gỡ, đụng ràng buộc chu kỳ trùng) không được chặn phần còn lại
                log.warn("Không lăn được chu kỳ của tenantId={}: {}", tenantId, e.toString());
            }
        }
        return xong;
    }
}
