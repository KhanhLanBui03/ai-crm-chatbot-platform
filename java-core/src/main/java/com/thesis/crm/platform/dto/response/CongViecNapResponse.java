package com.thesis.crm.platform.dto.response;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * SCR033 — hình {@code CongViecNap}, dựng từ {@code IngestionJobProgress} của ai-service. Không có
 * bảng {@code ingestion_jobs}: một tài liệu là một việc nạp, {@code id} = {@code documentId} (V202).
 *
 * @param trigger    {@code UPLOAD} hoặc {@code REINDEX} (bản bóng, ADR-0031)
 * @param tokensUsed luôn {@code null} — luồng nạp chưa ghi token (giảm độ sâu UC019)
 * @param costVnd    luôn {@code null} — cùng lý do
 */
public record CongViecNapResponse(
        UUID id,
        UUID documentId,
        String documentTitle,
        String trigger,
        String state,
        int attempt,
        int chunksCreated,
        Long tokensUsed,
        BigDecimal costVnd,
        String errorCode,
        String errorMessage,
        Long durationMs,
        Instant startedAt,
        Instant finishedAt,
        Instant createdAt) {
}
