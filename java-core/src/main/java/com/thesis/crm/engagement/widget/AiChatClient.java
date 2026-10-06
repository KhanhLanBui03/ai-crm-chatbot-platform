package com.thesis.crm.engagement.widget;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * Gọi {@code POST /v1/ai/chat} của ai-service (UC010 bước 6 → UC022). Hợp đồng:
 * {@code ai-service/src/ai/schemas.py} {@code ChatRequest}/{@code ChatResponse}.
 *
 * <p>Gọi thẳng ai-service trong mạng nội bộ, KHÔNG qua gateway; tenant đi bằng header
 * {@code X-Tenant-Id} lấy từ token widget đã xác thực chữ ký (ai-service {@code deps.py}).
 *
 * <p>Mọi lỗi (mạng, quá giờ chờ, 5xx, phản hồi sai dạng) trả {@link Optional#empty()} — bên gọi
 * chuyển hội thoại cho nhân viên thay vì để khách thấy lỗi (đường lùi đã chốt cho UC010).
 */
@Component
public class AiChatClient {

    private static final Logger log = LoggerFactory.getLogger(AiChatClient.class);

    public record Citation(String documentId, String title, String snippet) {}

    public record AiReply(String answer, String route, boolean refused, boolean handoff,
                          List<Citation> citations) {}

    /** Một tin trong lịch sử gửi kèm: {@code role} là user/assistant như ai-service mong đợi. */
    public record Turn(String role, String content) {}

    private final RestClient http;

    public AiChatClient(
            @Value("${ai-service.url}") String baseUrl,
            @Value("${ai-service.chat-timeout:10s}") Duration timeout) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout((int) Duration.ofSeconds(2).toMillis());
        factory.setReadTimeout((int) timeout.toMillis());
        this.http = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
    }

    public Optional<AiReply> chat(UUID tenantId, UUID conversationId, String message,
                                  List<Turn> history, String traceId) {
        try {
            JsonNode body = http.post()
                    .uri("/v1/ai/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .header("X-Tenant-Id", tenantId.toString())
                    .header("X-Trace-Id", traceId)
                    .body(Map.of(
                            "conversation_id", conversationId.toString(),
                            "message", message,
                            "history", history.stream()
                                    .map(t -> Map.of("role", t.role(), "content", t.content())).toList(),
                            "metadata", Map.of("channel", "WEB_WIDGET")))
                    .retrieve()
                    .body(JsonNode.class);
            if (body == null || !body.hasNonNull("answer")) {
                log.warn("ai-service trả phản hồi thiếu 'answer' (trace {})", traceId);
                return Optional.empty();
            }
            List<Citation> citations = new ArrayList<>();
            for (JsonNode c : body.path("citations")) {
                citations.add(new Citation(
                        c.path("document_id").asText(null),
                        c.path("title").asText(null),
                        c.path("snippet").asText(null)));
            }
            return Optional.of(new AiReply(
                    body.get("answer").asText(),
                    body.path("route").asText("FALLBACK"),
                    body.path("refused").asBoolean(false),
                    body.path("handoff").asBoolean(false),
                    citations));
        } catch (RuntimeException e) {
            log.warn("Gọi ai-service thất bại (trace {}): {}", traceId, e.toString());
            return Optional.empty();
        }
    }
}
