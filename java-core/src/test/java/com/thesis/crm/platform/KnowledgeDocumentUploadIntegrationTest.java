package com.thesis.crm.platform;

import static java.nio.charset.StandardCharsets.UTF_8;
import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.text.Normalizer;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.checksums.RequestChecksumCalculation;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.S3Object;

/**
 * UC018 phía java-core, đầu-cuối qua HTTP thật (Tomcat thật — giới hạn multipart của servlet có
 * hiệu lực, MockMvc thì không).
 *
 * <p>Hạ tầng THẬT: Postgres chạy đủ V101–V116, ứng dụng nối bằng {@code crm_app} — role CHỊU RLS
 * (nối bằng {@code crm_owner} thì mọi kiểm tra cách ly tenant xanh giả vì chủ bảng bypass RLS);
 * RustFS cùng image với {@code docker-compose.yml}; JWT RS256 ký bằng khoá sinh trong test và đi
 * qua bộ giải mã thật của {@code SecurityConfig}. Chỉ ai-service là giả ({@link FakeAiService}).
 *
 * <p>Đây là chỗ DUY NHẤT đo được ca 409: ai-service không đọc được hạn mức gói.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class KnowledgeDocumentUploadIntegrationTest {

    static final UUID TENANT_A = UUID.fromString("11111111-1111-1111-1111-111111111111");
    static final UUID TENANT_B = UUID.fromString("22222222-2222-2222-2222-222222222222");
    /** Có doanh nghiệp, KHÔNG có thuê bao — ca SUBSCRIPTION_NOT_ACTIVE. */
    static final UUID TENANT_C = UUID.fromString("33333333-3333-3333-3333-333333333333");
    static final UUID SUB_A = UUID.fromString("aaaaaaaa-0000-0000-0000-00000000000a");
    static final UUID SUB_B = UUID.fromString("bbbbbbbb-0000-0000-0000-00000000000b");
    static final UUID ADMIN_A = UUID.fromString("aaaaaaaa-1111-0000-0000-000000000001");

    static final String BUCKET = "kb-tai-lieu";
    static final String S3_ACCESS = "kb-test";
    static final String S3_SECRET = "kb-test-secret"; // chỉ sống trong container dùng một lần
    static final int MIB = 1024 * 1024;
    /** Gói TRIAL của V102: max_documents = 20. */
    static final int QUOTA_TRIAL = 20;
    /** Gói TRIAL của V102: storage_mb = 100, lưu theo BYTE (ADR-0020 (c)). */
    static final long DUNG_LUONG_TRIAL = 100L * MIB;
    /** Chu kỳ ĐÃ HẾT của tenant B — ca chép mức tồn kho sang chu kỳ mới. */
    static final UUID SUB_B_CU = UUID.fromString("bbbbbbbb-0000-0000-0000-0000000000c0");

    @Container
    static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>(
            DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres"))
            .withDatabaseName("thesis_crm")
            .withUsername("crm_owner")
            .withPassword("changeme")
            // Tạo crm_app/ai_app và extension — đúng file compose dùng, chạy bằng psql lúc initdb.
            .withCopyFileToContainer(
                    MountableFile.forHostPath(Path.of("..", "scripts", "init-db.sql").toAbsolutePath()),
                    "/docker-entrypoint-initdb.d/00-init.sql");

    @Container
    static final GenericContainer<?> RUSTFS = new GenericContainer<>(DockerImageName.parse("rustfs/rustfs:1.0.0"))
            .withEnv("RUSTFS_ACCESS_KEY", S3_ACCESS)
            .withEnv("RUSTFS_SECRET_KEY", S3_SECRET)
            .withExposedPorts(9000)
            .waitingFor(Wait.forHttp("/health").forPort(9000).forStatusCode(200));

    static final FakeAiService AI = FakeAiService.start();
    static final KeyPair KHOA = taoCapKhoa();
    static final Path KHOA_CONG_KHAI = ghiKhoaCongKhai(KHOA);

    static S3Client s3;

    @DynamicPropertySource
    static void cauHinh(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", () -> "crm_app");
        r.add("spring.datasource.password", () -> "changeme");
        r.add("spring.flyway.user", () -> "crm_owner");
        r.add("spring.flyway.password", () -> "changeme");
        r.add("crm.storage.s3.endpoint", () -> RUSTFS.getHost() + ":" + RUSTFS.getMappedPort(9000));
        r.add("crm.storage.s3.access-key", () -> S3_ACCESS);
        r.add("crm.storage.s3.secret-key", () -> S3_SECRET);
        r.add("crm.security.jwt.public-key-location", () -> "file:" + KHOA_CONG_KHAI);
        // Tên dịch vụ "ai-service" vẫn đi qua LoadBalancer — chỉ danh sách instance trỏ vào bản giả.
        r.add("spring.cloud.discovery.client.simple.instances.ai-service[0].uri", AI::baseUrl);
        r.add("crm.ai-service.read-timeout", () -> "2s");
        r.add("eureka.client.enabled", () -> "false");
        // Không có Kafka ở đây: job phát sẽ khoá và thử kết nối mỗi 500 ms. Test đếm dòng outbox
        // CHƯA phát — job phát có test riêng (OutboxPublisherIntegrationTest).
        r.add("crm.outbox.publisher.enabled", () -> "false");
    }

    @LocalServerPort
    int port;

    final HttpClient http = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
    final ObjectMapper json = new ObjectMapper();

    record KetQua(int status, JsonNode body) {
        String code() {
            return body.path("code").asText(null);
        }
    }

    @BeforeAll
    static void taoBucket() {
        s3 = S3Client.builder()
                .endpointOverride(URI.create("http://" + RUSTFS.getHost() + ":" + RUSTFS.getMappedPort(9000)))
                .forcePathStyle(true)
                .region(Region.US_EAST_1)
                .requestChecksumCalculation(RequestChecksumCalculation.WHEN_REQUIRED)
                .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create(S3_ACCESS, S3_SECRET)))
                .build();
        s3.createBucket(b -> b.bucket(BUCKET));
    }

    @AfterAll
    static void dong() {
        AI.close();
        s3.close();
    }

    /**
     * Gieo ở {@code @BeforeEach} chứ không {@code @BeforeAll}: bảng do Flyway tạo lúc Spring dựng
     * context, mà context dựng SAU {@code @BeforeAll}. Câu gieo idempotent nên chạy lại vô hại.
     */
    @BeforeEach
    void datLai() throws SQLException {
        chay("""
                INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES
                    ('%s', 'Doanh nghiệp A', 'dn-a', 'a@example.test'),
                    ('%s', 'Doanh nghiệp B', 'dn-b', 'b@example.test'),
                    ('%s', 'Doanh nghiệp C', 'dn-c', 'c@example.test')
                ON CONFLICT (id) DO NOTHING
                """.formatted(TENANT_A, TENANT_B, TENANT_C));
        chay("""
                INSERT INTO platform.tenant_subscriptions (id, tenant_id, plan_id, status, period_start, period_end)
                SELECT v.id, v.tenant, p.id, 'TRIALING', now() - interval '1 day', now() + interval '29 days'
                  FROM (VALUES ('%s'::uuid, '%s'::uuid), ('%s'::uuid, '%s'::uuid)) AS v(id, tenant)
                 CROSS JOIN platform.subscription_plans p
                 WHERE p.code = 'TRIAL'
                ON CONFLICT (id) DO NOTHING
                """.formatted(SUB_A, TENANT_A, SUB_B, TENANT_B));
        chay("DELETE FROM platform.usage_records");
        chay("DELETE FROM platform.outbox_events");
        for (String key : s3Keys()) {
            s3.deleteObject(b -> b.bucket(BUCKET).key(key));
        }
        AI.reset();
    }

    // ── Luồng chính ──────────────────────────────────────────────────────────────

    @Test
    void nhanTepHopLe202GhiS3GoiAiServiceVaGhiOutbox() throws Exception {
        byte[] pdf = "%PDF-1.7\nbang gia".getBytes(UTF_8);

        KetQua kq = taiLen(tokenAdmin(TENANT_A), "Bảng giá 2026.pdf", pdf,
                truong("title", "  Bảng giá sản phẩm 2026  ", "description", "Giá niêm yết"), "trace-uc018-1");

        assertThat(kq.status()).as(kq.body().toString()).isEqualTo(202);
        JsonNode data = kq.body().path("data");
        UUID documentId = UUID.fromString(data.path("id").asText());
        assertThat(data.path("jobId").asText()).isEqualTo(documentId.toString());
        assertThat(data.path("title").asText()).isEqualTo("Bảng giá sản phẩm 2026");
        assertThat(data.path("status").asText()).isEqualTo("PENDING");
        assertThat(data.path("sourceType").asText()).isEqualTo("PDF");
        assertThat(data.path("fileName").asText()).isEqualTo("Bảng giá 2026.pdf");
        assertThat(data.path("sizeBytes").asLong()).isEqualTo(pdf.length);
        assertThat(data.path("language").asText()).isEqualTo("vi");
        assertThat(data.path("chunkCount").asInt()).isZero();
        assertThat(data.path("documentQuota").path("used").asLong()).isEqualTo(1);
        assertThat(data.path("documentQuota").path("quota").asLong()).isEqualTo(QUOTA_TRIAL);
        assertThat(data.path("storageQuota").path("used").asLong()).isEqualTo(pdf.length);
        assertThat(data.path("storageQuota").path("quota").asLong()).isEqualTo(DUNG_LUONG_TRIAL);
        assertThat(hanMuc(TENANT_A, "STORAGE_MB")).containsEntry("used_value", (long) pdf.length)
                .containsEntry("quota_value", DUNG_LUONG_TRIAL);

        // Kho S3: đúng một object, dưới thư mục của tenant trong JWT, tên đã làm sạch.
        List<String> keys = s3Keys();
        assertThat(keys).hasSize(1);
        assertThat(keys.get(0)).matches(TENANT_A + "/[0-9a-f-]{36}/Bảng-giá-2026\\.pdf");
        assertThat(s3.getObjectAsBytes(b -> b.bucket(BUCKET).key(keys.get(0))).asByteArray()).isEqualTo(pdf);

        // ai-service: tenant ở header, KHÔNG ở thân; thân đúng sáu trường của KbDocumentCreate.
        assertThat(AI.requests).hasSize(1);
        FakeAiService.Request goi = AI.requests.get(0);
        assertThat(goi.tenantId()).isEqualTo(TENANT_A.toString());
        assertThat(goi.traceId()).isEqualTo("trace-uc018-1");
        assertThat(goi.contentType()).startsWith("application/json");
        assertThat(goi.body()).containsOnlyKeys("file_uri", "file_name", "title", "description", "language",
                "uploaded_by");
        assertThat(goi.body())
                .containsEntry("file_uri", "s3://" + BUCKET + "/" + keys.get(0))
                .containsEntry("file_name", "Bảng giá 2026.pdf")
                .containsEntry("title", "Bảng giá sản phẩm 2026")
                .containsEntry("description", "Giá niêm yết")
                .containsEntry("language", "vi")
                .containsEntry("uploaded_by", ADMIN_A.toString());

        // Hạn mức: dòng tạo lần đầu, quota CHÉP từ gói TRIAL.
        Map<String, Object> hanMuc = hanMuc(TENANT_A);
        assertThat(hanMuc).containsEntry("used_value", 1L).containsEntry("quota_value", (long) QUOTA_TRIAL);
        assertThat(hanMuc.get("warned_at")).isNull();

        // Outbox: một sự kiện, cùng tenant, trace ở header chứ không ở payload.
        List<Map<String, Object>> suKien = outbox();
        assertThat(suKien).hasSize(1);
        Map<String, Object> e = suKien.get(0);
        assertThat(e).containsEntry("tenant_id", TENANT_A.toString())
                .containsEntry("aggregate_type", "document")
                .containsEntry("aggregate_id", documentId.toString())
                .containsEntry("event_type", "DocumentUploaded")
                .containsEntry("topic", "crm.kb.document.uploaded");
        JsonNode payload = json.readTree((String) e.get("payload"));
        assertThat(payload.path("document_id").asText()).isEqualTo(documentId.toString());
        assertThat(payload.path("version").asInt()).isEqualTo(1);
        assertThat(payload.path("source_type").asText()).isEqualTo("PDF");
        assertThat(payload.path("size_bytes").asLong()).isEqualTo(pdf.length);
        assertThat(payload.path("uploaded_by").asText()).isEqualTo(ADMIN_A.toString());
        assertThat(payload.has("title")).as("payload không mang dữ liệu người dùng nhập").isFalse();
        assertThat(json.readTree((String) e.get("headers")).path("X-Trace-Id").asText()).isEqualTo("trace-uc018-1");
    }

    @Test
    void boQuaTenantTrongForm() throws Exception {
        KetQua kq = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8),
                truong("title", "Leo tenant", "tenantId", TENANT_B.toString(), "tenant_id", TENANT_B.toString()));

        assertThat(kq.status()).isEqualTo(202);
        assertThat(s3Keys()).singleElement().asString().startsWith(TENANT_A + "/");
        assertThat(AI.requests.get(0).tenantId()).isEqualTo(TENANT_A.toString());
        assertThat(AI.requests.get(0).body()).doesNotContainKeys("tenant_id", "tenantId");
        assertThat(hanMuc(TENANT_B)).isNull();
    }

    // ── 413 · 422 · 415 — kiểm rẻ, chưa ghi gì ──────────────────────────────────

    @Test
    void tepDung20MiBDuocNhan() throws Exception {
        KetQua kq = taiLen(tokenAdmin(TENANT_A), "vua-dung.pdf", pdfCoDungLuong(20 * MIB), truong("title", "Vừa đúng"));

        assertThat(kq.status()).as(kq.body().toString()).isEqualTo(202);
        assertThat(kq.body().at("/data/sizeBytes").asLong()).isEqualTo(20L * MIB);
    }

    @Test
    void tepVuot20MiB413TruocKhiDocForm() throws Exception {
        // Tiêu đề sai VÀ đuôi sai: 413 vẫn thắng — servlet chặn trước khi Spring bind form.
        KetQua kq = taiLen(tokenAdmin(TENANT_A), "qua-lon.xlsx", pdfCoDungLuong(20 * MIB + 1), truong("title", "x"));

        assertThat(kq.status()).isEqualTo(413);
        assertThat(kq.code()).isEqualTo("FILE_TOO_LARGE");
        khongGhiGiCa();
    }

    @Test
    void tieuDeSaiDoDai422() throws Exception {
        for (String tieuDe : List.of("ab", "   a  ", "x".repeat(256))) {
            KetQua kq = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", tieuDe));
            assertThat(kq.status()).as(tieuDe).isEqualTo(422);
            assertThat(kq.code()).isEqualTo("INVALID_METADATA");
        }
        KetQua thieu = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong());
        assertThat(thieu.status()).isEqualTo(422);
        khongGhiGiCa();
    }

    @Test
    void tieuDeNfdDemSauKhiChuanHoaNfc() throws Exception {
        // 255 chữ "ệ" dạng NFD = 765 code point. Đếm trước NFC thì bị 422 oan.
        String nfd255 = Normalizer.normalize("ệ".repeat(255), Normalizer.Form.NFD);
        assertThat(nfd255.codePointCount(0, nfd255.length())).isEqualTo(765);

        KetQua ok = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", nfd255));
        assertThat(ok.status()).as(ok.body().toString()).isEqualTo(202);
        assertThat(AI.requests.get(0).body().get("title")).isEqualTo("ệ".repeat(255));

        String nfd256 = Normalizer.normalize("ệ".repeat(256), Normalizer.Form.NFD);
        assertThat(taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", nfd256)).status())
                .isEqualTo(422);
    }

    @Test
    void ngonNguVaMoTa422() throws Exception {
        KetQua sai = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8),
                truong("title", "Tiếng Pháp", "language", "fr"));
        assertThat(sai.status()).isEqualTo(422);

        KetQua moTaDai = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8),
                truong("title", "Mô tả dài", "description", "m".repeat(501)));
        assertThat(moTaDai.status()).isEqualTo(422);

        KetQua ok = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8),
                truong("title", "Mô tả trắng", "description", "   ", "language", "en"));
        assertThat(ok.status()).isEqualTo(202);
        assertThat(AI.requests.get(0).body()).containsEntry("description", null).containsEntry("language", "en");
    }

    @Test
    void thieuTep422() throws Exception {
        KetQua kq = taiLen(tokenAdmin(TENANT_A), null, null, truong("title", "Không có tệp"));
        assertThat(kq.status()).isEqualTo(422);
        assertThat(kq.code()).isEqualTo("INVALID_METADATA");
    }

    @Test
    void duoiKhongHoTro415() throws Exception {
        for (String ten : List.of("bang-tinh.xlsx", "khong-duoi", ".pdf", "anh.png")) {
            KetQua kq = taiLen(tokenAdmin(TENANT_A), ten, "x".getBytes(UTF_8), truong("title", "Sai đuôi"));
            assertThat(kq.status()).as(ten).isEqualTo(415);
            assertThat(kq.code()).isEqualTo("UNSUPPORTED_FORMAT");
        }
        khongGhiGiCa();
    }

    // ── 401 · 403 ────────────────────────────────────────────────────────────────

    @Test
    void xacThuc401() throws Exception {
        byte[] x = "x".getBytes(UTF_8);
        Map<String, String> f = truong("title", "Không token");
        Instant now = Instant.now();

        assertThat(taiLen(null, "a.txt", x, f).status()).isEqualTo(401);
        // Thiếu tenantId, tenantId không phải UUID chuẩn, hết hạn, ký bằng khoá lạ.
        assertThat(taiLen(ky(KHOA, Map.of("sub", ADMIN_A.toString(), "roleCode", "TENANT_ADMIN"), now), "a.txt", x, f)
                .status()).isEqualTo(401);
        assertThat(taiLen(ky(KHOA, Map.of("sub", ADMIN_A.toString(), "roleCode", "TENANT_ADMIN",
                "tenantId", "1-1-1-1-1"), now), "a.txt", x, f).status()).isEqualTo(401);
        assertThat(taiLen(ky(KHOA, claims(TENANT_A, "TENANT_ADMIN"), now.minusSeconds(3600)), "a.txt", x, f)
                .status()).isEqualTo(401);
        KetQua khoaLa = taiLen(ky(taoCapKhoa(), claims(TENANT_A, "TENANT_ADMIN"), now), "a.txt", x, f);
        assertThat(khoaLa.status()).isEqualTo(401);
        assertThat(khoaLa.code()).isEqualTo("UNAUTHORIZED");
        assertThat(khoaLa.body().path("traceId").asText()).isNotBlank();
        khongGhiGiCa();
    }

    @Test
    void vaiTroAgent403TruocCa413() throws Exception {
        String agent = ky(KHOA, claims(TENANT_A, "AGENT"), Instant.now());

        KetQua nho = taiLen(agent, "a.txt", "x".getBytes(UTF_8), truong("title", "Agent"));
        assertThat(nho.status()).isEqualTo(403);
        assertThat(nho.code()).isEqualTo("FORBIDDEN");
        // Người thiếu quyền bị chặn trước khi servlet đọc tệp: không nhận 413.
        assertThat(taiLen(agent, "a.txt", pdfCoDungLuong(20 * MIB + 1), truong("title", "x")).status()).isEqualTo(403);
        khongGhiGiCa();
    }

    // ── 409 · 80% · 100% ─────────────────────────────────────────────────────────

    @Test
    void hetHanMuc409KhongGhiS3KhongGoiAi() throws Exception {
        datHanMuc(TENANT_A, SUB_A, QUOTA_TRIAL, QUOTA_TRIAL);

        KetQua kq = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", "Tài liệu thứ 21"));

        assertThat(kq.status()).isEqualTo(409);
        assertThat(kq.code()).isEqualTo("DOCUMENT_QUOTA_EXCEEDED");
        assertThat(kq.body().at("/data/used").asLong()).isEqualTo(QUOTA_TRIAL);
        assertThat(kq.body().at("/data/quota").asLong()).isEqualTo(QUOTA_TRIAL);
        assertThat(s3Keys()).isEmpty();
        assertThat(AI.requests).isEmpty();
        assertThat(outbox()).isEmpty();
        // Dòng gieo sẵn chưa có mốc (như khi gói bị hạ giữa chu kỳ): lần từ chối ghi mốc và
        // mốc đó được COMMIT dù phản hồi là lỗi.
        Map<String, Object> hanMuc = hanMuc(TENANT_A);
        assertThat(hanMuc).containsEntry("used_value", (long) QUOTA_TRIAL);
        assertThat(hanMuc.get("warned_at")).isNotNull();
        assertThat(hanMuc.get("blocked_at")).isNotNull();
    }

    @Test
    void cham80PhanTramGhiWarnedAt() throws Exception {
        datHanMuc(TENANT_A, SUB_A, 15, QUOTA_TRIAL);

        KetQua kq = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", "Tài liệu thứ 16"));

        assertThat(kq.status()).isEqualTo(202);
        JsonNode q = kq.body().at("/data/documentQuota");
        assertThat(q.path("used").asLong()).isEqualTo(16);
        assertThat(q.path("percent").asDouble()).isEqualTo(80.0);
        assertThat(q.path("warnedAt").isNull()).isFalse();
        assertThat(q.path("blockedAt").isNull()).isTrue();
        Instant moc = (Instant) hanMuc(TENANT_A).get("warned_at");
        assertThat(moc).isNotNull();

        // Lượt kế tiếp vẫn trên 80%: mốc KHÔNG bị ghi đè.
        taiLen(tokenAdmin(TENANT_A), "b.txt", "x".getBytes(UTF_8), truong("title", "Tài liệu thứ 17"));
        assertThat(hanMuc(TENANT_A)).containsEntry("used_value", 17L).containsEntry("warned_at", moc);
    }

    @Test
    void cham100PhanTramRoiChan() throws Exception {
        datHanMuc(TENANT_A, SUB_A, 19, QUOTA_TRIAL);

        KetQua cuoi = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", "Tài liệu thứ 20"));
        assertThat(cuoi.status()).isEqualTo(202);
        assertThat(cuoi.body().at("/data/documentQuota/blockedAt").isNull()).isFalse();
        assertThat(cuoi.body().at("/data/documentQuota/percent").asDouble()).isEqualTo(100.0);

        KetQua tuChoi = taiLen(tokenAdmin(TENANT_A), "b.txt", "x".getBytes(UTF_8), truong("title", "Tài liệu thứ 21"));
        assertThat(tuChoi.status()).isEqualTo(409);
        assertThat(hanMuc(TENANT_A)).containsEntry("used_value", 20L);
        assertThat(outbox()).hasSize(1);
    }

    /**
     * Bẫy chính của hạn mức. Không có {@code SELECT … FOR UPDATE}, sáu lượt cùng đọc 19/20, cùng
     * được ai-service nhận, và mất cập nhật: sáu tài liệu nằm trong kho mà bộ đếm chỉ lên 20.
     */
    @Test
    void sauLuotDongThoiKhiConMotCho() throws Exception {
        datHanMuc(TENANT_A, SUB_A, QUOTA_TRIAL - 1, QUOTA_TRIAL);
        // ai-service chậm để các lượt thật sự chồng lên nhau trong lúc lượt đầu giữ khoá.
        AI.responder = r -> new FakeAiService.Response(202, FakeAiService.chapNhan(r).body(), 300);
        String token = tokenAdmin(TENANT_A);
        int soLuot = 6;
        CountDownLatch xuatPhat = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(soLuot);
        List<Future<KetQua>> ketQua = new ArrayList<>();
        for (int i = 0; i < soLuot; i++) {
            String ten = "dong-thoi-" + i + ".txt";
            ketQua.add(pool.submit(() -> {
                xuatPhat.await();
                return taiLen(token, ten, "x".getBytes(UTF_8), truong("title", "Đồng thời " + ten));
            }));
        }
        xuatPhat.countDown();
        List<Integer> ma = new ArrayList<>();
        for (Future<KetQua> f : ketQua) {
            ma.add(f.get().status());
        }
        pool.shutdown();

        assertThat(ma).as(ma.toString()).containsOnly(202, 409);
        assertThat(ma.stream().filter(m -> m == 202)).hasSize(1);
        assertThat(AI.requests).hasSize(1);
        assertThat(s3Keys()).hasSize(1);
        assertThat(outbox()).hasSize(1);
        assertThat(hanMuc(TENANT_A)).containsEntry("used_value", (long) QUOTA_TRIAL);
    }

    @Test
    void hanMucTachTheoTenant() throws Exception {
        datHanMuc(TENANT_A, SUB_A, QUOTA_TRIAL, QUOTA_TRIAL);

        assertThat(taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", "A hết chỗ")).status())
                .isEqualTo(409);
        KetQua b = taiLen(tokenAdmin(TENANT_B), "b.txt", "x".getBytes(UTF_8), truong("title", "B còn chỗ"));
        assertThat(b.status()).isEqualTo(202);
        assertThat(hanMuc(TENANT_B)).containsEntry("used_value", 1L);
        assertThat(hanMuc(TENANT_A)).containsEntry("used_value", (long) QUOTA_TRIAL);
    }

    /**
     * Dung lượng tính theo BYTE đang có (ADR-0020). Tệp làm VƯỢT trần bị chặn dù mức dùng chưa đủ
     * 100% — và lần bị chặn đó ghi {@code blocked_at}. Tệp lấp ĐÚNG trần thì vẫn được nhận.
     */
    @Test
    void hetDungLuong409TheoByte() throws Exception {
        datHanMuc(TENANT_A, SUB_A, "STORAGE_MB", DUNG_LUONG_TRIAL - 10, DUNG_LUONG_TRIAL);

        KetQua vuot = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".repeat(11).getBytes(UTF_8), truong("title", "Vượt 1 byte"));
        assertThat(vuot.status()).isEqualTo(409);
        assertThat(vuot.code()).isEqualTo("STORAGE_MB_QUOTA_EXCEEDED");
        assertThat(vuot.body().path("message").asText()).contains("MB");
        khongGhiGiCa();
        Map<String, Object> dungLuong = hanMuc(TENANT_A, "STORAGE_MB");
        assertThat(dungLuong).containsEntry("used_value", DUNG_LUONG_TRIAL - 10);
        assertThat(dungLuong.get("warned_at")).isNotNull();
        assertThat(dungLuong.get("blocked_at")).as("lần bị chặn là chạm trần").isNotNull();

        KetQua vuaKhit = taiLen(tokenAdmin(TENANT_A), "b.txt", "x".repeat(10).getBytes(UTF_8), truong("title", "Vừa khít"));
        assertThat(vuaKhit.status()).isEqualTo(202);
        assertThat(vuaKhit.body().at("/data/storageQuota/percent").asDouble()).isEqualTo(100.0);
        assertThat(hanMuc(TENANT_A, "STORAGE_MB")).containsEntry("used_value", DUNG_LUONG_TRIAL);
    }

    /**
     * Hạn mức tài liệu là lượng ĐANG CÓ (ADR-0020 (d)): sang chu kỳ mới, dòng hạn mức mới chép mức
     * tồn kho của chu kỳ trước chứ không về 0 — 7 tài liệu đang có thì lượt tải đầu chu kỳ là thứ 8.
     */
    @Test
    void chuKyMoiChepMucTonKho() throws Exception {
        chay("""
                INSERT INTO platform.tenant_subscriptions (id, tenant_id, plan_id, status, period_start, period_end)
                SELECT '%s', '%s', p.id, 'EXPIRED', now() - interval '31 days', now() - interval '1 day'
                  FROM platform.subscription_plans p WHERE p.code = 'TRIAL'
                ON CONFLICT (id) DO NOTHING
                """.formatted(SUB_B_CU, TENANT_B));
        datHanMuc(TENANT_B, SUB_B_CU, "DOCUMENT", 7, QUOTA_TRIAL);
        datHanMuc(TENANT_B, SUB_B_CU, "STORAGE_MB", 5000, DUNG_LUONG_TRIAL);
        byte[] tep = "noi dung".getBytes(UTF_8);

        KetQua kq = taiLen(tokenAdmin(TENANT_B), "b.txt", tep, truong("title", "Đầu chu kỳ mới"));

        assertThat(kq.status()).as(kq.body().toString()).isEqualTo(202);
        assertThat(kq.body().at("/data/documentQuota/used").asLong()).isEqualTo(8);
        assertThat(kq.body().at("/data/storageQuota/used").asLong()).isEqualTo(5000 + tep.length);
        assertThat(hanMuc(TENANT_B, "DOCUMENT")).containsEntry("used_value", 8L);
    }

    @Test
    void khongCoThueBao409() throws Exception {
        KetQua kq = taiLen(tokenAdmin(TENANT_C), "a.txt", "x".getBytes(UTF_8), truong("title", "Chưa mua gói"));

        assertThat(kq.status()).isEqualTo(409);
        assertThat(kq.code()).isEqualTo("SUBSCRIPTION_NOT_ACTIVE");
        khongGhiGiCa();
    }

    // ── ai-service từ chối: xoá object vừa ghi, không cộng hạn mức, không sự kiện ──

    @Test
    void aiServiceTuChoiNoiDung415() throws Exception {
        AI.traLoi(415, "UNSUPPORTED_FORMAT", "Đuôi '.pdf' nhưng nội dung không phải PDF");

        KetQua kq = taiLen(tokenAdmin(TENANT_A), "anh-doi-duoi.pdf", "\u0089PNG".getBytes(UTF_8),
                truong("title", "Ảnh đổi đuôi"));

        assertThat(kq.status()).isEqualTo(415);
        assertThat(kq.code()).isEqualTo("UNSUPPORTED_FORMAT");
        assertThat(kq.body().path("message").asText()).isEqualTo("Đuôi '.pdf' nhưng nội dung không phải PDF");
        assertThat(AI.requests).hasSize(1);
        daDonSachSauKhiGoiAi();
    }

    @Test
    void aiServiceLoi5xxHoacQuaHan503() throws Exception {
        AI.traLoi(500, "INTERNAL_ERROR", "Lỗi nội bộ ai-service");
        KetQua loi500 = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", "AI lỗi"));
        assertThat(loi500.status()).isEqualTo(503);
        assertThat(loi500.code()).isEqualTo("AI_SERVICE_UNAVAILABLE");
        daDonSachSauKhiGoiAi();

        AI.traLoi(503, "STORAGE_UNAVAILABLE", "Không kết nối được kho S3");
        KetQua khoChet = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", "Kho chết"));
        assertThat(khoChet.status()).isEqualTo(503);
        assertThat(khoChet.code()).isEqualTo("STORAGE_UNAVAILABLE");
        daDonSachSauKhiGoiAi();

        // Chậm hơn read-timeout (2 s trong test).
        AI.responder = r -> new FakeAiService.Response(202, FakeAiService.chapNhan(r).body(), 4000);
        KetQua quaHan = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", "AI chậm"));
        assertThat(quaHan.status()).isEqualTo(503);
        assertThat(quaHan.code()).isEqualTo("AI_SERVICE_UNAVAILABLE");
        daDonSachSauKhiGoiAi();
    }

    @Test
    void lechHopDongVoiAiService500() throws Exception {
        AI.traLoi(403, "FORBIDDEN_FILE_URI", "Key không nằm trong thư mục của tenant đang gọi");

        KetQua kq = taiLen(tokenAdmin(TENANT_A), "a.txt", "x".getBytes(UTF_8), truong("title", "URI lệch"));

        assertThat(kq.status()).isEqualTo(500);
        assertThat(kq.code()).isEqualTo("INTERNAL_ERROR");
        // Không lộ thông điệp nội bộ của ai-service cho người dùng.
        assertThat(kq.body().path("message").asText()).isEqualTo("Lỗi nội bộ");
        daDonSachSauKhiGoiAi();
    }

    // ── Tiện ích ─────────────────────────────────────────────────────────────────

    private void khongGhiGiCa() throws SQLException {
        assertThat(s3Keys()).as("không object nào trên S3").isEmpty();
        assertThat(AI.requests).as("không gọi ai-service").isEmpty();
        assertThat(outbox()).as("không sự kiện").isEmpty();
    }

    /** Đã gọi ai-service nhưng bị từ chối: object bị xoá, hạn mức không đổi, không sự kiện. */
    private void daDonSachSauKhiGoiAi() throws SQLException {
        assertThat(s3Keys()).as("object vừa ghi phải bị xoá").isEmpty();
        assertThat(outbox()).isEmpty();
        for (String metric : List.of("DOCUMENT", "STORAGE_MB")) {
            Map<String, Object> hanMuc = hanMuc(TENANT_A, metric);
            assertThat(hanMuc == null ? 0L : hanMuc.get("used_value")).as(metric).isEqualTo(0L);
        }
    }

    private KetQua taiLen(String token, String tenTep, byte[] noiDung, Map<String, String> truong) throws Exception {
        return taiLen(token, tenTep, noiDung, truong, null);
    }

    /** Dựng multipart bằng tay như trình duyệt: tên tệp UTF-8 thô, phần văn bản không khai charset. */
    private KetQua taiLen(String token, String tenTep, byte[] noiDung, Map<String, String> truong, String traceId)
            throws Exception {
        String bien = "----bien" + UUID.randomUUID();
        ByteArrayOutputStream out = new ByteArrayOutputStream((noiDung == null ? 0 : noiDung.length) + 2048);
        for (Map.Entry<String, String> e : truong.entrySet()) {
            out.write(("--" + bien + "\r\nContent-Disposition: form-data; name=\"" + e.getKey() + "\"\r\n\r\n")
                    .getBytes(UTF_8));
            out.write(e.getValue().getBytes(UTF_8));
            out.write("\r\n".getBytes(UTF_8));
        }
        if (tenTep != null) {
            out.write(("--" + bien + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"" + tenTep
                    + "\"\r\nContent-Type: application/octet-stream\r\n\r\n").getBytes(UTF_8));
            out.write(noiDung);
            out.write("\r\n".getBytes(UTF_8));
        }
        out.write(("--" + bien + "--\r\n").getBytes(UTF_8));

        HttpRequest.Builder req = HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/api/v1/documents"))
                .header("Content-Type", "multipart/form-data; boundary=" + bien)
                .POST(HttpRequest.BodyPublishers.ofByteArray(out.toByteArray()));
        if (token != null) {
            req.header("Authorization", "Bearer " + token);
        }
        if (traceId != null) {
            req.header("X-Trace-Id", traceId);
        }
        HttpResponse<String> resp = http.send(req.build(), HttpResponse.BodyHandlers.ofString(UTF_8));
        JsonNode body = resp.body().isBlank() ? json.createObjectNode() : json.readTree(resp.body());
        return new KetQua(resp.statusCode(), body);
    }

    private static Map<String, String> truong(String... cap) {
        Map<String, String> m = new LinkedHashMap<>();
        for (int i = 0; i < cap.length; i += 2) {
            m.put(cap[i], cap[i + 1]);
        }
        return m;
    }

    private static byte[] pdfCoDungLuong(int soByte) {
        byte[] b = new byte[soByte];
        byte[] dau = "%PDF-1.7\n".getBytes(UTF_8);
        System.arraycopy(dau, 0, b, 0, dau.length);
        return b;
    }

    private static List<String> s3Keys() {
        return s3.listObjectsV2Paginator(b -> b.bucket(BUCKET)).contents().stream().map(S3Object::key).toList();
    }

    // ── CSDL — nối bằng crm_owner (bypass RLS) để gieo và soi, KHÔNG phải đường của ứng dụng ──

    private static Connection chuBang() throws SQLException {
        return DriverManager.getConnection(PG.getJdbcUrl(), "crm_owner", "changeme");
    }

    private static void chay(String sql) throws SQLException {
        try (Connection c = chuBang(); Statement s = c.createStatement()) {
            s.execute(sql);
        }
    }

    private static void datHanMuc(UUID tenant, UUID sub, long used, long quota) throws SQLException {
        datHanMuc(tenant, sub, "DOCUMENT", used, quota);
    }

    private static void datHanMuc(UUID tenant, UUID sub, String metric, long used, long quota) throws SQLException {
        try (Connection c = chuBang(); PreparedStatement ps = c.prepareStatement("""
                INSERT INTO platform.usage_records (tenant_id, subscription_id, metric, used_value, quota_value)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (subscription_id, metric) DO UPDATE
                   SET used_value = EXCLUDED.used_value, quota_value = EXCLUDED.quota_value,
                       warned_at = NULL, blocked_at = NULL
                """)) {
            ps.setObject(1, tenant);
            ps.setObject(2, sub);
            ps.setString(3, metric);
            ps.setLong(4, used);
            ps.setLong(5, quota);
            ps.executeUpdate();
        }
    }

    private static Map<String, Object> hanMuc(UUID tenant) throws SQLException {
        return hanMuc(tenant, "DOCUMENT");
    }

    /** Dòng hạn mức của chu kỳ ĐANG HIỆU LỰC (bỏ qua dòng của chu kỳ cũ). */
    private static Map<String, Object> hanMuc(UUID tenant, String metric) throws SQLException {
        try (Connection c = chuBang(); PreparedStatement ps = c.prepareStatement("""
                SELECT u.used_value, u.quota_value, u.warned_at, u.blocked_at
                  FROM platform.usage_records u
                  JOIN platform.tenant_subscriptions s ON s.id = u.subscription_id
                 WHERE u.tenant_id = ? AND u.metric = ? AND s.period_end > now()
                """)) {
            ps.setObject(1, tenant);
            ps.setString(2, metric);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                Map<String, Object> m = new HashMap<>();
                m.put("used_value", rs.getLong("used_value"));
                m.put("quota_value", rs.getLong("quota_value"));
                m.put("warned_at", thoiDiem(rs, "warned_at"));
                m.put("blocked_at", thoiDiem(rs, "blocked_at"));
                return m;
            }
        }
    }

    private static Instant thoiDiem(ResultSet rs, String cot) throws SQLException {
        java.sql.Timestamp t = rs.getTimestamp(cot);
        return t == null ? null : t.toInstant();
    }

    private static List<Map<String, Object>> outbox() throws SQLException {
        List<Map<String, Object>> ds = new ArrayList<>();
        try (Connection c = chuBang(); Statement s = c.createStatement(); ResultSet rs = s.executeQuery("""
                SELECT tenant_id::text, aggregate_type, aggregate_id::text, event_type, topic,
                       payload::text, headers::text
                  FROM platform.outbox_events ORDER BY id
                """)) {
            while (rs.next()) {
                Map<String, Object> m = new HashMap<>();
                m.put("tenant_id", rs.getString(1));
                m.put("aggregate_type", rs.getString(2));
                m.put("aggregate_id", rs.getString(3));
                m.put("event_type", rs.getString(4));
                m.put("topic", rs.getString(5));
                m.put("payload", rs.getString(6));
                m.put("headers", rs.getString(7));
                ds.add(m);
            }
        }
        return ds;
    }

    // ── JWT ─────────────────────────────────────────────────────────────────────

    private static String tokenAdmin(UUID tenant) {
        return ky(KHOA, claims(tenant, "TENANT_ADMIN"), Instant.now());
    }

    private static Map<String, Object> claims(UUID tenant, String vaiTro) {
        return Map.of("sub", ADMIN_A.toString(), "tenantId", tenant.toString(), "roleCode", vaiTro);
    }

    /** Ký RS256 như java-core sẽ phát hành ở UC002 — claim theo securitySchemes.tenantJwt. */
    private static String ky(KeyPair khoa, Map<String, Object> claims, Instant phatHanh) {
        JWTClaimsSet.Builder b = new JWTClaimsSet.Builder()
                .issueTime(Date.from(phatHanh))
                .expirationTime(Date.from(phatHanh.plusSeconds(600)));
        claims.forEach(b::claim);
        SignedJWT jwt = new SignedJWT(new JWSHeader(JWSAlgorithm.RS256), b.build());
        try {
            jwt.sign(new RSASSASigner(khoa.getPrivate()));
        } catch (JOSEException e) {
            throw new IllegalStateException(e);
        }
        return jwt.serialize();
    }

    private static KeyPair taoCapKhoa() {
        try {
            KeyPairGenerator g = KeyPairGenerator.getInstance("RSA");
            g.initialize(2048);
            return g.generateKeyPair();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static Path ghiKhoaCongKhai(KeyPair khoa) {
        String pem = "-----BEGIN PUBLIC KEY-----\n"
                + Base64.getMimeEncoder(64, "\n".getBytes(UTF_8)).encodeToString(khoa.getPublic().getEncoded())
                + "\n-----END PUBLIC KEY-----\n";
        try {
            Path p = Files.createTempFile("jwt-test-", ".pem");
            Files.writeString(p, pem);
            p.toFile().deleteOnExit();
            return p;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
