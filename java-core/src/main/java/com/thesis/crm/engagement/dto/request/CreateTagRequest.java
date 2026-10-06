package com.thesis.crm.engagement.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * Tạo thẻ — UC017 luồng 8.1. Giới hạn theo CSDL (V105): tên ≤ 50, màu {@code #RRGGBB}.
 * Không gửi màu thì hệ thống tự gán ({@code TagColors}).
 */
public record CreateTagRequest(
        @NotBlank(message = "Tên thẻ không được để trống.")
        @Size(max = 50, message = "Tên thẻ tối đa 50 ký tự.")
        String name,

        @Pattern(regexp = "^#[0-9A-Fa-f]{6}$", message = "Màu thẻ phải có dạng #RRGGBB.")
        String color) {}
