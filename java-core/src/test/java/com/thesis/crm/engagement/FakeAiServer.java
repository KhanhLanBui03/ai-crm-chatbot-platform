package com.thesis.crm.engagement;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/**
 * ai-service giả cho test tích hợp: trả {@code POST /v1/ai/chat} theo kịch bản do test đặt, và ghi
 * lại request cuối để kiểm java-core gửi đúng header tenant. Dùng HttpServer có sẵn của JDK — không
 * thêm thư viện test nào.
 */
final class FakeAiServer {

    /** Kịch bản: mã HTTP + thân JSON + độ trễ (ms). */
    record Script(int status, String body, long delayMs) {}

    private final HttpServer server;
    private final AtomicReference<Script> script = new AtomicReference<>(answer("Xin chào!"));
    final AtomicReference<String> lastTenantHeader = new AtomicReference<>();
    final AtomicReference<String> lastBody = new AtomicReference<>();
    final AtomicInteger calls = new AtomicInteger();
    /** UC040 — thân trả cho GET /v1/safety-events (mảng JSON) và mã HTTP; header tenant của lần gọi cuối. */
    final AtomicReference<Script> safety = new AtomicReference<>(new Script(200, "[]", 0));
    final AtomicReference<String> lastSafetyTenant = new AtomicReference<>();
    /** UC038 — thân trả cho GET /v1/topic-clusters/latest; mã 204 = chưa có kỳ nào. */
    final AtomicReference<Script> topicClusters = new AtomicReference<>(new Script(204, "", 0));
    final AtomicReference<String> lastTopicTenant = new AtomicReference<>();
    /** GD2 — mã lượt mà {@link #answer} trả về, để test kiểm {@code messages.ai_interaction_id}. */
    static final String INTERACTION_ID = "33333333-3333-3333-3333-333333333333";
    /** GD2 — GET /v1/ai-interactions (danh sách) và POST …/{id}/feedback (đánh giá). */
    final AtomicReference<Script> interactions = new AtomicReference<>(
            new Script(200, "{\"items\": [], \"total\": 0, \"page\": 0, \"size\": 25}", 0));
    final AtomicReference<Script> feedback = new AtomicReference<>(new Script(200, """
            {"success": true, "message": "Đã ghi nhận đánh giá",
             "feedback_id": "44444444-4444-4444-4444-444444444444", "created": true}""", 0));
    final AtomicReference<String> lastInteractionsQuery = new AtomicReference<>();
    final AtomicReference<String> lastFeedbackPath = new AtomicReference<>();
    final AtomicReference<String> lastFeedbackBody = new AtomicReference<>();
    final AtomicReference<String> lastFeedbackTenant = new AtomicReference<>();
    final AtomicInteger feedbackCalls = new AtomicInteger();
    /** GD2 — GET /v1/knowledge-gaps và GET /v1/ai/quality (ô tỉ lệ tích cực của UC039, chốt Q2). */
    final AtomicReference<Script> gaps = new AtomicReference<>(
            new Script(200, "{\"items\": [], \"total\": 0, \"page\": 0, \"size\": 25}", 0));
    final AtomicReference<Script> quality = new AtomicReference<>(new Script(200, "{\"danh_gia\": []}", 0));
    final AtomicReference<String> lastQualityQuery = new AtomicReference<>();
    /** GD3 — POST /v1/ai/summarize (UC026 MANUAL) và DELETE /v1/ai/privacy/contacts/{id} (UC041). */
    final AtomicReference<Script> summarize = new AtomicReference<>(new Script(500, "{}", 0));
    final AtomicReference<String> lastSummarizeBody = new AtomicReference<>();
    final AtomicReference<Script> privacy = new AtomicReference<>(new Script(500, "{}", 0));
    final AtomicReference<String> lastPrivacyQuery = new AtomicReference<>();
    final AtomicReference<String> lastPrivacyToken = new AtomicReference<>();
    final AtomicInteger privacyCalls = new AtomicInteger();

    private FakeAiServer(HttpServer server) {
        this.server = server;
    }

