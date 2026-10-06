package com.thesis.crm.platform.dto;

import java.time.Instant;
import java.util.UUID;

public record UserDto(
        UUID id,
        String fullName,
        String email,
        String roleCode,
        String roleName,
        String status,
        Instant emailVerifiedAt,
        Instant lastLoginAt,
        int assignedConversationCount,
        Instant createdAt
) {}
