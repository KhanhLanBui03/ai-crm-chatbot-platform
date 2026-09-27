package com.thesis.crm.platform.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.platform.dto.request.UpdateTenantProfileRequest;
import com.thesis.crm.platform.dto.response.TenantProfileResponse;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.platform.repository.TenantRepository;
import com.thesis.crm.platform.service.TenantService;
import com.thesis.crm.security.SecurityUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class TenantServiceImpl implements TenantService {

    private static final Logger log = LoggerFactory.getLogger(TenantServiceImpl.class);
    private static final Set<String> HOP_LE_AI_TONE = Set.of("PROFESSIONAL", "FRIENDLY", "CONCISE");
    private static final Set<String> HOP_LE_ASSIGNMENT_MODE = Set.of("ROUND_ROBIN", "LEAST_BUSY", "MANUAL");

    private final TenantRepository tenantRepository;
    private final ObjectMapper objectMapper;

    public TenantServiceImpl(TenantRepository tenantRepository, ObjectMapper objectMapper) {
        this.tenantRepository = tenantRepository;
        this.objectMapper = objectMapper;
    }

    @Override
    @Transactional(readOnly = true)
    public TenantProfileResponse getProfile() {
        UUID tenantId = SecurityUtils.getCurrentTenantId();
        if (tenantId == null) {
            throw new AppException("Phiên đăng nhập không hợp lệ hoặc thiếu mã doanh nghiệp.", HttpStatus.UNAUTHORIZED);
        }

        Tenant tenant = tenantRepository.findById(tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy doanh nghiệp trong hệ thống.", HttpStatus.NOT_FOUND));

        return toResponse(tenant);
    }

    @Override
    @Transactional
    public TenantProfileResponse updateProfile(UpdateTenantProfileRequest request) {
        if (!SecurityUtils.isTenantAdmin()) {
            throw new AppException("Chỉ quản trị viên doanh nghiệp mới có quyền cập nhật hồ sơ doanh nghiệp.", HttpStatus.FORBIDDEN);
        }

        UUID tenantId = SecurityUtils.getCurrentTenantId();
        if (tenantId == null) {
            throw new AppException("Phiên đăng nhập không hợp lệ hoặc thiếu mã doanh nghiệp.", HttpStatus.UNAUTHORIZED);
        }

        Tenant tenant = tenantRepository.findById(tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy doanh nghiệp trong hệ thống.", HttpStatus.NOT_FOUND));

        if (request.name() != null && !request.name().isBlank()) {
            tenant.setName(request.name().trim());
        }

        if (request.industry() != null) {
            tenant.setIndustry(request.industry().trim().isEmpty() ? null : request.industry().trim());
        }

        if (request.contactEmail() != null && !request.contactEmail().isBlank()) {
            tenant.setContactEmail(request.contactEmail().trim().toLowerCase());
        }

        if (request.phone() != null) {
            tenant.setPhone(request.phone().trim().isEmpty() ? null : request.phone().trim());
        }

        if (request.timezone() != null && !request.timezone().isBlank()) {
            tenant.setTimezone(request.timezone().trim());
        }

        if (request.defaultLocale() != null && !request.defaultLocale().isBlank()) {
            tenant.setLocale(request.defaultLocale().trim());
        }

        if (request.aiTone() != null && !request.aiTone().isBlank()) {
            String tone = request.aiTone().trim().toUpperCase();
            if (!HOP_LE_AI_TONE.contains(tone)) {
                throw new AppException("Giọng điệu AI không hợp lệ. Chọn PROFESSIONAL, FRIENDLY hoặc CONCISE.", HttpStatus.BAD_REQUEST);
            }
            tenant.setAiTone(tone);
        }

        if (request.leadScoreThreshold() != null) {
            tenant.setLeadScoreThreshold(request.leadScoreThreshold().shortValue());
        }

        if (request.autoLeadCreation() != null) {
            tenant.setAutoLeadCreation(request.autoLeadCreation());
        }

        if (request.assignmentMode() != null && !request.assignmentMode().isBlank()) {
            String mode = request.assignmentMode().trim().toUpperCase();
            if (!HOP_LE_ASSIGNMENT_MODE.contains(mode)) {
                throw new AppException("Chế độ phân công không hợp lệ. Chọn ROUND_ROBIN, LEAST_BUSY hoặc MANUAL.", HttpStatus.BAD_REQUEST);
            }
            tenant.setAssignmentMode(mode);
        }

        if (request.businessHours() != null) {
            try {
                tenant.setBusinessHours(objectMapper.writeValueAsString(request.businessHours()));
            } catch (Exception e) {
                log.warn("Lỗi serialize businessHours: {}", e.getMessage());
            }
        }

        if (request.assignmentConfig() != null) {
            try {
                tenant.setAssignmentConfig(objectMapper.writeValueAsString(request.assignmentConfig()));
            } catch (Exception e) {
                log.warn("Lỗi serialize assignmentConfig: {}", e.getMessage());
            }
        }

        tenant.setUpdatedAt(Instant.now());
        Tenant saved = tenantRepository.save(tenant);

        log.info("Đã cập nhật hồ sơ doanh nghiệp id={}, name={}", saved.getId(), saved.getName());
        return toResponse(saved);
    }

    private TenantProfileResponse toResponse(Tenant tenant) {
        Map<String, Object> businessHours = parseJsonMap(tenant.getBusinessHours());
        Map<String, Object> assignmentConfig = parseJsonMap(tenant.getAssignmentConfig());

        return new TenantProfileResponse(
                tenant.getName(),
                tenant.getSlug(),
                tenant.getIndustry(),
                tenant.getContactEmail(),
                tenant.getPhone(),
                tenant.getTimezone(),
                tenant.getLocale(),
                businessHours,
                tenant.getAiTone(),
                (int) tenant.getLeadScoreThreshold(),
                tenant.isAutoLeadCreation(),
                tenant.getAssignmentMode(),
                assignmentConfig,
                tenant.getStatus()
        );
    }

    private Map<String, Object> parseJsonMap(String json) {
        if (json == null || json.isBlank() || json.equals("{}")) {
            return Collections.emptyMap();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            log.warn("Không thể parse json: {}", json);
            return Collections.emptyMap();
        }
    }
}
