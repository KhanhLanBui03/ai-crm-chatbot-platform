package com.thesis.crm.platform.dto.response;

import java.util.UUID;

/**
 * SCR032 — hình {@code DoanTaiLieu}. Không có {@code embedding}: ai-service không bao giờ trả nó.
 *
 * @param sectionPath tiêu đề mục chứa đoạn ({@code heading} phía ai-service)
 * @param embeddingVersion lưu trên TỪNG đoạn — đặc tả UC020 bước 4
 */
public record DoanTaiLieuResponse(
        UUID id,
        int ordinal,
        String content,
        String sectionPath,
        Integer tokenCount,
        String embeddingModel,
        String embeddingVersion) {
}
