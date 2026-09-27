package com.thesis.crm.platform.service;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.TenantAdminDto;
import com.thesis.crm.platform.entity.SubscriptionPlan;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.platform.entity.TenantSubscription;
import com.thesis.crm.platform.entity.UsageRecord;
import com.thesis.crm.platform.repository.*;
import com.thesis.crm.security.TenantContextExecutor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class AdminTenantService {

    private static final Logger log = LoggerFactory.getLogger(AdminTenantService.class);

    private final TenantRepository tenantRepository;
    private final TenantSubscriptionRepository subscriptionRepository;
    private final SubscriptionPlanRepository planRepository;
    private final UserRepository userRepository;
    private final UsageRecordRepository usageRecordRepository;
    private final TenantContextExecutor tenantContextExecutor;

    public AdminTenantService(
            TenantRepository tenantRepository,
            TenantSubscriptionRepository subscriptionRepository,
            SubscriptionPlanRepository planRepository,
            UserRepository userRepository,
            UsageRecordRepository usageRecordRepository,
            TenantContextExecutor tenantContextExecutor
    ) {
        this.tenantRepository = tenantRepository;
        this.subscriptionRepository = subscriptionRepository;
        this.planRepository = planRepository;
        this.userRepository = userRepository;
        this.usageRecordRepository = usageRecordRepository;
        this.tenantContextExecutor = tenantContextExecutor;
    }

    @Transactional(readOnly = true)
    public PageResponse<TenantAdminDto> layDanhSachDoanhNghiep(
            String q,
            String status,
            String planCode,
            int page,
            int size
    ) {
        tenantContextExecutor.setPlatformAdminContext();
        Pageable pageable = PageRequest.of(Math.max(0, page), Math.max(1, size), Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Tenant> tenantsPage = tenantRepository.searchTenants(q, status, pageable);

        List<TenantAdminDto> items = new ArrayList<>();
        for (Tenant t : tenantsPage.getContent()) {
            TenantAdminDto dto = toTenantAdminDto(t);
            if (planCode == null || planCode.isBlank() || planCode.equalsIgnoreCase(dto.planCode())) {
                items.add(dto);
            }
        }

        return PageResponse.of(items, tenantsPage.getNumber(), tenantsPage.getSize(), tenantsPage.getTotalElements());
    }

    @Transactional
    public TenantAdminDto dinhChiDoanhNghiep(UUID tenantId, String reason) {
        tenantContextExecutor.setPlatformAdminContext();
        Tenant tenant = tenantRepository.findById(tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy doanh nghiệp.", HttpStatus.NOT_FOUND));

        tenant.setStatus("SUSPENDED");
        tenant.setSuspendedReason(reason != null ? reason.trim() : "Đình chỉ theo quyết định của quản trị viên nền tảng");
        tenant.setSuspendedAt(Instant.now());
        tenant.setUpdatedAt(Instant.now());

        Tenant saved = tenantRepository.save(tenant);
        log.warn("🚨 [PLATFORM ADMIN] Đã đình chỉ doanh nghiệp: id={} | name={} | reason={}",
                tenantId, saved.getName(), reason);

        return toTenantAdminDto(saved);
    }

    @Transactional
    public TenantAdminDto kichHoatDoanhNghiep(UUID tenantId) {
        tenantContextExecutor.setPlatformAdminContext();
        Tenant tenant = tenantRepository.findById(tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy doanh nghiệp.", HttpStatus.NOT_FOUND));

        tenant.setStatus("ACTIVE");
        tenant.setSuspendedReason(null);
        tenant.setSuspendedAt(null);
        tenant.setUpdatedAt(Instant.now());

        Tenant saved = tenantRepository.save(tenant);
        log.info("✅ [PLATFORM ADMIN] Đã kích hoạt lại doanh nghiệp: id={} | name={}",
                tenantId, saved.getName());

        return toTenantAdminDto(saved);
    }

    private TenantAdminDto toTenantAdminDto(Tenant t) {
        Optional<TenantSubscription> subOpt = subscriptionRepository.findFirstByTenantIdOrderByCreatedAtDesc(t.getId());

        String planCode = "TRIAL";
        String planName = "Dùng thử 14 ngày";
        long tokenUsed = 0L;
        long conversationCount = 0L;

        if (subOpt.isPresent()) {
            TenantSubscription sub = subOpt.get();
            Optional<SubscriptionPlan> planOpt = planRepository.findById(sub.getPlanId());
            if (planOpt.isPresent()) {
                planCode = planOpt.get().getCode();
                planName = planOpt.get().getName();
            }

            tokenUsed = usageRecordRepository.findBySubscriptionIdAndMetric(sub.getId(), "AI_TOKEN")
                    .map(UsageRecord::getUsedValue)
                    .orElse(0L);

            conversationCount = usageRecordRepository.findBySubscriptionIdAndMetric(sub.getId(), "CONVERSATION")
                    .map(UsageRecord::getUsedValue)
                    .orElse(0L);
        }

        long userCount = Math.max(1L, userRepository.countActiveUsersByTenantId(t.getId()));

        return new TenantAdminDto(
                t.getId(),
                t.getName(),
                t.getSlug(),
                t.getContactEmail(),
                t.getPhone(),
                t.getIndustry(),
                t.getStatus(),
                t.getSuspendedReason(),
                t.getSuspendedAt() != null ? t.getSuspendedAt().toString() : null,
                planCode,
                planName,
                userCount,
                conversationCount,
                tokenUsed,
                t.getCreatedAt()
        );
    }
}
