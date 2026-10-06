package com.thesis.crm.platform.dto;

import java.util.List;
import java.util.UUID;

public record NguoiDungHienTaiDto(
        UUID id,
        String fullName,
        String email,
        String roleCode,
        List<String> permissions,
        String tenantName,
        String planName
) {}
