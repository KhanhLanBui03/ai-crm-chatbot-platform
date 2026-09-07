package com.thesis.crm.common.enums;

/**
 * Thang ba mức dùng chung. Khớp {@code MucDo} trong {@code docs/openapi/dashboard-api.yaml}.
 *
 * <p>Hiện dùng cho {@code sales.leads.budget_confidence} và {@code sales.leads.urgency}.
 *
 * <p>Vì sao ngân sách lưu dưới dạng <b>khoảng</b> kèm mức chắc chắn thay vì một con số: khách
 * hàng hiếm khi nói một số chính xác trong hội thoại, và ép tác tử AI trích ra một con số duy
 * nhất là buộc nó đoán — con số đoán trông y hệt con số khách đã nói.
 */
public enum Level {
    LOW,
    MEDIUM,
    HIGH
}
