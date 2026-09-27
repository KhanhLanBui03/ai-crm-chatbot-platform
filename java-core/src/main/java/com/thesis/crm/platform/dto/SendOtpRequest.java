package com.thesis.crm.platform.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record SendOtpRequest(
        @NotBlank(message = "Email không được để trống")
        @Email(message = "Email không đúng định dạng")
        String email,

        String companyName,

        String purpose // "REGISTER" | "FORGOT_PASSWORD"
) {}
