package com.thesis.crm.platform.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.util.Map;

/**
 * Hồ sơ doanh nghiệp (SCR007).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TenantProfileResponse(
        String name,
        String slug,
        String industry,
        String contactEmail,
        String phone,
        String timezone,
        String defaultLocale,
        Map<String, Object> businessHours,
        String aiTone,
        Integer leadScoreThreshold,
        Boolean autoLeadCreation,
        String assignmentMode,
        Map<String, Object> assignmentConfig,
        String status
) {}
