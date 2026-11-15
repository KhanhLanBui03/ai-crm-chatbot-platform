package com.thesis.crm.platform.service;

import com.thesis.crm.common.enums.UsageMetric;
import com.thesis.crm.platform.entity.SubscriptionPlan;
import com.thesis.crm.platform.entity.TenantSubscription;
import com.thesis.crm.platform.entity.UsageRecord;
import com.thesis.crm.platform.repository.SubscriptionPlanRepository;
import com.thesis.crm.platform.repository.TenantSubscriptionRepository;
import com.thesis.crm.platform.repository.UsageRecordRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC006 — vòng đời chu kỳ thuê bao: mở chu kỳ mới khi chu kỳ cũ hết hạn.
 *
 * <p>MỖI CHU KỲ LÀ MỘT DÒNG {@code tenant_subscriptions} MỚI, không sửa dòng cũ. Lược đồ V102 bày sẵn
 * như vậy: {@code UNIQUE (tenant_id, period_start)} cho phép nhiều chu kỳ một doanh nghiệp, và
 * {@code usage_records UNIQUE (subscription_id, metric)} buộc mỗi chu kỳ có bộ hạn mức riêng. Nhờ đó
 * hạn mức là ẢNH CHỤP của gói lúc mở chu kỳ (đặc tả UC006: "không đọc qua khoá gói") và hai mốc
 * {@code warned_at} / {@code blocked_at} của V128 tự về NULL mà không cần job nào dọn.
 *
 * <p>Sang chu kỳ mới, chỉ số <b>dòng chảy</b> (hội thoại, token) về 0 còn <b>tồn kho</b> (tài liệu,
 * dung lượng, người dùng) chép nguyên — tài liệu không biến mất khi sang tháng ({@link UsageMetric}).
 *
 * <p>Gói dùng thử KHÔNG tự lăn sang chu kỳ mới: hết hạn là {@code EXPIRED}, chờ quản trị viên chọn gói
 * trả phí ({@code changePlan} mở chu kỳ mới). Lăn tiếp là biến bản dùng thử 14 ngày thành miễn phí mãi.
 */
@Service
public class SubscriptionCycleService {

    private static final Logger log = LoggerFactory.getLogger(SubscriptionCycleService.class);

    /** Giá gói ghi theo tháng ({@code monthly_price_vnd}) nên chu kỳ trả phí là một tháng. */
    static final int SO_THANG_MOT_CHU_KY = 1;
    /** Doanh nghiệp bỏ quên nhiều tháng: lăn bù trong MỘT lượt, nhưng có trần để một dòng hỏng không thành vòng lặp vô tận. */
    static final int SO_CHU_KY_BU_TOI_DA = 24;
    /** Trạng thái còn sống — chỉ những dòng này mới được xét lăn chu kỳ. */
    static final List<String> CON_SONG = List.of("TRIALING", "ACTIVE", "PAST_DUE");

    private final TenantSubscriptionRepository thueBao;
    private final SubscriptionPlanRepository goi;
    private final UsageRecordRepository mucDung;

    public SubscriptionCycleService(TenantSubscriptionRepository thueBao, SubscriptionPlanRepository goi,
            UsageRecordRepository mucDung) {
        this.thueBao = thueBao;
        this.goi = goi;
        this.mucDung = mucDung;
    }

    /** Kết quả một lượt xử lý, để job nền ghi log và test đọc được. */
    public record KetQua(int soChuKyMoMoi, boolean daDongVanDungThu) {
        static final KetQua KHONG_LAM_GI = new KetQua(0, false);
    }

