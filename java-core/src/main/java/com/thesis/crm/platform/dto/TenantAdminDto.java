package com.thesis.crm.platform.dto;

import java.time.Instant;
import java.util.UUID;

public record TenantAdminDto(
        UUID id,
        String companyName,
        String slug,
        String contactEmail,
        String phone,
        String industry,
        String status,
        String suspendedReason,
        String suspendedAt,
        String planCode,
        String planName,
        long userCount,
        long conversationCount,
        long tokenUsed,
        Instant createdAt
) {}
