package com.thesis.crm.common.enums;

/**
 * Chỉ số hạn mức. Khớp ràng buộc {@code CHECK (metric IN (...))} của
 * {@code platform.usage_records} (V102) — thêm giá trị ở đây mà quên migration thì ghi xuống
 * CSDL nổ ngay, không lặng lẽ.
 *
 * <p>Hai loại chỉ số, khác nhau ở chỗ sang chu kỳ mới (ADR-0023):
 *
 * <ul>
 *   <li><b>Dòng chảy</b> — tiêu thụ trong chu kỳ, sang chu kỳ mới về 0: hội thoại, token.
 *   <li><b>Tồn kho</b> — lượng ĐANG CÓ, sang chu kỳ mới chép nguyên: tài liệu, dung lượng, người
 *       dùng. Tài liệu không biến mất khi sang tháng.
 * </ul>
 */
public enum UsageMetric {
    CONVERSATION(false),
    AI_TOKEN(false),
    DOCUMENT(true),
    /** Tính bằng BYTE ở cả {@code used_value} lẫn {@code quota_value}, dù tên là MB (ADR-0023 (c)). */
    STORAGE_MB(true),
    USER(true);

    private final boolean tonKho;

    UsageMetric(boolean tonKho) {
        this.tonKho = tonKho;
    }

    /** {@code true}: sang chu kỳ mới chép mức đang có thay vì về 0. */
    public boolean isStock() {
        return tonKho;
    }
}
