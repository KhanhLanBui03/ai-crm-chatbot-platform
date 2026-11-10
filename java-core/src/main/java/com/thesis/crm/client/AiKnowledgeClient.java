package com.thesis.crm.client;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriBuilder;

/**
 * Kho tri thức phía ai-service — UC019 tiến độ nạp, UC020 quản lý kho (GD1). Chỉ là bảng địa chỉ
 * và gương DTO; vận chuyển, header tenant/trace và mã lỗi do {@link AiServiceClient} lo.
 *
 * <p>Record ở đây là GƯƠNG của {@code ai-service/src/ai/schemas.py} ({@code DocumentDetail},
 * {@code ChunkItem}, {@code IngestionJobProgress}…). Tên trường Java viết camelCase, mapper
 * {@code snake_case} của {@link AiServiceClient} đổi chiều — không cần {@code @JsonNaming} từng
 * record. Trường ai-service có mà gương không khai thì bỏ qua (vd. {@code steps}, {@code percent}).
 * Nháp hợp đồng: {@code docs/contracts/giao-dien-gd.md}.
 */
@Component
public class AiKnowledgeClient {

    private final AiServiceClient ai;

    public AiKnowledgeClient(AiServiceClient ai) {
        this.ai = ai;
    }

    /** SCR030. Không lọc {@code status} thì ai-service ẩn {@code ARCHIVED}. */
    public KbDocumentPage listDocuments(UUID tenantId, String keyword, String status, String sourceType,
            int page, int size) {
        return ai.get(tenantId, b -> {
            Map<String, Object> bien = new HashMap<>();
            b.path("/v1/documents").queryParam("page", page).queryParam("size", size);
            themNeuCo(b, bien, "keyword", keyword);
            themNeuCo(b, bien, "status", status);
            themNeuCo(b, bien, "sourceType", sourceType);
            return b.build(bien);
        }, KbDocumentPage.class);
    }

    public KbDocument getDocument(UUID tenantId, UUID documentId) {
        return ai.get(tenantId, b -> b.path("/v1/documents/{id}").build(documentId), KbDocument.class);
    }

    public KbChunkPage listChunks(UUID tenantId, UUID documentId, int page, int size) {
        return ai.get(tenantId, b -> b.path("/v1/documents/{id}/chunks")
                .queryParam("page", page)
                .queryParam("size", size)
                .build(documentId), KbChunkPage.class);
    }

    /** Chỉ siêu dữ liệu — chỉ mục vector giữ nguyên. Trả bản ghi SAU khi sửa. */
    public KbDocument updateMetadata(UUID tenantId, UUID documentId, KbMetadataUpdate than) {
        return ai.patch(tenantId, b -> b.path("/v1/documents/{id}").build(documentId), than, KbDocument.class);
    }

    /** Tạo bản bóng {@code PENDING} (ADR-0031) — {@code jobId} của phản hồi là id bản bóng. */
    public KbReindexAccepted reindex(UUID tenantId, UUID documentId) {
        return ai.post(tenantId, b -> b.path("/v1/documents/{id}/reindex").build(documentId), null,
                KbReindexAccepted.class);
    }

    /**
     * Gỡ khỏi chỉ mục — đường nội bộ đặc tả UC020 ghi ({@code DELETE /v1/ai/kb/documents/{id}},
     * đồng bộ). Xoá đoạn trước rồi mới {@code ARCHIVED}, cùng transaction (luồng phụ 7.2).
     */
    public KbDocumentDeleted delete(UUID tenantId, UUID documentId) {
        return ai.delete(tenantId, b -> b.path("/v1/ai/kb/documents/{id}").build(documentId),
                KbDocumentDeleted.class);
    }

    /** {@code jobId} = {@code documentId} của tài liệu (hoặc của bản bóng đang nạp lại). */
    public KbIngestionJob ingestionJob(UUID tenantId, UUID jobId) {
        return ai.get(tenantId, b -> b.path("/v1/ai/kb/ingestion-jobs/{id}").build(jobId), KbIngestionJob.class);
    }

