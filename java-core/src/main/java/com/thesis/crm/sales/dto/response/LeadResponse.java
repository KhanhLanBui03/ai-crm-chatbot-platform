package com.thesis.crm.sales.dto.response;

import com.thesis.crm.common.enums.LeadStatus;
import java.time.Instant;
import java.util.UUID;

/**
 * MẪU — DTO đầu ra. Không trả entity thẳng ra controller.
 *
 * <p>Trả entity làm lộ cột nội bộ, kéo theo lazy-loading ngoài transaction, và khiến mọi
 * thay đổi schema thành thay đổi API.
 */
public record LeadResponse(
        UUID id,
        String fullName,
        String phone,
        String email,
        LeadStatus status,
        Instant createdAt) {
}