    static FakeAiServer start() {
        try {
            HttpServer s = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            FakeAiServer fake = new FakeAiServer(s);
            s.createContext("/v1/ai/chat", ex -> {
                fake.calls.incrementAndGet();
                fake.lastTenantHeader.set(ex.getRequestHeaders().getFirst("X-Tenant-Id"));
                fake.lastBody.set(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
                Script sc = fake.script.get();
                if (sc.delayMs() > 0) {
                    try {
                        Thread.sleep(sc.delayMs());
                    } catch (InterruptedException ignored) {
                        Thread.currentThread().interrupt();
                    }
                }
                byte[] out = sc.body().getBytes(StandardCharsets.UTF_8);
                ex.getResponseHeaders().add("Content-Type", "application/json");
                ex.sendResponseHeaders(sc.status(), out.length);
                try (OutputStream os = ex.getResponseBody()) {
                    os.write(out);
                }
            });
            s.createContext("/v1/safety-events", ex -> {
                fake.lastSafetyTenant.set(ex.getRequestHeaders().getFirst("X-Tenant-Id"));
                Script sc = fake.safety.get();
                byte[] out = sc.body().getBytes(StandardCharsets.UTF_8);
                ex.getResponseHeaders().add("Content-Type", "application/json");
                ex.sendResponseHeaders(sc.status(), out.length);
                try (OutputStream os = ex.getResponseBody()) {
                    os.write(out);
                }
            });
            s.createContext("/v1/topic-clusters/latest", ex -> {
                fake.lastTopicTenant.set(ex.getRequestHeaders().getFirst("X-Tenant-Id"));
                Script sc = fake.topicClusters.get();
                byte[] out = sc.body().getBytes(StandardCharsets.UTF_8);
                ex.getResponseHeaders().add("Content-Type", "application/json");
                ex.sendResponseHeaders(sc.status(), sc.status() == 204 ? -1 : out.length);
                if (sc.status() != 204) {
                    try (OutputStream os = ex.getResponseBody()) {
                        os.write(out);
                    }
                } else {
                    ex.close();
                }
            });
            s.createContext("/v1/ai-interactions", ex -> {
                if ("POST".equals(ex.getRequestMethod())) {
                    fake.feedbackCalls.incrementAndGet();
                    fake.lastFeedbackPath.set(ex.getRequestURI().getPath());
                    fake.lastFeedbackTenant.set(ex.getRequestHeaders().getFirst("X-Tenant-Id"));
                    fake.lastFeedbackBody.set(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
                    tra(ex, fake.feedback.get());
                } else {
                    fake.lastInteractionsQuery.set(ex.getRequestURI().getRawQuery());
                    tra(ex, fake.interactions.get());
                }
            });
            s.createContext("/v1/knowledge-gaps", ex -> tra(ex, fake.gaps.get()));
            s.createContext("/v1/ai/summarize", ex -> {
                fake.lastSummarizeBody.set(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
                tra(ex, fake.summarize.get());
            });
            s.createContext("/v1/ai/privacy/contacts", ex -> {
                fake.privacyCalls.incrementAndGet();
                fake.lastPrivacyQuery.set(ex.getRequestURI().getRawQuery());
                fake.lastPrivacyToken.set(ex.getRequestHeaders().getFirst("X-Internal-Token"));
                tra(ex, fake.privacy.get());
            });
            s.createContext("/v1/ai/quality", ex -> {
                fake.lastQualityQuery.set(ex.getRequestURI().getRawQuery());
                tra(ex, fake.quality.get());
            });
            s.start();
            return fake;
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    private static void tra(com.sun.net.httpserver.HttpExchange ex, Script sc) throws IOException {
        byte[] out = sc.body().getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().add("Content-Type", "application/json");
        ex.sendResponseHeaders(sc.status(), out.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(out);
        }
    }

    String baseUrl() {
        return "http://127.0.0.1:" + server.getAddress().getPort();
    }

    void respond(Script s) {
        script.set(s);
    }

    static Script answer(String text) {
        return new Script(200, """
                {"answer": "%s", "citations": [{"chunk_id": "11111111-1111-1111-1111-111111111111",
                 "document_id": "22222222-2222-2222-2222-222222222222", "title": "Bảng giá 2026",
                 "snippet": "Gói Pro 3.990.000đ/tháng", "score": 0.91}],
                 "route": "RAG", "refused": false, "handoff": false, "latency_ms": 120,
                 "interaction_id": "%s", "refusal_reason": null, "degraded": false}
                """.formatted(text, INTERACTION_ID), 0);
    }

    /** UC023 8.2 — LLM không phục vụ được, câu trả lời là trích nguyên văn đoạn liên quan nhất. */
    static Script degraded(String text) {
        return new Script(200, """
                {"answer": "%s", "citations": [], "route": "RAG", "refused": false, "handoff": false,
                 "latency_ms": 90, "interaction_id": "%s", "degraded": true}
                """.formatted(text, INTERACTION_ID), 0);
    }

    static Script handoff() {
        return new Script(200, """
                {"answer": "", "citations": [], "route": "HANDOFF", "refused": false, "handoff": true,
                 "latency_ms": 40}
                """, 0);
    }
}
