package com.thesis.crm.common.enums;

/**
 * Chỉ số hạn mức. Khớp ràng buộc {@code CHECK (metric IN (...))} của
 * {@code platform.usage_records} (V102) — thêm giá trị ở đây mà quên migration thì ghi xuống
 * CSDL nổ ngay, không lặng lẽ.
 *
 * <p>UC006 hiển thị bốn chỉ số; {@code STORAGE_MB} có trong ràng buộc nhưng chưa màn nào dùng.
 */
public enum UsageMetric {
    CONVERSATION,
    AI_TOKEN,
    DOCUMENT,
    STORAGE_MB,
    USER
}
