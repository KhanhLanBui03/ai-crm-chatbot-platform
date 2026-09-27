package com.thesis.crm.platform.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record InviteUserRequest(
        @NotBlank(message = "Email không được để trống")
        @Email(message = "Email không đúng định dạng")
        String email,

        String fullName,

        @NotBlank(message = "Vai trò không được để trống")
        String roleCode
) {}
