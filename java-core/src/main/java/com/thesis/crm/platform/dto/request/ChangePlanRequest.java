package com.thesis.crm.platform.dto.request;

import jakarta.validation.constraints.NotBlank;

/**
 * Yêu cầu đổi gói dịch vụ (POST /api/v1/subscription/change).
 */
public record ChangePlanRequest(
        @NotBlank(message = "Mã gói không được để trống.")
        String planCode
) {}
