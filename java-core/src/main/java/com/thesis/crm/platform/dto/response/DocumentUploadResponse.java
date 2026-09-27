package com.thesis.crm.platform.dto.response;

import java.time.Instant;
import java.util.UUID;

/**
 * Phản hồi 202 của UC018 — hình {@code TaiLieu} ({@code dashboard-api.yaml}) cộng {@code jobId},
 * {@code documentQuota} và {@code storageQuota}. Đề xuất vá hợp đồng: {@code docs/contracts/uc018-tai-tai-lieu.md}.
 *
 * <p>{@code sourceType}, {@code mimeType}, {@code version} lấy từ ai-service — MIME THẬT của tệp,
 * không phải MIME trình duyệt khai. {@code uploadedByName} luôn {@code null} ở đây: người tải
 * chính là người đang xem phản hồi.
 *
 * @param jobId         bằng {@code id} — một tài liệu có đúng một tiến trình nạp (V202)
 * @param documentQuota số tài liệu đang có SAU lượt này so với trần của gói; {@code warnedAt ≠ null}
 *                      thì hiện cảnh báo 80%
 * @param storageQuota  dung lượng tài liệu đang chiếm SAU lượt này, tính bằng BYTE (ADR-0020)
 */
public record DocumentUploadResponse(
        UUID id,
        UUID jobId,
        String title,
        String description,
        String sourceType,
        String fileName,
        String mimeType,
        long sizeBytes,
        String language,
        String status,
        int chunkCount,
        int version,
        String errorMessage,
        String uploadedByName,
        Instant indexedAt,
        Instant createdAt,
        QuotaUsageResponse documentQuota,
        QuotaUsageResponse storageQuota) {
}
