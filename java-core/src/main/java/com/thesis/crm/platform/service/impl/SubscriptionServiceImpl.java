package com.thesis.crm.platform.service.impl;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.platform.dto.request.ChangePlanRequest;
import com.thesis.crm.platform.dto.response.GoiDichVuResponse;
import com.thesis.crm.platform.dto.response.HanMucSuDungResponse;
import com.thesis.crm.platform.dto.response.MotHanMucDto;
import com.thesis.crm.platform.dto.response.ThueBaoResponse;
import com.thesis.crm.platform.entity.SubscriptionPlan;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.platform.entity.TenantSubscription;
import com.thesis.crm.platform.entity.UsageRecord;
import com.thesis.crm.platform.repository.SubscriptionPlanRepository;
import com.thesis.crm.platform.repository.TenantSubscriptionRepository;
import com.thesis.crm.platform.repository.UsageRecordRepository;
import com.thesis.crm.platform.repository.UserRepository;
import com.thesis.crm.platform.service.SubscriptionService;
import com.thesis.crm.security.SecurityUtils;
import jakarta.persistence.EntityManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class SubscriptionServiceImpl implements SubscriptionService {

    private static final Logger log = LoggerFactory.getLogger(SubscriptionServiceImpl.class);

    private final SubscriptionPlanRepository subscriptionPlanRepository;
    private final TenantSubscriptionRepository tenantSubscriptionRepository;
    private final UsageRecordRepository usageRecordRepository;
    private final UserRepository userRepository;
    private final EntityManager em;

    public SubscriptionServiceImpl(
            SubscriptionPlanRepository subscriptionPlanRepository,
            TenantSubscriptionRepository tenantSubscriptionRepository,
            UsageRecordRepository usageRecordRepository,
            UserRepository userRepository,
            EntityManager em) {
        this.subscriptionPlanRepository = subscriptionPlanRepository;
        this.tenantSubscriptionRepository = tenantSubscriptionRepository;
        this.usageRecordRepository = usageRecordRepository;
        this.userRepository = userRepository;
        this.em = em;
    }

    @Override
    @Transactional(readOnly = true)
    public List<GoiDichVuResponse> getPlans() {
        UUID tenantId = SecurityUtils.getCurrentTenantId();
        UUID currentPlanId = null;
        if (tenantId != null) {
            Optional<TenantSubscription> subOpt = tenantSubscriptionRepository.findFirstByTenantIdOrderByCreatedAtDesc(tenantId);
            if (subOpt.isPresent()) {
                currentPlanId = subOpt.get().getPlanId();
            }
        }

        UUID finalCurrentPlanId = currentPlanId;
        List<SubscriptionPlan> plans = subscriptionPlanRepository.findAllByIsActiveTrueOrderBySortOrderAsc();

        return plans.stream()
                .map(p -> toGoiDichVu(p, finalCurrentPlanId != null && finalCurrentPlanId.equals(p.getId())))
                .toList();
    }

    @Override
    @Transactional
    public ThueBaoResponse getCurrentSubscription() {
        UUID tenantId = requireCurrentTenantId();
        TenantSubscription sub = getOrCreateSubscription(tenantId);

        SubscriptionPlan plan = subscriptionPlanRepository.findById(sub.getPlanId())
                .orElseThrow(() -> new AppException("Không tìm thấy gói dịch vụ tương ứng.", HttpStatus.NOT_FOUND));

        SubscriptionPlan scheduledPlan = null;
        if (sub.getScheduledPlanId() != null) {
            scheduledPlan = subscriptionPlanRepository.findById(sub.getScheduledPlanId()).orElse(null);
        }

        return toThueBaoResponse(sub, plan, scheduledPlan);
    }

    @Override
    @Transactional
    public ThueBaoResponse changePlan(ChangePlanRequest request) {
        if (!SecurityUtils.isTenantAdmin()) {
            throw new AppException("Chỉ quản trị viên doanh nghiệp mới có quyền đổi gói dịch vụ.", HttpStatus.FORBIDDEN);
        }

        UUID tenantId = requireCurrentTenantId();
        String targetCode = request.planCode() != null ? request.planCode().trim().toUpperCase() : "";

        SubscriptionPlan targetPlan = subscriptionPlanRepository.findByCode(targetCode)
                .orElseThrow(() -> new AppException("Mã gói dịch vụ không tồn tại: " + targetCode, HttpStatus.BAD_REQUEST));

        TenantSubscription sub = getOrCreateSubscription(tenantId);
        SubscriptionPlan currentPlan = subscriptionPlanRepository.findById(sub.getPlanId())
                .orElseThrow(() -> new AppException("Gói hiện tại không hợp lệ.", HttpStatus.INTERNAL_SERVER_ERROR));

        UUID userId = SecurityUtils.getCurrentUserId();

        if (targetPlan.getSortOrder() > currentPlan.getSortOrder() || "TRIALING".equalsIgnoreCase(sub.getStatus())) {
            // Nâng gói (Upgrade) -> Có hiệu lực ngay lập tức
            sub.setPlanId(targetPlan.getId());
            sub.setScheduledPlanId(null);
            sub.setScheduledEffectiveAt(null);
            sub.setStatus("ACTIVE");
            sub.setChangedBy(userId);
            sub.setUpdatedAt(Instant.now());
            tenantSubscriptionRepository.save(sub);

            // Đồng bộ định mức mới vào usage_records
            syncUsageRecordQuotas(tenantId, sub.getId(), targetPlan);

            log.info("Doanh nghiệp tenantId={} nâng cấp lên gói {} thành công", tenantId, targetPlan.getCode());
            return toThueBaoResponse(sub, targetPlan, null);
        } else if (targetPlan.getSortOrder() < currentPlan.getSortOrder()) {
            // Hạ gói (Downgrade) -> Đặt lịch cuối chu kỳ
            sub.setScheduledPlanId(targetPlan.getId());
            sub.setScheduledEffectiveAt(sub.getPeriodEnd());
            sub.setChangedBy(userId);
            sub.setUpdatedAt(Instant.now());
            tenantSubscriptionRepository.save(sub);

            log.info("Doanh nghiệp tenantId={} đặt lịch hạ gói xuống {} từ {}", tenantId, targetPlan.getCode(), sub.getPeriodEnd());
            return toThueBaoResponse(sub, currentPlan, targetPlan);
        } else {
            // Chọn lại gói hiện tại -> Hủy lịch hạ gói nếu có
            if (sub.getScheduledPlanId() != null) {
                sub.setScheduledPlanId(null);
                sub.setScheduledEffectiveAt(null);
                sub.setUpdatedAt(Instant.now());
                tenantSubscriptionRepository.save(sub);
            }
            return toThueBaoResponse(sub, currentPlan, null);
        }
    }

    @Override
    @Transactional
    public HanMucSuDungResponse getCurrentUsage() {
        UUID tenantId = requireCurrentTenantId();
        TenantSubscription sub = getOrCreateSubscription(tenantId);
        SubscriptionPlan plan = subscriptionPlanRepository.findById(sub.getPlanId())
                .orElseThrow(() -> new AppException("Không tìm thấy thông tin gói dịch vụ.", HttpStatus.NOT_FOUND));

        // Hạn mức đọc từ ẢNH CHỤP của chu kỳ (usage_records.quota_value), không đọc qua gói hiện tại: đổi gói
        // giữa chừng mà đọc qua plan_id thì báo cáo chu kỳ cũ sai ngay (đặc tả UC006). Chưa có dòng thì lấy gói.
        MotHanMucDto convs = mucCua(sub.getId(), "CONVERSATION", null, plan.getConversationQuota());
        MotHanMucDto tokens = mucCua(sub.getId(), "AI_TOKEN", null, plan.getAiTokenQuota());
        // Người dùng là TỒN KHO đếm tức thời — số đang hoạt động, mốc vẫn lấy từ dòng hạn mức
        MotHanMucDto users = mucCua(sub.getId(), "USER",
                Math.max(1L, userRepository.countActiveUsersByTenantId(tenantId)), plan.getMaxUsers());
        MotHanMucDto docs = mucCua(sub.getId(), "DOCUMENT", null, plan.getMaxDocuments());

        // Mốc THẬT đã ghi trong chu kỳ (V128) — trước đây trả Instant.now() mỗi lần mở màn, tức "thời điểm
        // chạm 80%" đổi theo lúc người xem bấm vào.
        Instant warnedAt = somNhat(convs.warnedAt(), tokens.warnedAt(), users.warnedAt(), docs.warnedAt());
        Instant blockedAt = somNhat(convs.blockedAt(), tokens.blockedAt());

        return new HanMucSuDungResponse(
                sub.getPeriodStart().toString(),
                sub.getPeriodEnd().toString(),
                convs,
                tokens,
                users,
                docs,
                chiPhiAiTuDauChuKy(tenantId, sub.getPeriodStart()),
                warnedAt,
                blockedAt
        );
    }

    private MotHanMucDto mucCua(UUID subId, String metric, Long dungTucThoi, long quotaGoi) {
        Optional<UsageRecord> r = usageRecordRepository.findBySubscriptionIdAndMetric(subId, metric);
        long used = dungTucThoi != null ? dungTucThoi : r.map(UsageRecord::getUsedValue).orElse(0L);
        long quota = r.map(UsageRecord::getQuotaValue).orElse(quotaGoi);
        return MotHanMucDto.of(used, quota, r.map(UsageRecord::getWarnedAt).orElse(null),
                r.map(UsageRecord::getBlockedAt).orElse(null));
    }

    private static Instant somNhat(Instant... cac) {
        Instant kq = null;
        for (Instant i : cac) {
            if (i != null && (kq == null || i.isBefore(kq))) {
                kq = i;
            }
        }
        return kq;
    }

    /**
     * Chi phí AI từ ngày mở chu kỳ (theo múi giờ doanh nghiệp) tới nay — cộng từ mô hình đọc theo ngày mà
     * consumer {@code ai.turn.completed} đã dựng (UC039). Đặc tả bước 3 ghi "gọi sang ai-service"; người dùng
     * chốt 08/11/2026 dùng đường sự kiện vì chính đặc tả yêu cầu token đi qua sự kiện, và hai nguồn số dễ lệch.
     * Độ phân giải là NGÀY: lượt trước giờ mở chu kỳ trong cùng ngày đầu cũng được tính.
     */
    private BigDecimal chiPhiAiTuDauChuKy(UUID tenantId, Instant batDau) {
        LocalDate tu = batDau.atZone(muiGio(tenantId)).toLocalDate();
        BigDecimal tong = em.createQuery("""
                        SELECT coalesce(sum(m.costVnd), 0) FROM MetricsDaily m
                        WHERE m.tenantId = :t AND m.metricDate >= :tu""", BigDecimal.class)
                .setParameter("t", tenantId)
                .setParameter("tu", tu)
                .getSingleResult();
        return tong == null ? BigDecimal.ZERO : tong;
    }

    private ZoneId muiGio(UUID tenantId) {
        Tenant t = em.find(Tenant.class, tenantId);
        try {
            return ZoneId.of(t == null || t.getTimezone() == null ? "Asia/Ho_Chi_Minh" : t.getTimezone());
        } catch (Exception e) {
            return ZoneId.of("Asia/Ho_Chi_Minh");
        }
    }

    private TenantSubscription getOrCreateSubscription(UUID tenantId) {
        return tenantSubscriptionRepository.findFirstByTenantIdOrderByCreatedAtDesc(tenantId)
                .orElseGet(() -> {
                    SubscriptionPlan trial = subscriptionPlanRepository.findByCode("TRIAL")
                            .orElseGet(() -> {
                                List<SubscriptionPlan> all = subscriptionPlanRepository.findAllByIsActiveTrueOrderBySortOrderAsc();
                                return all.isEmpty() ? null : all.get(0);
                            });

                    if (trial == null) {
                        throw new AppException("Chưa cấu hình gói dịch vụ mẫu trong hệ thống.", HttpStatus.INTERNAL_SERVER_ERROR);
                    }

                    TenantSubscription newSub = new TenantSubscription();
                    newSub.setTenantId(tenantId);
                    newSub.setPlanId(trial.getId());
                    newSub.setStatus("TRIALING");
                    newSub.setPeriodStart(Instant.now());
                    newSub.setPeriodEnd(Instant.now().plus(Duration.ofDays(14)));
                    newSub.setAutoRenew(true);
                    TenantSubscription saved = tenantSubscriptionRepository.save(newSub);

                    syncUsageRecordQuotas(tenantId, saved.getId(), trial);
                    return saved;
                });
    }

    private void syncUsageRecordQuotas(UUID tenantId, UUID subId, SubscriptionPlan plan) {
        upsertUsageQuota(tenantId, subId, "CONVERSATION", plan.getConversationQuota());
        upsertUsageQuota(tenantId, subId, "AI_TOKEN", plan.getAiTokenQuota());
        upsertUsageQuota(tenantId, subId, "USER", plan.getMaxUsers());
        upsertUsageQuota(tenantId, subId, "DOCUMENT", plan.getMaxDocuments());
    }

    private void upsertUsageQuota(UUID tenantId, UUID subId, String metric, long quotaValue) {
        UsageRecord record = usageRecordRepository.findBySubscriptionIdAndMetric(subId, metric)
                .orElseGet(() -> new UsageRecord(tenantId, subId, metric, quotaValue));
        record.setQuotaValue(quotaValue);
        record.setUpdatedAt(Instant.now());
        usageRecordRepository.save(record);
    }

    private UUID requireCurrentTenantId() {
        UUID tenantId = SecurityUtils.getCurrentTenantId();
        if (tenantId == null) {
            throw new AppException("Phiên làm việc không hợp lệ hoặc thiếu mã doanh nghiệp.", HttpStatus.UNAUTHORIZED);
        }
        return tenantId;
    }

    private GoiDichVuResponse toGoiDichVu(SubscriptionPlan p, boolean isCurrent) {
        return new GoiDichVuResponse(
                p.getCode(),
                p.getName(),
                p.getMonthlyPriceVnd(),
                p.getConversationQuota(),
                p.getAiTokenQuota(),
                p.getMaxUsers(),
                p.getMaxDocuments(),
                p.getMaxChannels(),
                p.getSortOrder(),
                isCurrent
        );
    }

    private ThueBaoResponse toThueBaoResponse(TenantSubscription sub, SubscriptionPlan plan, SubscriptionPlan scheduledPlan) {
        boolean readOnly = "PAST_DUE".equalsIgnoreCase(sub.getStatus()) || "EXPIRED".equalsIgnoreCase(sub.getStatus());
        return new ThueBaoResponse(
                sub.getStatus(),
                toGoiDichVu(plan, true),
                sub.getPeriodStart().toString(),
                sub.getPeriodEnd().toString(),
                scheduledPlan != null ? toGoiDichVu(scheduledPlan, false) : null,
                sub.getScheduledEffectiveAt() != null ? sub.getScheduledEffectiveAt().toString() : null,
                readOnly
        );
    }
}
