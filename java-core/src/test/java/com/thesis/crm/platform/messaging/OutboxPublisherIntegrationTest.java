package com.thesis.crm.platform.messaging;

import static java.nio.charset.StandardCharsets.UTF_8;
import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
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
 * Job phát outbox trên Postgres và Kafka THẬT (cùng image {@code cp-kafka:7.9.0} với compose).
 *
 * <p>Gọi {@link OutboxPublisher#publishPendingBatch()} trực tiếp, bộ hẹn giờ tắt — test không phải
 * đoán lúc nào lượt 500 ms chạy tới.
 */
@SpringBootTest
@Testcontainers
class OutboxPublisherIntegrationTest {

    static final UUID TENANT_A = UUID.fromString("11111111-1111-1111-1111-111111111111");
    static final UUID TENANT_B = UUID.fromString("22222222-2222-2222-2222-222222222222");
    static final String TOPIC_TAI_LIEU = "crm.kb.document.uploaded";
    static final String TOPIC_LEAD = "crm.lead.v1";

    @Container
    static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>(
            DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres"))
            .withDatabaseName("thesis_crm")
            .withUsername("crm_owner")
            .withPassword("changeme")
            .withCopyFileToContainer(
                    MountableFile.forHostPath(Path.of("..", "scripts", "init-db.sql").toAbsolutePath()),
                    "/docker-entrypoint-initdb.d/00-init.sql");

    /**
     * Chế độ ZooKeeper (mặc định của KafkaContainer), KHÔNG {@code withKraft()}: đã thử, cp-kafka
     * 7.9.0 ở KRaft thoát ngay với "advertised.listeners cannot use the nonroutable meta-address
     * 0.0.0.0" — đúng lỗi mà ADR-0009 và {@code docker-compose.yml} né bằng ZooKeeper.
     */
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
    }

    @Autowired
    OutboxPublisher publisher;

    final ObjectMapper json = new ObjectMapper();

    /** Ba phân vùng: kiểm được rằng mọi sự kiện của một tenant rơi vào CÙNG một phân vùng. */
    @BeforeAll
    static void taoTopic() throws Exception {
        try (AdminClient admin = AdminClient.create(Map.of("bootstrap.servers", KAFKA.getBootstrapServers()))) {
            admin.createTopics(List.of(
                    new NewTopic(TOPIC_TAI_LIEU, 3, (short) 1),
                    new NewTopic(TOPIC_LEAD, 3, (short) 1))).all().get();
        }
    }

    @BeforeEach
    void datLai() throws SQLException {
        chay("""
                INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES
                    ('%s', 'A', 'dn-a', 'a@example.test'), ('%s', 'B', 'dn-b', 'b@example.test')
                ON CONFLICT (id) DO NOTHING
                """.formatted(TENANT_A, TENANT_B));
        chay("DELETE FROM platform.outbox_events");
    }

    @Test
    void phatVoSuKienKhoaTenantVaGiuThuTuTrongTenant() throws Exception {
        List<Long> idA = new ArrayList<>();
        for (int i = 1; i <= 3; i++) {
            idA.add(chenOutbox(TENANT_A, TOPIC_TAI_LIEU, "{\"document_id\": \"a-" + i + "\", \"version\": " + i + "}"));
            chenOutbox(TENANT_B, TOPIC_TAI_LIEU, "{\"document_id\": \"b-" + i + "\", \"version\": 1}");
        }

        assertThat(publisher.publishPendingBatch()).isEqualTo(6);

        List<ConsumerRecord<String, String>> banTin = doc(TOPIC_TAI_LIEU, 6);
        assertThat(banTin).hasSize(6);

        // Khoá bản tin = tenant_id; mọi bản tin của A nằm một phân vùng, đúng thứ tự event_id.
        List<ConsumerRecord<String, String>> cuaA = banTin.stream()
                .filter(r -> r.key().equals(TENANT_A.toString())).toList();
        assertThat(cuaA).hasSize(3);
        assertThat(cuaA.stream().map(ConsumerRecord::partition).distinct()).hasSize(1);
        List<Long> thuTu = new ArrayList<>();
        for (ConsumerRecord<String, String> r : cuaA) {
            thuTu.add(json.readTree(r.value()).path("event_id").asLong());
        }
        assertThat(thuTu).containsExactlyElementsOf(idA);

        // Vỏ đúng docs/events/README.md + hợp đồng UC018 mục 6.
        ConsumerRecord<String, String> dau = cuaA.get(0);
        JsonNode vo = json.readTree(dau.value());
        assertThat(vo.fieldNames()).toIterable().containsExactly(
                "event_id", "event_version", "event_type", "tenant_id", "aggregate_id", "occurred_at", "payload");
        assertThat(vo.path("event_version").asInt()).isEqualTo(1);
        assertThat(vo.path("event_type").asText()).isEqualTo("DocumentUploaded");
        assertThat(vo.path("tenant_id").asText()).isEqualTo(TENANT_A.toString());
        assertThat(Instant.parse(vo.path("occurred_at").asText())).isBefore(Instant.now().plusSeconds(1));
        assertThat(vo.path("payload").path("document_id").asText()).isEqualTo("a-1");

        // Trace ID ở header Kafka; không rò tên lớp Java qua header __TypeId__.
        assertThat(new String(dau.headers().lastHeader("X-Trace-Id").value(), UTF_8)).isEqualTo("trace-outbox");
        assertThat(dau.headers().lastHeader("__TypeId__")).isNull();

        assertThat(demChuaPhat()).isZero();
    }

    @Test
    void suKienHongChiChanTenantCuaNo() throws Exception {
        long hong = chenOutbox(TENANT_A, "ten topic khong hop le!", "{}");
        long sauHong = chenOutbox(TENANT_A, TOPIC_LEAD, "{\"thu_tu\": 2}");
        chenOutbox(TENANT_B, TOPIC_LEAD, "{\"thu_tu\": 1}");

        assertThat(publisher.publishPendingBatch()).isEqualTo(1);

        // B không bị kẹt vì A; sự kiện sau của A phải CHỜ sự kiện hỏng — phát nó là sai thứ tự.
        List<ConsumerRecord<String, String>> banTin = doc(TOPIC_LEAD, 1);
        assertThat(banTin).singleElement().satisfies(r -> assertThat(r.key()).isEqualTo(TENANT_B.toString()));
        Map<String, Object> dongHong = dong(hong);
        assertThat(dongHong.get("published_at")).isNull();
        assertThat(dongHong.get("attempt_count")).isEqualTo(1);
        assertThat((String) dongHong.get("last_error")).isNotBlank();
        assertThat(dong(sauHong).get("published_at")).isNull();
        assertThat(dong(sauHong).get("attempt_count")).isEqualTo(0);

        // Lượt kế tiếp ngay sau đó: còn trong khoảng lùi 2 s — không thử lại, không phát gì của A.
        assertThat(publisher.publishPendingBatch()).isZero();
        assertThat(dong(hong).get("attempt_count")).isEqualTo(1);
    }

    @Test
    void phienBanLayTuHauToTopic() {
        assertThat(OutboxPublisher.phienBan("crm.kb.document.uploaded")).isEqualTo(1);
        assertThat(OutboxPublisher.phienBan("crm.document.v1")).isEqualTo(1);
        assertThat(OutboxPublisher.phienBan("crm.lead.v12")).isEqualTo(12);
        assertThat(OutboxPublisher.phienBan("khong-co-hau-to")).isEqualTo(1);
    }

    // ── Tiện ích ─────────────────────────────────────────────────────────────────

    private List<ConsumerRecord<String, String>> doc(String topic, int canDoc) {
        Properties p = new Properties();
        p.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, KAFKA.getBootstrapServers());
        p.put(ConsumerConfig.GROUP_ID_CONFIG, "test-" + UUID.randomUUID());
        p.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        List<ConsumerRecord<String, String>> ds = new ArrayList<>();
        try (KafkaConsumer<String, String> c = new KafkaConsumer<>(p, new StringDeserializer(), new StringDeserializer())) {
            c.subscribe(List.of(topic));
            long han = System.currentTimeMillis() + 20_000;
            while (ds.size() < canDoc && System.currentTimeMillis() < han) {
                c.poll(Duration.ofMillis(500)).forEach(ds::add);
            }
            // Đợi thêm một nhịp: bắt được bản tin THỪA nếu job phát nhầm thứ không được phát.
            c.poll(Duration.ofSeconds(1)).forEach(ds::add);
        }
        return ds;
    }

    private static Connection chuBang() throws SQLException {
        return DriverManager.getConnection(PG.getJdbcUrl(), "crm_owner", "changeme");
    }

    private static void chay(String sql) throws SQLException {
        try (Connection c = chuBang(); Statement s = c.createStatement()) {
            s.execute(sql);
        }
    }

    private static long chenOutbox(UUID tenant, String topic, String payload) throws SQLException {
        try (Connection c = chuBang(); PreparedStatement ps = c.prepareStatement("""
                INSERT INTO platform.outbox_events
                    (tenant_id, aggregate_type, aggregate_id, event_type, topic, payload, headers)
                VALUES (?, 'document', ?, 'DocumentUploaded', ?, ?::jsonb, '{"X-Trace-Id": "trace-outbox"}'::jsonb)
                RETURNING id
                """)) {
            ps.setObject(1, tenant);
            ps.setObject(2, UUID.randomUUID());
            ps.setString(3, topic);
            ps.setString(4, payload);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return rs.getLong(1);
            }
        }
    }

    private static Map<String, Object> dong(long id) throws SQLException {
        try (Connection c = chuBang(); PreparedStatement ps = c.prepareStatement(
                "SELECT published_at, attempt_count, last_error FROM platform.outbox_events WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                Map<String, Object> m = new java.util.HashMap<>();
                m.put("published_at", rs.getTimestamp(1));
                m.put("attempt_count", rs.getInt(2));
                m.put("last_error", rs.getString(3));
                return m;
            }
        }
    }

    private static int demChuaPhat() throws SQLException {
        try (Connection c = chuBang(); Statement s = c.createStatement();
                ResultSet rs = s.executeQuery("SELECT count(*) FROM platform.outbox_events WHERE published_at IS NULL")) {
            rs.next();
            return rs.getInt(1);
        }
    }
}
