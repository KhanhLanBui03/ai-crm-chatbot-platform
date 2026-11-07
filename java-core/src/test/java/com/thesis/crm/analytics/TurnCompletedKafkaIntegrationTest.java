package com.thesis.crm.analytics;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.KafkaContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;

/**
 * UC039 đầu-cuối trên Kafka và Postgres THẬT: bản tin {@code ai.turn.completed} (đúng khuôn ai-service gửi —
 * khoá tenant, giá trị JSON chuỗi) → {@code TurnCompletedListener} → {@code analytics.metrics_daily}.
 *
 * <p>Bắt ba điều chỉ đường thật mới lộ: bộ giải mã nhận đúng chuỗi JSON, offset xác nhận thủ công vẫn chạy,
 * và một bản tin hỏng KHÔNG chặn các bản tin sau trong cùng phân vùng.
 */
@SpringBootTest
@Testcontainers
class TurnCompletedKafkaIntegrationTest {

    static final UUID TENANT = UUID.fromString("33333333-3333-3333-3333-333333333333");
    static final String TOPIC = "ai.turn.completed";

    @Container
    static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>(
            DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres"))
            .withDatabaseName("thesis_crm")
            .withUsername("crm_owner")
            .withPassword("changeme")
            .withCopyFileToContainer(
                    MountableFile.forHostPath(Path.of("..", "scripts", "init-db.sql").toAbsolutePath()),
                    "/docker-entrypoint-initdb.d/00-init.sql");

    /** ZooKeeper, không KRaft — cùng lý do với {@code OutboxPublisherIntegrationTest} (ADR-0009). */
    @Container
    static final KafkaContainer KAFKA = new KafkaContainer(DockerImageName.parse("confluentinc/cp-kafka:7.9.0"));

    @DynamicPropertySource
    static void cauHinh(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", () -> "crm_app");
        r.add("spring.datasource.password", () -> "changeme");
        r.add("spring.flyway.user", () -> "crm_owner");
        r.add("spring.flyway.password", () -> "changeme");
        r.add("spring.kafka.bootstrap-servers", KAFKA::getBootstrapServers);
        r.add("crm.outbox.publisher.enabled", () -> "false");
        r.add("eureka.client.enabled", () -> "false");
        // Bật lại consumer mà src/test/resources/application.properties tắt cho các test không có Kafka
        r.add("crm.analytics.turn-consumer.enabled", () -> "true");
    }

    @BeforeAll
    static void taoTopic() throws Exception {
        try (AdminClient admin = AdminClient.create(Map.of("bootstrap.servers", KAFKA.getBootstrapServers()))) {
            admin.createTopics(List.of(new NewTopic(TOPIC, 3, (short) 1))).all().get();
        }
    }

    @Test
    void banTinThat_duocCongDon_banTinTrungBoQua_banTinHongKhongChanPhanVung() throws Exception {
        seedTenant();
        String id1 = UUID.randomUUID().toString();
        String id2 = UUID.randomUUID().toString();
        try (KafkaProducer<String, String> p = producer()) {
            gui(p, suKien(id1, "RAG", true, "0.5000"));
            gui(p, suKien(id1, "RAG", true, "0.5000"));          // giao lại — phải bỏ qua
            gui(p, "đây không phải JSON");                         // hỏng — ghi log, xác nhận, đi tiếp
            gui(p, suKien(id2, "CLARIFY", false, "0"));
            p.flush();
        }

        doi(() -> "2".equals(motCot("SELECT coalesce(sum(interaction_count), 0) FROM analytics.metrics_daily "
                + "WHERE tenant_id = ?", TENANT)), Duration.ofSeconds(60));

        // Chờ thêm một nhịp: nếu bản trùng bị cộng thì tổng sẽ lên 3 ngay sau đó
        Thread.sleep(2000);
        assertThat(motCot("SELECT sum(interaction_count) FROM analytics.metrics_daily WHERE tenant_id = ?", TENANT))
                .isEqualTo("2");
        assertThat(motCot("SELECT sum(llm_call_count) FROM analytics.metrics_daily WHERE tenant_id = ?", TENANT))
                .isEqualTo("1");
        assertThat(motCot("SELECT sum(cost_vnd)::text FROM analytics.metrics_daily WHERE tenant_id = ?", TENANT))
                .isEqualTo("0.5000");
        assertThat(motCot("SELECT count(*) FROM analytics.processed_events WHERE consumer_group = 'analytics-cg' "
                + "AND tenant_id = ?", TENANT)).isEqualTo("2");
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static String suKien(String eventId, String branch, boolean llm, String cost) {
        return """
                {"event_id":"%s","event_version":1,"event_type":"TurnCompleted","tenant_id":"%s",
                 "aggregate_id":"%s","occurred_at":"%s",
                 "payload":{"conversation_id":"%s","branch":"%s","status":"SUCCESS","is_answered":true,
                   "refusal_reason":null,"llm_called":%s,"is_cached":false,"is_degraded":false,"is_handoff":false,
                   "safety_flag":null,"model_name":"%s","model_version":null,"prompt_tokens":%d,
                   "completion_tokens":%d,"cost_vnd":%s,"latency_ms":900,
                   "latency_breakdown":{"guard_ms":1,"classify_ms":5},"groundedness_score":null}}"""
                .formatted(eventId, TENANT, UUID.randomUUID(), Instant.now(), UUID.randomUUID(), branch, llm,
                        llm ? "gemini-2.5-flash" : "template", llm ? 700 : 0, llm ? 50 : 0, cost);
    }

    private static KafkaProducer<String, String> producer() {
        return new KafkaProducer<>(Map.of(
                ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, KAFKA.getBootstrapServers(),
                ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class,
                ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class));
    }

    /** Khoá tenant_id như ai-service — mọi bản tin của một doanh nghiệp vào cùng một phân vùng, đúng thứ tự. */
    private static void gui(KafkaProducer<String, String> p, String value) throws Exception {
        p.send(new ProducerRecord<>(TOPIC, TENANT.toString(), value)).get();
    }

    private static void doi(Callable<Boolean> dieuKien, Duration toiDa) throws Exception {
        Instant het = Instant.now().plus(toiDa);
        while (Instant.now().isBefore(het)) {
            if (Boolean.TRUE.equals(dieuKien.call())) {
                return;
            }
            Thread.sleep(500);
        }
        throw new AssertionError("Hết " + toiDa.toSeconds() + " giây mà consumer chưa cộng dồn xong.");
    }

    private static void seedTenant() throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                INSERT INTO platform.tenants (id, name, slug, contact_email)
                VALUES (?, 'DN Kafka', 'dn-kafka-uc039', 'k@example.test') ON CONFLICT (id) DO NOTHING""")) {
            ps.setObject(1, TENANT);
            ps.executeUpdate();
        }
    }

    private static String motCot(String query, Object... args) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : null;
            }
        }
    }

    private static Connection owner() throws Exception {
        return DriverManager.getConnection(PG.getJdbcUrl(), "crm_owner", "changeme");
    }
}
