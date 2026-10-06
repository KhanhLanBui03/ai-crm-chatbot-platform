package com.thesis.crm.platform.dto;

import java.util.UUID;

public record DangKyResult(
        UUID tenantId,
        String slug,
        String email,
        boolean verificationRequired
) {}
