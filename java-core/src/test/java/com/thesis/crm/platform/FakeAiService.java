package com.thesis.crm.platform;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * ai-service giả cho test tích hợp của java-core — máy chủ HTTP có sẵn trong JDK, không thêm
 * phụ thuộc. Mặc định trả 202 đúng hình {@code KbDocumentAccepted}; từng test đổi được phản hồi.
 *
 * <p>Giả lập chứ không chạy ai-service thật: phía ai-service đã có 96 test riêng trên Postgres và
 * RustFS thật. Ở đây cần điều khiển được ai-service trả GÌ (415, 403, 500, chậm quá hạn) để kiểm
 * java-core dọn dẹp và dịch lỗi đúng.
 */
final class FakeAiService implements AutoCloseable {

    record Request(String tenantId, String traceId, String contentType, Map<String, Object> body) {
    }

    record Response(int status, Map<String, Object> body, long delayMs) {
    }

    @FunctionalInterface
    interface Responder {
        Response respond(Request request);
    }

    private static final Map<String, String[]> DINH_DANG = Map.of(
            ".pdf", new String[] {"PDF", "application/pdf"},
            ".docx", new String[] {"DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
            ".txt", new String[] {"TXT", "text/plain"},
            ".md", new String[] {"MD", "text/markdown"},
            ".html", new String[] {"HTML", "text/html"});

    private final ObjectMapper json = new ObjectMapper();
    private final HttpServer server;
    private final ExecutorService executor = Executors.newFixedThreadPool(8);
    final List<Request> requests = new CopyOnWriteArrayList<>();
    volatile Responder responder = FakeAiService::chapNhan;

    private FakeAiService() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.setExecutor(executor);
        server.createContext("/v1/ai/kb/documents", this::handle);
        server.start();
    }

    static FakeAiService start() {
        try {
            return new FakeAiService();
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    String baseUrl() {
        return "http://127.0.0.1:" + server.getAddress().getPort();
    }

    void reset() {
        requests.clear();
        responder = FakeAiService::chapNhan;
    }

    /** Trả lỗi đúng khuôn {@code {code, message}} của {@code src/api/errors.py}. */
    void traLoi(int status, String code, String message) {
        responder = r -> new Response(status, Map.of("code", code, "message", message), 0);
    }

    /** 202 như ai-service thật: MIME tra từ đuôi, version 1. */
    static Response chapNhan(Request r) {
        String ten = (String) r.body().get("file_name");
        String duoi = ten.substring(ten.lastIndexOf('.')).toLowerCase(Locale.ROOT);
        String[] dd = DINH_DANG.getOrDefault(duoi, new String[] {"TXT", "text/plain"});
        UUID id = UUID.randomUUID();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("document_id", id.toString());
        body.put("job_id", id.toString());
        body.put("title", r.body().get("title"));
        body.put("version", 1);
        body.put("status", "PENDING");
        body.put("source_type", dd[0]);
        body.put("mime_type", dd[1]);
        return new Response(202, body, 0);
    }

    private void handle(HttpExchange ex) throws IOException {
        try (ex) {
            Map<String, Object> body = json.readValue(ex.getRequestBody().readAllBytes(), new TypeReference<>() {
            });
            Request req = new Request(ex.getRequestHeaders().getFirst("X-Tenant-Id"),
                    ex.getRequestHeaders().getFirst("X-Trace-Id"),
                    ex.getRequestHeaders().getFirst("Content-Type"), body);
            requests.add(req);
            Response resp = responder.respond(req);
            if (resp.delayMs() > 0) {
                Thread.sleep(resp.delayMs());
            }
            byte[] out = json.writeValueAsString(resp.body()).getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().add("Content-Type", "application/json");
            ex.sendResponseHeaders(resp.status(), out.length);
            try (OutputStream os = ex.getResponseBody()) {
                os.write(out);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (IOException e) {
            // java-core đã bỏ chờ (ca quá thời gian) — ghi phản hồi hỏng là bình thường.
        }
    }

    @Override
    public void close() {
        server.stop(0);
        executor.shutdownNow();
    }
}
