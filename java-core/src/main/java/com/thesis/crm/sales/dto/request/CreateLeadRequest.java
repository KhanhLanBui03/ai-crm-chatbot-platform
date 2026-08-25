package com.thesis.crm.sales.dto.request;

import com.thesis.crm.common.enums.Level;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.util.UUID;

/**
 * MẪU — DTO đầu vào. Dùng {@code record} + Bean Validation.
 *
 * <p>DTO KHÔNG BAO GIỜ nhận {@code tenantId} từ phía client. Giá trị đó lấy từ JWT đã xác thực
 * (xem {@code security/}). Cho client truyền tenantId là mở toang đường vượt tenant.
 *
 * <p>Cũng không nhận {@code source}: cơ hội tạo qua đường này luôn là {@code MANUAL}. Nhánh
 * {@code AI_AUTO} đi qua API nội bộ của Track B, không qua controller công khai — nếu để client
 * tự khai nguồn thì chỉ số "bao nhiêu phần trăm cơ hội đến từ bot" mất hết ý nghĩa.
 *
 * <p>Không nhận {@code currentScore} vì cùng lý do: điểm do Track B tính.
 */
public record CreateLeadRequest(
        @NotNull UUID contactId,
        UUID sourceConversationId,
        @Size(max = 200) String interestedProduct,
        @DecimalMin("0") BigDecimal budgetMin,
        @DecimalMin("0") BigDecimal budgetMax,
        Level budgetConfidence,
        Level urgency,
        String interestSummary,
        UUID ownerUserId) {
}
