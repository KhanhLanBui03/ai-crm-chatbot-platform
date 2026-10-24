package com.thesis.crm.platform.dto.response;

import java.time.Instant;
import java.util.UUID;

/**
 * SCR031 — hình {@code TaiLieuChiTiet} = {@code TaiLieu} + ba trường. Chép đủ trường thay vì lồng
 * {@link TaiLieuResponse}: hợp đồng là {@code allOf} (cùng cấp), record Java không kế thừa được.
 *
 * @param replacesDocumentId bản này là bản bóng nạp lại của tài liệu nào (ADR-0031)
 * @param latestJob          việc nạp gần nhất: của bản bóng nếu đang nạp lại, không thì của chính nó
 * @param checksum           luôn {@code null} — ai-service chưa lưu băm tệp
 */
public record TaiLieuChiTietResponse(
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
        Instant createdAt,
        UUID replacesDocumentId,
        CongViecNapResponse latestJob,
        String checksum) {
}
