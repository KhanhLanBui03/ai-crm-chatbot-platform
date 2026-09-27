package com.thesis.crm.platform.service.impl;

import com.thesis.crm.common.enums.SubscriptionStatus;
import com.thesis.crm.common.enums.UsageMetric;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.exception.QuotaExceededException;
import com.thesis.crm.platform.dto.response.QuotaUsageResponse;
import com.thesis.crm.platform.entity.TenantSubscription;
import com.thesis.crm.platform.entity.UsageRecord;
import com.thesis.crm.platform.repository.TenantSubscriptionRepository;
import com.thesis.crm.platform.repository.UsageRecordRepository;
import com.thesis.crm.platform.service.UsageQuotaService;
import java.time.Instant;
import java.util.EnumSet;
import java.util.Set;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Cài đặt hạn mức. Mốc 80% và 100% ghi MỘT LẦN mỗi chu kỳ (V116) — đó là "thời điểm chạm mốc"
 * UC006 4.1–4.2 hiển thị, nên không ghi đè khi các lượt sau vẫn ở trên ngưỡng.
 */
@Service
public class UsageQuotaServiceImpl implements UsageQuotaService {

    /** UC006 "Tham số và ngưỡng": cảnh báo 80%, chặn 100%. */
    static final int NGUONG_CANH_BAO_PHAN_TRAM = 80;

    /** Chỉ hai trạng thái này được tiêu thụ; PAST_DUE/EXPIRED là chế độ chỉ đọc. */
    private static final Set<SubscriptionStatus> DUOC_TIEU_THU =
            EnumSet.of(SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE);

    private final TenantSubscriptionRepository subscriptions;
    private final UsageRecordRepository usageRecords;

    public UsageQuotaServiceImpl(TenantSubscriptionRepository subscriptions,
            UsageRecordRepository usageRecords) {
        this.subscriptions = subscriptions;
        this.usageRecords = usageRecords;
    }

    /**
     * {@code noRollbackFor}: lúc từ chối có thể vừa ghi {@code blocked_at} (gói bị hạ giữa chu kỳ
     * nên dòng chưa từng chạm 100% theo quota mới). Không khai thì Spring đánh dấu transaction
     * chung là rollback-only ngay khi ngoại lệ đi qua đây, dù phía gọi có khai hay không.
     */
    @Override
    @Transactional(propagation = Propagation.MANDATORY, noRollbackFor = QuotaExceededException.class)
    public UsageRecord lockForConsumption(UsageMetric metric) {
        Instant now = Instant.now();
        TenantSubscription thueBao = subscriptions.findEffective(DUOC_TIEU_THU, now).stream()
                .findFirst()
                .orElseThrow(() -> new BusinessException(HttpStatus.CONFLICT, "SUBSCRIPTION_NOT_ACTIVE",
                        "Doanh nghiệp chưa có gói dịch vụ đang hiệu lực. Hãy gia hạn hoặc chọn gói."));

        usageRecords.insertIfAbsent(thueBao.getId(), metric.name());
        UsageRecord dong = usageRecords.findForUpdate(thueBao.getId(), metric)
                .orElseThrow(() -> new IllegalStateException(
                        "Không đọc lại được dòng hạn mức vừa tạo — RLS hoặc app.tenant_id sai"));

        if (dong.getUsedValue() >= dong.getQuotaValue()) {
            ghiMocNeuTrong(dong, now);
            throw new QuotaExceededException(metric, thongDiepHetHanMuc(metric, dong),
                    QuotaUsageResponse.from(dong));
        }
        return dong;
    }

    @Override
    @Transactional(propagation = Propagation.MANDATORY)
    public QuotaUsageResponse consume(UsageRecord locked, long amount) {
        Instant now = Instant.now();
        locked.setUsedValue(locked.getUsedValue() + amount);
        locked.setLastCalculatedAt(now);
        ghiMocNeuTrong(locked, now);
        return QuotaUsageResponse.from(locked);
    }

    /**
     * Ghi mốc theo mức dùng HIỆN TẠI của dòng. Thứ tự 80% rồi 100% là bắt buộc: ràng buộc
     * {@code ck_usage_moc_theo_thu_tu} (V116) từ chối dòng có {@code blocked_at} mà thiếu
     * {@code warned_at}. Nhân chéo thay vì chia để khỏi sai số dấu phẩy động ở đúng ngưỡng.
     */
    private static void ghiMocNeuTrong(UsageRecord r, Instant now) {
        long used = r.getUsedValue();
        long quota = r.getQuotaValue();
        if (r.getWarnedAt() == null && used * 100 >= quota * NGUONG_CANH_BAO_PHAN_TRAM) {
            r.setWarnedAt(now);
        }
        if (r.getBlockedAt() == null && used >= quota) {
            r.setBlockedAt(now);
        }
    }

    private static String thongDiepHetHanMuc(UsageMetric metric, UsageRecord r) {
        if (metric == UsageMetric.DOCUMENT) {
            return "Đã dùng " + r.getUsedValue() + "/" + r.getQuotaValue()
                    + " tài liệu của gói. Hãy gỡ bớt tài liệu cũ hoặc nâng gói dịch vụ.";
        }
        return "Đã chạm hạn mức " + metric.name() + " của gói (" + r.getUsedValue() + "/"
                + r.getQuotaValue() + ").";
    }
}
