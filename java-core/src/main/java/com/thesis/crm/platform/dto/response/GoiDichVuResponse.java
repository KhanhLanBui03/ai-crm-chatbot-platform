package com.thesis.crm.platform.dto.response;

import java.math.BigDecimal;

/**
 * Gói dịch vụ (SCR013).
 */
public record GoiDichVuResponse(
        String code,
        String name,
        BigDecimal monthlyPriceVnd,
        int conversationQuota,
        long tokenQuota,
        int maxUsers,
        int maxDocuments,
        int maxChannels,
        int sortOrder,
        boolean isCurrent
) {}
