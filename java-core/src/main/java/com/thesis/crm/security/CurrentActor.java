package com.thesis.crm.security;

import com.thesis.crm.common.exception.AppException;
import java.util.UUID;
import org.springframework.http.HttpStatus;

/**
 * Lấy danh tính người gọi từ JWT ĐÃ XÁC THỰC — không bao giờ từ query/body/path (CLAUDE.md luật 1).
 * Thiếu thì 401 ngay, không đoán và không mặc định.
 */
public final class CurrentActor {

    private CurrentActor() {}

    public static UUID requireTenantId() {
        UUID tenantId = SecurityUtils.getCurrentTenantId();
        if (tenantId == null) {
            throw new AppException(
                    "Phiên làm việc không hợp lệ hoặc thiếu thông tin doanh nghiệp.", HttpStatus.UNAUTHORIZED);
        }
        return tenantId;
    }

    /** Người thao tác — cần cho nhật ký kiểm toán và quyền sửa/xoá. */
    public static UUID requireUserId() {
        UUID userId = SecurityUtils.getCurrentUserId();
        if (userId == null) {
            throw new AppException("Phiên làm việc không xác định được người dùng.", HttpStatus.UNAUTHORIZED);
        }
        return userId;
    }

    public static boolean isTenantAdmin() {
        return SecurityUtils.isTenantAdmin();
    }
}
