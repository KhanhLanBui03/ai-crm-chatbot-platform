package com.thesis.crm.platform.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record DangKyRequest(
        @NotBlank(message = "Tên doanh nghiệp không được để trống")
        @Size(min = 2, max = 200, message = "Tên doanh nghiệp từ 2 đến 200 ký tự")
        String companyName,

        String industry,

        @NotBlank(message = "Họ và tên không được để trống")
        @Size(min = 2, max = 200, message = "Họ và tên từ 2 đến 200 ký tự")
        String fullName,

        @NotBlank(message = "Email không được để trống")
        @Email(message = "Email không đúng định dạng")
        String email,

        @NotBlank(message = "Mật khẩu không được để trống")
        @Size(min = 8, message = "Mật khẩu phải có ít nhất 8 ký tự")
        String password,

        String timezone,

        @NotNull(message = "Cần đồng ý điều khoản dịch vụ")
        Boolean acceptedTerms,

        String otpCode
) {}
