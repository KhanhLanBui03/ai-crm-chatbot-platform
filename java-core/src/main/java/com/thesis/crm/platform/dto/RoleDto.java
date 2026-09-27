package com.thesis.crm.platform.dto;

import java.util.Map;

public record RoleDto(
        String code,
        String name,
        String description,
        Map<String, String> permissions,
        long userCount
) {}
