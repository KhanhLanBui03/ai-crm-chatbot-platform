package com.thesis.crm.security;

import com.thesis.crm.common.exception.BusinessException;
import java.util.UUID;
import org.springframework.http.HttpStatus;

/**
 * Tenant của một lời gọi {@code /internal/**}. Ở bề mặt này {@code X-Tenant-Id} LÀ ngữ cảnh đã xác
 * thực: chỉ ai-service gọi được (đã qua {@link InternalTokenFilter}), và nó chuyển tiếp đúng tenant của
 * luồng gốc — header gateway gắn từ JWT, hoặc vỏ sự kiện outbox. Không bao giờ đọc tenant từ path/body.
 * Thiếu hay sai thì ném ngay, không mặc định về tenant nào (CLAUDE.md luật 1).
 */
public final class InternalCaller {

    private InternalCaller() {
    }

    public static UUID requireTenantId(String header) {
        if (header == null || header.isBlank()) {
            throw thieu();
        }
        try {
            return UUID.fromString(header.trim());
        } catch (IllegalArgumentException e) {
            throw thieu();
        }
    }

    private static BusinessException thieu() {
        return new BusinessException(HttpStatus.BAD_REQUEST, "TENANT_CONTEXT_MISSING",
                "Lời gọi nội bộ thiếu hoặc sai X-Tenant-Id.");
    }
}
