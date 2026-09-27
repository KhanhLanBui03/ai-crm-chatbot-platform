package com.thesis.crm.platform.dto;

import jakarta.validation.constraints.NotBlank;

public record SuspendTenantRequest(
        @NotBlank(message = "Vui lòng nhập lý do đình chỉ")
        String reason
) {}
