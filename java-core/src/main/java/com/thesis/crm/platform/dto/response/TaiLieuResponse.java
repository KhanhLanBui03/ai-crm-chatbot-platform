package com.thesis.crm.platform.dto.response;

import java.time.Instant;
import java.util.UUID;

/**
 * Một dòng SCR030 — hình {@code TaiLieu} của {@code dashboard-api.yaml}, dựng từ
 * {@code DocumentDetail} của ai-service. java-core không đọc schema {@code knowledge} (ADR-0002):
 * mọi trường đến từ ai-service, riêng {@code uploadedByName} tra {@code platform.users}.
 *
 * @param sizeBytes {@code null} với nguồn URL (không có tệp)
 */
public record TaiLieuResponse(
        UUID id,
        String title,
        String description,
        String sourceType,
        String fileName,
        String mimeType,
        Long sizeBytes,
        String language,
        String status,
        int chunkCount,
        int version,
        String errorMessage,
        String uploadedByName,
        Instant indexedAt,
        Instant createdAt) {
}
