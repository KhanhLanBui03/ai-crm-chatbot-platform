package com.thesis.crm.platform.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * Hạn mức sử dụng trong chu kỳ hiện tại (SCR014).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record HanMucSuDungResponse(
        String periodStart,
        String periodEnd,
        MotHanMucDto conversations,
        MotHanMucDto tokens,
        MotHanMucDto users,
        MotHanMucDto documents,
        long costVnd,
        String warnedAt,
        String blockedAt
) {}
