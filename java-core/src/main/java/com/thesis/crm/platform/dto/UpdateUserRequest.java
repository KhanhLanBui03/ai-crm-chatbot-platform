package com.thesis.crm.platform.dto;

public record UpdateUserRequest(
        String fullName,
        String roleCode,
        String status
) {}
