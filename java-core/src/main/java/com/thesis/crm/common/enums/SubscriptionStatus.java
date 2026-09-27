package com.thesis.crm.common.enums;

/**
 * Trạng thái thuê bao. Khớp {@code CHECK} của {@code platform.tenant_subscriptions.status} (V102)
 * và {@code TrangThaiThueBao} trong {@code docs/openapi/dashboard-api.yaml}.
 *
 * <p>Chỉ {@code TRIALING} và {@code ACTIVE} được tiêu thụ hạn mức. {@code PAST_DUE} và
 * {@code EXPIRED} đưa hệ thống sang chế độ chỉ đọc ({@code readOnlyMode} của hợp đồng dashboard).
 */
public enum SubscriptionStatus {
    TRIALING,
    ACTIVE,
    PAST_DUE,
    EXPIRED,
    CANCELED
}