    /**
     * Lăn chu kỳ của MỘT doanh nghiệp cho tới khi chu kỳ hiện hành phủ {@code now}.
     *
     * <p>Phải gọi trong transaction đã đặt {@code app.tenant_id} (job nền làm việc đó).
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public KetQua lanChuKy(UUID tenantId, Instant now) {
        int moMoi = 0;
        boolean dongDungThu = false;
        for (int i = 0; i < SO_CHU_KY_BU_TOI_DA; i++) {
            Optional<TenantSubscription> het = thueBao
                    .findFirstByTenantIdAndStatusInOrderByPeriodStartDesc(tenantId, CON_SONG)
                    .filter(s -> !s.getPeriodEnd().isAfter(now));
            if (het.isEmpty()) {
                break;      // chu kỳ hiện hành còn hiệu lực, hoặc không còn dòng nào sống
            }
            TenantSubscription cu = het.get();
            // Dùng thử hết hạn, hoặc doanh nghiệp đã tắt tự gia hạn → đóng lại, không mở chu kỳ mới
            if ("TRIALING".equals(cu.getStatus()) || !cu.isAutoRenew()) {
                dongDungThu = "TRIALING".equals(cu.getStatus());
                dong(cu, now);
                break;
            }
            moChuKyTiep(cu, cu.getPeriodEnd(), now);
            moMoi++;
        }
        if (moMoi == SO_CHU_KY_BU_TOI_DA) {
            log.warn("Doanh nghiệp tenantId={} chạm trần {} chu kỳ lăn bù trong một lượt — lượt sau lăn tiếp",
                    tenantId, SO_CHU_KY_BU_TOI_DA);
        }
        return moMoi == 0 && !dongDungThu ? KetQua.KHONG_LAM_GI : new KetQua(moMoi, dongDungThu);
    }

    /**
     * Mở chu kỳ mới bắt đầu từ {@code batDau}, áp lịch hạ gói nếu đã tới hạn (đặc tả UC006 2.2 — hạ gói
     * chỉ hiệu lực từ chu kỳ sau). Đóng dòng cũ lại để mỗi doanh nghiệp chỉ có MỘT chu kỳ còn sống.
     *
     * @return dòng thuê bao của chu kỳ mới
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public TenantSubscription moChuKyTiep(TenantSubscription cu, Instant batDau, Instant now) {
        UUID goiMoi = cu.getScheduledPlanId() != null && cu.getScheduledEffectiveAt() != null
                && !cu.getScheduledEffectiveAt().isAfter(batDau)
                ? cu.getScheduledPlanId()
                : cu.getPlanId();
        SubscriptionPlan ke = goi.findById(goiMoi).orElseThrow(() ->
                new IllegalStateException("Gói " + goiMoi + " không còn — không mở được chu kỳ mới"));

        TenantSubscription moi = new TenantSubscription();
        moi.setTenantId(cu.getTenantId());
        moi.setPlanId(ke.getId());
        moi.setStatus("ACTIVE");
        moi.setPeriodStart(batDau);
        moi.setPeriodEnd(batDau.plus(SO_THANG_MOT_CHU_KY * 30L, ChronoUnit.DAYS));
        moi.setAutoRenew(cu.isAutoRenew());
        moi.setChangedBy(cu.getChangedBy());
        moi.setCreatedAt(now);
        moi.setUpdatedAt(now);
        TenantSubscription daLuu = thueBao.save(moi);

        chepHanMuc(cu, daLuu, ke, now);
        dong(cu, now);
        log.info("Doanh nghiệp tenantId={} mở chu kỳ mới {} → {}, gói {}", cu.getTenantId(),
                daLuu.getPeriodStart(), daLuu.getPeriodEnd(), ke.getCode());
        return daLuu;
    }

    /**
     * Dựng {@code usage_records} cho chu kỳ mới: hạn mức chụp từ gói, chỉ số dòng chảy về 0, chỉ số tồn
     * kho chép mức đang có của chu kỳ cũ (ADR-0023). Mốc 80% / 100% để trống — chu kỳ mới chưa chạm gì.
     */
    private void chepHanMuc(TenantSubscription cu, TenantSubscription moi, SubscriptionPlan ke, Instant now) {
        for (UsageMetric chiSo : UsageMetric.values()) {
            long tran = hanMucCuaGoi(ke, chiSo);
            UsageRecord dong = new UsageRecord(moi.getTenantId(), moi.getId(), chiSo.name(), tran);
            if (chiSo.isStock()) {
                mucDung.findBySubscriptionIdAndMetric(cu.getId(), chiSo.name())
                        .ifPresent(r -> dong.setUsedValue(r.getUsedValue()));
            }
            dong.setLastCalculatedAt(now);
            // Tồn kho chép sang có thể đã vượt trần của gói mới (hạ gói): ghi mốc ngay để màn nói đúng
            dong.ghiMocTheoMucDung(now);
            mucDung.save(dong);
        }
    }

    private static long hanMucCuaGoi(SubscriptionPlan p, UsageMetric chiSo) {
        return switch (chiSo) {
            case CONVERSATION -> p.getConversationQuota();
            case AI_TOKEN -> p.getAiTokenQuota();
            case DOCUMENT -> p.getMaxDocuments();
            case USER -> p.getMaxUsers();
            // storage_mb của gói ghi bằng MB, used_value đếm bằng BYTE (ADR-0023 (c))
            case STORAGE_MB -> p.getStorageMb() * 1024L * 1024L;
        };
    }

    private void dong(TenantSubscription s, Instant now) {
        s.setStatus("EXPIRED");
        s.setUpdatedAt(now);
        thueBao.save(s);
    }
}
