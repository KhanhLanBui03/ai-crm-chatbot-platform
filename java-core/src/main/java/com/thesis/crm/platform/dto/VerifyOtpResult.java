package com.thesis.crm.platform.dto;

public record VerifyOtpResult(
        boolean valid,
        String resetToken
) {}
