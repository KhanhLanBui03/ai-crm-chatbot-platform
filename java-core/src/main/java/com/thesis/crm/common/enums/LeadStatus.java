package com.thesis.crm.common.enums;

/**
 * Trạng thái cơ hội tiềm năng.
 *
 * <p>Năm giá trị này lấy nguyên văn từ ràng buộc {@code CHECK} của {@code sales.leads.status}
 * (migration V108) và từ {@code TrangThaiLead} trong {@code docs/openapi/dashboard-api.yaml}.
 * Ba nơi phải khớp nhau: thêm giá trị ở đây mà quên migration thì {@code ddl-auto: validate}
 * không bắt được — lỗi chỉ nổ lúc chạy, khi CHECK từ chối bản ghi.
 *
 * <p>Chuyển trạng thái phát sự kiện {@code crm.lead.v1} qua outbox (ADR-0003).
 */
public enum LeadStatus {
    NEW,
    CONTACTED,
    QUALIFIED,
    CONVERTED,
    DISQUALIFIED
}
