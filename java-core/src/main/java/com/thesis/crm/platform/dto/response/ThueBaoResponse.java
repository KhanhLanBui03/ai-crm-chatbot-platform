package com.thesis.crm.platform.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * Thuê bao hiện tại của doanh nghiệp (SCR012).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ThueBaoResponse(
        String status,
        GoiDichVuResponse plan,
        String periodStart,
        String periodEnd,
        GoiDichVuResponse scheduledPlan,
        String scheduledEffectiveAt,
        boolean readOnlyMode
) {}
