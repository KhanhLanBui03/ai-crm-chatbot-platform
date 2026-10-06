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
            s.start();
            return fake;
        } catch (IOException e) {
            throw new IllegalStateException(e);
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
                 "route": "RAG", "refused": false, "handoff": false, "latency_ms": 120}
                """.formatted(text), 0);
    }

    static Script handoff() {
        return new Script(200, """
                {"answer": "", "citations": [], "route": "HANDOFF", "refused": false, "handoff": true,
                 "latency_ms": 40}
                """, 0);
    }
}
