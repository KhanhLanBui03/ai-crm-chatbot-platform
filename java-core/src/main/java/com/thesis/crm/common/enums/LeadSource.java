package com.thesis.crm.common.enums;

/**
 * Nguồn sinh ra cơ hội tiềm năng. Khớp {@code sales.leads.source} (V108) và {@code NguonLead}
 * trong {@code docs/openapi/dashboard-api.yaml}.
 *
 * <p>Tách hai giá trị này là điều kiện để đo được đóng góp thật của tác tử AI: không có nó thì
 * không trả lời được câu "bao nhiêu phần trăm cơ hội đến từ bot" — chỉ số trung tâm của chương
 * đánh giá.
 */
public enum LeadSource {
    /** Tác tử AI phát hiện tín hiệu quan tâm rồi tự tạo (UC029 → UC030 → UC031). */
    AI_AUTO,
    /** Nhân viên nhập tay. */
    MANUAL
}
