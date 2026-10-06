package com.thesis.crm.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import java.io.IOException;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

/**
 * Bề mặt DUY NHẤT của java-core gọi ai-service (ADR-0002, luật ranh giới 4 của java-core).
 *
 * <p>Hợp đồng từng endpoint: {@code docs/contracts/uc018-tai-tai-lieu.md} (nháp) →
 * {@code docs/openapi/ai-service-to-java-core.yaml} khi đã chốt. DTO ở đây là GƯƠNG của
 * {@code ai-service/src/ai/schemas.py} — đổi bên này phải đổi bên kia.
 */
@Component
public class AiServiceClient {

    public static final String HEADER_TENANT = "X-Tenant-Id";
    public static final String HEADER_TRACE = "X-Trace-Id";

    private final RestClient rest;
    private final ObjectMapper objectMapper;

    public AiServiceClient(@Qualifier("aiServiceRestClient") RestClient rest, ObjectMapper objectMapper) {
        this.rest = rest;
        this.objectMapper = objectMapper;
    }

    /**
     * UC018 — báo ai-service rằng tệp đã nằm trên kho S3, nhận lại bản ghi {@code PENDING}.
     *
     * <p>Tenant đi ở header {@code X-Tenant-Id}, KHÔNG ở thân: {@link KbDocumentCreate} không có
     * trường tenant, và ai-service từ chối (422) mọi trường lạ trong thân.
     *
     * @throws AiServiceException khi ai-service trả khác 202 hoặc không trả lời
     */
    public KbDocumentAccepted createKbDocument(UUID tenantId, String traceId, KbDocumentCreate body) {
        try {
            return rest.post()
                    .uri("/v1/ai/kb/documents")
                    .header(HEADER_TENANT, tenantId.toString())
                    .header(HEADER_TRACE, traceId)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .exchange((req, resp) -> {
                        // Chỉ 202 là thành công. 200/201 cũng là lệch hợp đồng — ai-service
                        // chưa hề ghi nhận rằng việc nạp đã được xếp hàng.
                        if (resp.getStatusCode().value() == HttpStatus.ACCEPTED.value()) {
                            return objectMapper.readValue(resp.getBody(), KbDocumentAccepted.class);
                        }
                        throw loiTuPhanHoi(resp.getStatusCode().value(), resp.getBody().readAllBytes());
                    });
        } catch (ResourceAccessException e) {
            throw AiServiceException.unreachable(e);
        }
    }

    /** Đọc {@code {code, message}} của ai-service; thân không đúng khuôn thì vẫn giữ mã HTTP. */
    private AiServiceException loiTuPhanHoi(int status, byte[] than) {
        String code = null;
        String message = "ai-service trả " + status;
        try {
            JsonNode node = objectMapper.readTree(than);
            if (node != null && node.hasNonNull("code")) {
                code = node.get("code").asText();
            }
            if (node != null && node.hasNonNull("message")) {
                message = node.get("message").asText();
            }
        } catch (IOException ignored) {
            // Thân không phải JSON (proxy trả HTML, …) — mã HTTP là đủ để phân loại.
        }
        return new AiServiceException(status, code, message);
    }

    /** Gương của {@code KbDocumentCreate} (Pydantic, {@code extra="forbid"}). */
    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public record KbDocumentCreate(
            String fileUri,
            String fileName,
            String title,
            String description,
            String language,
            UUID uploadedBy) {
    }

    /** Gương của {@code KbDocumentAccepted}. {@code jobId} bằng đúng {@code documentId}. */
    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record KbDocumentAccepted(
            UUID documentId,
            UUID jobId,
            String title,
            int version,
            String status,
            String sourceType,
            String mimeType) {
    }
}
