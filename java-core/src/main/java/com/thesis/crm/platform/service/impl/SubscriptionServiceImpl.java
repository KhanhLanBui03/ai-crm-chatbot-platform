package com.thesis.crm.platform.service.impl;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.platform.dto.request.ChangePlanRequest;
import com.thesis.crm.platform.dto.response.GoiDichVuResponse;
import com.thesis.crm.platform.dto.response.HanMucSuDungResponse;
import com.thesis.crm.platform.dto.response.MotHanMucDto;
import com.thesis.crm.platform.dto.response.ThueBaoResponse;
import com.thesis.crm.platform.entity.SubscriptionPlan;
import com.thesis.crm.platform.entity.TenantSubscription;
import com.thesis.crm.platform.entity.UsageRecord;
import com.thesis.crm.platform.repository.SubscriptionPlanRepository;
import com.thesis.crm.platform.repository.TenantSubscriptionRepository;
import com.thesis.crm.platform.repository.UsageRecordRepository;
import com.thesis.crm.platform.repository.UserRepository;
import com.thesis.crm.platform.service.SubscriptionService;
import com.thesis.crm.security.SecurityUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
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

    public SubscriptionServiceImpl(
            SubscriptionPlanRepository subscriptionPlanRepository,
            TenantSubscriptionRepository tenantSubscriptionRepository,
            UsageRecordRepository usageRecordRepository,
            UserRepository userRepository) {
        this.subscriptionPlanRepository = subscriptionPlanRepository;
        this.tenantSubscriptionRepository = tenantSubscriptionRepository;
        this.usageRecordRepository = usageRecordRepository;
        this.userRepository = userRepository;
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

        long usedConvs = getMetricUsage(sub.getId(), "CONVERSATION");
        long usedTokens = getMetricUsage(sub.getId(), "AI_TOKEN");
        long usedDocs = getMetricUsage(sub.getId(), "DOCUMENT");
        long usedUsers = Math.max(1L, userRepository.countActiveUsersByTenantId(tenantId));

        MotHanMucDto convs = MotHanMucDto.of(usedConvs, plan.getConversationQuota());
        MotHanMucDto tokens = MotHanMucDto.of(usedTokens, plan.getAiTokenQuota());
        MotHanMucDto users = MotHanMucDto.of(usedUsers, plan.getMaxUsers());
        MotHanMucDto docs = MotHanMucDto.of(usedDocs, plan.getMaxDocuments());

        boolean hasWarning = convs.percent() >= 80.0 || tokens.percent() >= 80.0 || users.percent() >= 80.0 || docs.percent() >= 80.0;
        boolean hasBlocked = convs.percent() >= 100.0 || tokens.percent() >= 100.0;

        String warnedAt = hasWarning ? Instant.now().toString() : null;
        String blockedAt = hasBlocked ? Instant.now().toString() : null;

        return new HanMucSuDungResponse(
                sub.getPeriodStart().toString(),
                sub.getPeriodEnd().toString(),
                convs,
                tokens,
                users,
                docs,
                0L,
                warnedAt,
                blockedAt
        );
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

    private long getMetricUsage(UUID subId, String metric) {
        return usageRecordRepository.findBySubscriptionIdAndMetric(subId, metric)
                .map(UsageRecord::getUsedValue)
                .orElse(0L);
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