    /** SCR033 — hàng đợi nạp, mới nhất trước. */
    public KbIngestionJobPage listIngestionJobs(UUID tenantId, String state, int page, int size) {
        return ai.get(tenantId, b -> {
            Map<String, Object> bien = new HashMap<>();
            b.path("/v1/ai/kb/ingestion-jobs").queryParam("page", page).queryParam("size", size);
            themNeuCo(b, bien, "state", state);
            return b.build(bien);
        }, KbIngestionJobPage.class);
    }

    /**
     * Giá trị người dùng gõ đi qua BIẾN URI, không ghép thẳng vào mẫu: biến được mã hoá chặt (cả
     * {@code &}, {@code +}, {@code =}), nên từ khoá "a&status=READY" không lén thêm được tham số.
     */
    private static void themNeuCo(UriBuilder b, Map<String, Object> bien, String ten, String giaTri) {
        if (giaTri != null && !giaTri.isBlank()) {
            b.queryParam(ten, "{" + ten + "}");
            bien.put(ten, giaTri);
        }
    }

    // ── Gương DTO ───────────────────────────────────────────────────────────────────

    /** Gương {@code DocumentDetail}. {@code reindexDocumentId}: bản bóng ĐANG nạp lại dòng này. */
    public record KbDocument(
            UUID id,
            String title,
            String status,
            String sourceType,
            UUID uploadedBy,
            int chunkCount,
            OffsetDateTime createdAt,
            String description,
            String language,
            String fileName,
            String mimeType,
            Long fileSizeBytes,
            int version,
            String errorMessage,
            OffsetDateTime indexedAt,
            OffsetDateTime updatedAt,
            UUID replacesDocumentId,
            UUID reindexDocumentId) {
    }

    public record KbDocumentPage(List<KbDocument> items, long total, int page, int size) {
    }

    /** Gương {@code ChunkItem} — không bao giờ có {@code embedding}. */
    public record KbChunk(
            UUID chunkId,
            int chunkIndex,
            String content,
            String heading,
            Integer pageNumber,
            Integer tokenCount,
            String embeddingModel,
            String embeddingVersion) {
    }

    public record KbChunkPage(List<KbChunk> items, long total, int page, int size) {
    }

    /**
     * Gương {@code DocumentMetadataUpdate}. {@code ALWAYS}: {@code description = null} PHẢI đi trong
     * thân — ai-service phân biệt "xoá mô tả" (có trường, giá trị null) với "giữ nguyên" (vắng trường).
     * Không có {@code contactId}: gắn tài liệu với khách là việc của UC041, không mở ra dashboard ở đây.
     */
    @JsonInclude(JsonInclude.Include.ALWAYS)
    public record KbMetadataUpdate(String title, String description) {
    }

    /** Gương {@code ReindexAccepted}: {@code documentId} là bản CŨ, {@code jobId} là bản bóng MỚI. */
    public record KbReindexAccepted(String message, UUID documentId, UUID jobId, int version, String status) {
    }

    /**
     * Gương {@code DocumentDeleted}. {@code quotaReleased}: lượt gỡ này vừa chuyển một tài liệu được
     * đếm hạn mức sang {@code ARCHIVED} — java-core trả 1 tài liệu và {@code fileSizeBytes} byte.
     */
    public record KbDocumentDeleted(String message, int chunksDeleted, Long fileSizeBytes, boolean quotaReleased) {
    }

    /** Gương {@code IngestionJobProgress} (bỏ {@code steps}, {@code percent} — dashboard tự vẽ từ {@code state}). */
    public record KbIngestionJob(
            UUID jobId,
            UUID documentId,
            String documentTitle,
            String trigger,
            String state,
            String status,
            int attempt,
            int chunksCreated,
            Integer chunksTotal,
            String errorCode,
            String errorMessage,
            Long durationMs,
            OffsetDateTime startedAt,
            OffsetDateTime finishedAt,
            OffsetDateTime createdAt) {
    }

    public record KbIngestionJobPage(List<KbIngestionJob> items, long total, int page, int size) {
    }
}
