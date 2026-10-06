package com.thesis.crm.engagement;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;

/**
 * Nền chung cho test tích hợp nhóm engagement (UC016, UC017): Postgres THẬT (pgvector:pg16, cùng
 * image docker-compose), Flyway thật, role runtime {@code crm_app} — H2 không có RLS.
 *
 * <p>Container và dữ liệu nền (2 doanh nghiệp, mỗi doanh nghiệp một quản trị viên + một nhân viên)
 * dùng chung cho mọi lớp con; Spring tái dùng cùng một context vì cấu hình giống nhau.
 */
@SpringBootTest
@AutoConfigureMockMvc
abstract class EngagementIntegrationTestBase {

    static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>(
            DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres"))
            .withDatabaseName("thesis_crm")
            .withUsername("crm_owner")
            .withPassword("changeme")
            .withCopyFileToContainer(
                    MountableFile.forHostPath(Path.of("..", "scripts", "init-db.sql").toAbsolutePath()),
                    "/docker-entrypoint-initdb.d/00-init.sql");

    /** Redis thật cho phần chống spam của widget (UC010) — cùng image docker-compose. */
    static final GenericContainer<?> REDIS =
            new GenericContainer<>(DockerImageName.parse("redis:7-alpine")).withExposedPorts(6379);

    /** ai-service giả: trả lời theo kịch bản từng test, không gọi LLM thật (kết quả lặp lại được). */
    static final FakeAiServer AI = FakeAiServer.start();

    static {
        PG.start();
        REDIS.start();
    }

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", () -> "crm_app");
        r.add("spring.datasource.password", () -> "changeme");
        r.add("spring.flyway.user", () -> "crm_owner");
        r.add("spring.flyway.password", () -> "changeme");
        r.add("eureka.client.enabled", () -> "false");
        r.add("spring.data.redis.host", REDIS::getHost);
        r.add("spring.data.redis.port", () -> REDIS.getMappedPort(6379));
        r.add("ai-service.url", AI::baseUrl);
        r.add("ai-service.chat-timeout", () -> "2s");
        // Job quá hạn hàng chờ: test gọi runOnce() trực tiếp, không để lịch chạy chen ngang
        r.add("inbox.watchdog.enabled", () -> "false");
    }

    static final UUID TENANT_A = UUID.randomUUID();
    static final UUID TENANT_B = UUID.randomUUID();
    /** Quản trị viên (TENANT_ADMIN) — audit_logs.actor_user_id có khoá ngoại tới users nên phải có thật. */
    static final UUID USER_A = UUID.randomUUID();
    static final UUID USER_B = UUID.randomUUID();
    /** Nhân viên thường (AGENT) của doanh nghiệp A — kiểm quyền sửa/xoá ghi chú. */
    static final UUID AGENT_A = UUID.randomUUID();

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    private static boolean seeded;

    /** Chạy SAU khi Spring khởi động (Flyway đã tạo bảng); cờ tĩnh để chỉ seed một lần. */
    @BeforeEach
    void seedTenants() throws Exception {
        if (seeded) {
            return;
        }
        seeded = true;
        // crm_owner là superuser của container nên ghi được bất chấp RLS
        try (Connection c = owner()) {
            for (UUID t : new UUID[] {TENANT_A, TENANT_B}) {
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, ?, ?, ?)")) {
                    ps.setObject(1, t);
                    ps.setString(2, "DN " + t);
                    ps.setString(3, "dn-" + t.toString().substring(0, 8));
                    ps.setString(4, "admin@" + t.toString().substring(0, 8) + ".vn");
                    ps.executeUpdate();
                }
            }
            for (Object[] u : new Object[][] {
                    {TENANT_A, USER_A, "Quản trị A"}, {TENANT_B, USER_B, "Quản trị B"}, {TENANT_A, AGENT_A, "Nhân viên A"}}) {
                try (PreparedStatement ps = c.prepareStatement("""
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', ?, 'ACTIVE')""")) {
                    ps.setObject(1, u[1]);
                    ps.setObject(2, u[0]);
                    ps.setString(3, u[1].toString().substring(0, 8) + "@nv.vn");
                    ps.setString(4, (String) u[2]);
                    ps.executeUpdate();
                }
            }
        }
    }

    // ── tiện ích chung ──────────────────────────────────────────────────────────

    /** Quản trị viên của doanh nghiệp. */
    static JwtRequestPostProcessor as(UUID tenantId) {
        return asUser(tenantId, TENANT_A.equals(tenantId) ? USER_A : USER_B, "TENANT_ADMIN");
    }

    static JwtRequestPostProcessor asUser(UUID tenantId, UUID userId, String role) {
        return jwt().jwt(j -> j.subject(userId.toString())
                .claim("tenant_id", tenantId.toString())
                .claim("role", role));
    }

    ResultActions createContact(UUID tenantId, String body) throws Exception {
        return mvc.perform(post("/api/v1/contacts").with(as(tenantId))
                .contentType(MediaType.APPLICATION_JSON).content(body));
    }

    String createdContactId(UUID tenantId, String body) throws Exception {
        String res = createContact(tenantId, body).andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
        return data(res).get("contact").get("id").asText();
    }

    JsonNode data(String body) {
        try {
            return json.readTree(body).get("data");
        } catch (Exception e) {
            throw new IllegalStateException(body, e);
        }
    }

    static Connection owner() throws Exception {
        return DriverManager.getConnection(PG.getJdbcUrl(), "crm_owner", "changeme");
    }
}
