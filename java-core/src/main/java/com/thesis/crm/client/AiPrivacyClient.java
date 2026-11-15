package com.thesis.crm.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.thesis.crm.config.InternalApiProperties;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * Xoá dữ liệu cá nhân phía Track B — UC041 bước 9, {@code DELETE /v1/ai/privacy/contacts/{id}}.
 *
 * <p>Endpoint chỉ java-core được gọi: ai-service đòi {@code X-Internal-Token} (cùng bí mật
 * {@code crm.internal.api-token}, chốt Q3 của GD3), thiếu/sai thì 403 {@code INTERNAL_ONLY} — lớp dịch
 * lỗi chung coi 403 là lệch cấu hình (500), đúng bản chất. Gateway chặn thêm đường này từ bên ngoài.
 *
 * <p>{@code conversationId} lặp lại được (tối đa 500): {@code ai.ai_interactions} không có
 * {@code contact_id}, chỉ java-core biết khách có những hội thoại nào. Gọi NGOÀI transaction của
 * java-core — giữa lượt này ai-service gọi ngược {@code DELETE /internal/contacts/{id}/lead-scores}.
 *
 * <p>Record là GƯƠNG của {@code ErasureResult}/{@code ErasureItem} ({@code ai-service/src/ai/schemas.py});
 * ai-service trả alias camelCase nên đọc bằng {@code @JsonProperty}. Nháp hợp đồng:
 * {@code docs/contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md} mục 4.
 */
@Component
public class AiPrivacyClient {

    /** Trần của ai-service ({@code max_length=500}) — java-core cắt trước khi gửi để không ăn 422. */
    public static final int TOI_DA_HOI_THOAI = 500;

    private final AiServiceClient ai;
    private final InternalApiProperties noiBo;

    public AiPrivacyClient(AiServiceClient ai, InternalApiProperties noiBo) {
        this.ai = ai;
        this.noiBo = noiBo;
    }

    public ErasureResult forgetContact(UUID tenantId, UUID contactId, Collection<UUID> conversationIds) {
        Map<String, String> header = noiBo.configured()
                ? Map.of(InternalApiProperties.HEADER, noiBo.apiToken())
                : Map.of();
        return ai.delete(tenantId, b -> {
            b.path("/v1/ai/privacy/contacts/{id}");
            conversationIds.forEach(c -> b.queryParam("conversationId", c.toString()));
            return b.build(contactId);
        }, header, ErasureResult.class);
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record ErasureItem(
            @JsonProperty("targetSchema") String targetSchema,
            @JsonProperty("targetTable") String targetTable,
            @JsonProperty("action") String action,
            @JsonProperty("status") String status,
            @JsonProperty("affectedRows") int affectedRows,
            @JsonProperty("errorCode") String errorCode) {
    }

    /**
     * {@code releasedDocuments}/{@code releasedStorageBytes}: phần hạn mức tồn kho mà lượt xoá này vừa
     * giải phóng (tài liệu ĐƯỢC ĐẾM — cùng luật với {@code quotaReleased} của đường gỡ UC020). Gọi lại
     * thì 0 vì tài liệu đã mất.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record ErasureResult(
            @JsonProperty("contactId") UUID contactId,
            @JsonProperty("status") String status,
            @JsonProperty("items") List<ErasureItem> items,
            @JsonProperty("note") String note,
            @JsonProperty("releasedDocuments") int releasedDocuments,
            @JsonProperty("releasedStorageBytes") long releasedStorageBytes) {
    }
}
