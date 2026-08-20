package com.thesis.crm.sales.dto.request;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * MẪU — DTO đầu vào. Dùng {@code record} + Bean Validation.
 *
 * <p>DTO KHÔNG BAO GIỜ nhận {@code tenantId} từ phía client. Giá trị đó lấy từ JWT đã xác thực
 * (xem {@code security/}). Cho client truyền tenantId là mở toang đường vượt tenant.
 */
public record CreateLeadRequest(
        @NotBlank @Size(max = 200) String fullName,
        @Size(max = 30) String phone,
        @Email @Size(max = 200) String email) {
}
