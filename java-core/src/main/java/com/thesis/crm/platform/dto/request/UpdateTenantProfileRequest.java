package com.thesis.crm.platform.dto.request;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import java.util.Map;

/**
 * Yêu cầu cập nhật hồ sơ doanh nghiệp (PATCH /api/v1/tenant).
 */
public record UpdateTenantProfileRequest(
        @Size(min = 2, max = 200, message = "Tên doanh nghiệp cần từ 2 đến 200 ký tự.")
        String name,

        @Size(max = 100, message = "Ngành hàng tối đa 100 ký tự.")
        String industry,

        @Size(max = 255, message = "Email liên hệ tối đa 255 ký tự.")
        String contactEmail,

        @Size(max = 20, message = "Số điện thoại tối đa 20 ký tự.")
        String phone,

        @Size(max = 64, message = "Múi giờ không hợp lệ.")
        String timezone,

        String defaultLocale,

        Map<String, Object> businessHours,

        String aiTone,

        @Min(value = 0, message = "Ngưỡng điểm phải từ 0 đến 100.")
        @Max(value = 100, message = "Ngưỡng điểm phải từ 0 đến 100.")
        Integer leadScoreThreshold,

        Boolean autoLeadCreation,

        String assignmentMode,

        Map<String, Object> assignmentConfig
) {}
