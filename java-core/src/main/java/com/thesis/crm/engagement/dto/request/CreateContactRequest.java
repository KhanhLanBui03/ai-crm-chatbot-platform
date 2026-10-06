package com.thesis.crm.engagement.dto.request;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * {@code LuuKhachHangRequest} (docs/openapi/dashboard-api.yaml) — tạo khách thủ công, SCR027.
 *
 * <p>Quy tắc "phải có số điện thoại HOẶC địa chỉ thư" nói về QUAN HỆ giữa hai trường nên kiểm ở
 * service, không bằng annotation trên từng trường — giống cách giao diện kiểm ở mức lược đồ.
 */
public record CreateContactRequest(
        @Size(max = 200, message = "Họ tên tối đa 200 ký tự.")
        String fullName,

        @Size(max = 30, message = "Số điện thoại tối đa 30 ký tự.")
        String phone,

        @Email(message = "Địa chỉ thư không hợp lệ.")
        @Size(max = 255, message = "Địa chỉ thư tối đa 255 ký tự.")
        String email,

        @Pattern(regexp = "WEB_WIDGET|ZALO|FACEBOOK|PHONE", message = "Kênh chính không hợp lệ.")
        String primaryChannel,

        Boolean consentGranted,

        @Pattern(regexp = "WIDGET|ZALO|FACEBOOK|AGENT_MANUAL", message = "Nguồn đồng ý không hợp lệ.")
        String consentSource) {}
