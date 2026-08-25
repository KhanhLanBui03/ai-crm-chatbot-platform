package com.thesis.crm.sales.dto.response;

import com.thesis.crm.common.enums.LeadSource;
import com.thesis.crm.common.enums.LeadStatus;
import com.thesis.crm.common.enums.Level;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * MẪU — DTO đầu ra. Không trả entity thẳng ra controller.
 *
 * <p>Trả entity làm lộ cột nội bộ, kéo theo lazy-loading ngoài transaction, và khiến mọi
 * thay đổi schema thành thay đổi API.
 *
 * <p>Hình dạng khớp schema {@code Lead} trong {@code docs/openapi/dashboard-api.yaml}. Đây là
 * hợp đồng với web-dashboard: dashboard sinh type TypeScript từ file đó bằng
 * {@code npm run gen:api} chứ không gõ tay, nên đổi tên trường ở đây mà quên sửa hợp đồng thì
 * lỗi chỉ lộ ra lúc chạy.
 *
 * <p>{@code contactName} lấy bằng phép nối sang {@code engagement.contacts} — dashboard cần tên
 * để hiển thị và không nên phải gọi thêm một vòng nữa chỉ để lấy một chuỗi.
 */
public record LeadResponse(
        UUID id,
        UUID contactId,
        String contactName,
        String contactPhone,
        UUID sourceConversationId,
        LeadSource source,
        LeadStatus status,
        String interestedProduct,
        BigDecimal budgetMin,
        BigDecimal budgetMax,
        Level budgetConfidence,
        Level urgency,
        Short currentScore,
        Instant scoreUpdatedAt,
        UUID ownerUserId,
        String ownerName,
        Instant createdAt) {
}
