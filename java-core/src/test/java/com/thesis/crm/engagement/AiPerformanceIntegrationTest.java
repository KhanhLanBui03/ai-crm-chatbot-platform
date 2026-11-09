package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.analytics.service.TurnMetricsService;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;

/**
 * UC039 — cộng dồn {@code ai.turn.completed} vào {@code analytics.metrics_daily} và API
 * {@code GET /api/v1/analytics/ai-performance}. Gọi thẳng {@link TurnMetricsService} (logic consumer); đường
 * Kafka thật nằm ở {@code TurnCompletedKafkaIntegrationTest}.
 *
 * <p>Mỗi test dùng một doanh nghiệp RIÊNG — số liệu là tổng cộng dồn, dùng chung thì test này đếm lượt của
 * test kia.
 */
class AiPerformanceIntegrationTest extends EngagementIntegrationTestBase {

    @Autowired TurnMetricsService metrics;
    @Autowired ObjectMapper mapper;

    private UUID tenant;
    private UUID admin;
    private UUID agent;
    private UUID channel;
    private UUID conv;

    @BeforeEach
    void doanhNghiepMoi() throws Exception {
        tenant = UUID.randomUUID();
        admin = UUID.randomUUID();
        agent = UUID.randomUUID();
        channel = UUID.randomUUID();
        conv = UUID.randomUUID();
        UUID contact = UUID.randomUUID();
        UUID identity = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN hiệu quả AI', ?, ?)",
                    tenant, "hq-" + tenant.toString().substring(0, 8), "hq@" + tenant.toString().substring(0, 8) + ".vn");
            for (UUID u : new UUID[] {admin, agent}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', 'Người dùng', 'ACTIVE')""", u, tenant, u.toString().substring(0, 8) + "@hq.vn");
            }
            exec(c, "INSERT INTO engagement.channels (id, tenant_id, type, name, status) VALUES (?, ?, 'ZALO', 'Zalo', 'ACTIVE')",
                    channel, tenant);
            exec(c, "INSERT INTO engagement.contacts (id, tenant_id, full_name, primary_channel) VALUES (?, ?, 'Khách', 'ZALO')",
                    contact, tenant);
            exec(c, """
                    INSERT INTO engagement.channel_identities (id, tenant_id, channel_id, contact_id, external_user_id)
                    VALUES (?, ?, ?, ?, ?)""", identity, tenant, channel, contact, "zl-" + identity);
            exec(c, """
                    INSERT INTO engagement.conversations (id, tenant_id, channel_id, channel_identity_id, contact_id)
                    VALUES (?, ?, ?, ?, ?)""", conv, tenant, channel, identity, contact);
        }
    }

    @Test
    void congDon_dungTong_dungTiLeKhongGoiLlm_chiPhiBonSoLe() throws Exception {
        nhan(luot("RAG").llm(true).cost("0.1235").tre(1800, Map.of("embed_ms", 40, "retrieve_ms", 60, "generate_ms", 1600)));
        nhan(luot("RAG").llm(true).cost("0.0001").tre(1200, Map.of("embed_ms", 20, "retrieve_ms", 40, "generate_ms", 1000)));
        nhan(luot("CLARIFY").tuChoi().tre(10, Map.of("guard_ms", 1, "classify_ms", 6)));
        nhan(luot("SMALL_TALK").tre(10, Map.of("guard_ms", 1, "classify_ms", 6)));

        JsonNode d = baoCao("");
        assertThat(d.get("totalInteractions").asLong()).isEqualTo(4);
        assertThat(d.get("llmFreeRate").asDouble()).isEqualTo(0.5);          // 2 trong 4 lượt không gọi LLM
        assertThat(d.get("refusalRate").asDouble()).isEqualTo(0.25);
        assertThat(new BigDecimal(d.get("costVnd").asText())).isEqualByComparingTo("0.1236");
        assertThat(d.get("avgLatencyMs").asLong()).isEqualTo((1800 + 1200 + 10 + 10) / 4);
        // Trung bình từng chặng chia theo số lượt CHẠY chặng — lượt mẫu câu không kéo "truy hồi" xuống
        assertThat(d.get("latencyBreakdown").get("retrieve").asLong()).isEqualTo((40 + 20) / 2 + (60 + 40) / 2);
        assertThat(d.get("latencyBreakdown").get("generate").asLong()).isEqualTo(1300);
        assertThat(d.get("updatedAt").isNull()).isFalse();
        assertThat(d.get("avgGroundedness").asDouble()).isEqualTo(0.8);
    }

    @Test
    void duBayNhanh_nhanhKhongCoLuotVanHien0() throws Exception {
        nhan(luot("RAG").llm(true));
        Map<String, Long> theoNhanh = new HashMap<>();
        baoCao("").get("routeDistribution").forEach(r -> theoNhanh.put(r.get("route").asText(), r.get("count").asLong()));
        assertThat(theoNhanh).hasSize(7).containsEntry("RAG", 1L).containsEntry("SUMMARY", 0L).containsEntry("TOOL_CALL", 0L);
    }

    @Test
    void nhanTrung_khongCongHaiLan() throws Exception {
        JsonNode sk = luot("RAG").llm(true).build();
        assertThat(metrics.ghiNhan(sk)).isTrue();
        assertThat(metrics.ghiNhan(sk)).isFalse();
        assertThat(baoCao("").get("totalInteractions").asLong()).isEqualTo(1);
    }

    @Test
    void nhanhLa_tuChoi_khongGhiGi() throws Exception {
        assertThatThrownBy(() -> metrics.ghiNhan(luot("TOOLCALL").build()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(motCot("SELECT count(*) FROM analytics.metrics_daily WHERE tenant_id = ?", tenant)).isEqualTo("0");
        assertThat(motCot("SELECT count(*) FROM analytics.processed_events WHERE tenant_id = ?", tenant)).isEqualTo("0");
    }

    @Test
    void doiPhienBanMoHinh_tachDong_locDuocTheoPhienBan() throws Exception {
        nhan(luot("RAG").llm(true).moHinh("gemini-2.5-flash", "2025-06").cost("1.0000"));
        nhan(luot("RAG").llm(true).moHinh("gemini-2.5-flash", "2025-09").cost("2.0000"));

        assertThat(motCot("SELECT count(*) FROM analytics.metrics_daily WHERE tenant_id = ? AND branch = 'RAG'", tenant))
                .isEqualTo("2");
        JsonNode tatCa = baoCao("");
        assertThat(tatCa.get("modelVersions").toString()).contains("gemini-2.5-flash@2025-06", "gemini-2.5-flash@2025-09");
        JsonNode moi = baoCao("?modelVersion=gemini-2.5-flash@2025-09");
        assertThat(moi.get("totalInteractions").asLong()).isEqualTo(1);
        assertThat(new BigDecimal(moi.get("costVnd").asText())).isEqualByComparingTo("2");
    }

    @Test
    void ngayTinhTheoMuiGioDoanhNghiep() throws Exception {
        // 18:30 UTC ngày 06/11 = 01:30 ngày 07/11 giờ Việt Nam
        nhan(luot("RAG").llm(true).luc("2026-11-06T18:30:00Z"));
        assertThat(motCot("SELECT metric_date::text FROM analytics.metrics_daily WHERE tenant_id = ?", tenant))
                .isEqualTo("2026-11-07");
        assertThat(baoCao("?from=2026-11-07&to=2026-11-07").get("totalInteractions").asLong()).isEqualTo(1);
        assertThat(baoCao("?from=2026-11-06&to=2026-11-06").get("totalInteractions").asLong()).isZero();
    }

    @Test
    void lyDoChuyenGiao_hetHanMucKhongTinhVaoChatLuong() throws Exception {
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO engagement.handoff_events (tenant_id, conversation_id, direction, reason, triggered_by,
                                                           counts_against_ai_quality)
                    VALUES (?, ?, 'BOT_TO_AGENT', 'QUOTA_EXCEEDED', 'SYSTEM', false),
                           (?, ?, 'BOT_TO_AGENT', 'LOW_CONFIDENCE', 'AI_AGENT', true),
                           (?, ?, 'BOT_TO_AGENT', 'LOW_CONFIDENCE', 'AI_AGENT', true),
                           (?, ?, 'AGENT_TO_BOT', 'CUSTOMER_REQUEST', 'SYSTEM', false)""",
                    tenant, conv, tenant, conv, tenant, conv, tenant, conv);
        }
        Map<String, JsonNode> lyDo = new LinkedHashMap<>();
        baoCao("").get("handoffReasons").forEach(r -> lyDo.put(r.get("reason").asText(), r));
        assertThat(lyDo).containsOnlyKeys("LOW_CONFIDENCE", "QUOTA_EXCEEDED");   // chiều trả về cho AI không tính
        assertThat(lyDo.get("LOW_CONFIDENCE").get("count").asLong()).isEqualTo(2);
        assertThat(lyDo.get("LOW_CONFIDENCE").get("countsAgainstAiQuality").asBoolean()).isTrue();
        assertThat(lyDo.get("QUOTA_EXCEEDED").get("countsAgainstAiQuality").asBoolean()).isFalse();
    }

    @Test
    void chuaCoLuotNao_tra0_vaMocCapNhatRong() throws Exception {
        JsonNode d = baoCao("");
        assertThat(d.get("totalInteractions").asLong()).isZero();
        assertThat(d.get("updatedAt").isNull()).isTrue();
        assertThat(d.get("avgLatencyMs").isNull()).isTrue();
        assertThat(d.get("routeDistribution")).hasSize(7);
    }

    @Test
    void cachLyDoanhNghiep_vaNhanVienBi403() throws Exception {
        nhan(luot("RAG").llm(true));
        UUID khac = tenant;
        doanhNghiepMoi();                       // doanh nghiệp mới, chưa có lượt nào
        assertThat(baoCao("").get("totalInteractions").asLong()).isZero();
        assertThat(khac).isNotEqualTo(tenant);

        mvc.perform(get("/api/v1/analytics/ai-performance").with(asUser(tenant, agent, "AGENT")))
                .andExpect(status().isForbidden());
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private JsonNode baoCao(String query) throws Exception {
        String body = mvc.perform(get("/api/v1/analytics/ai-performance" + query).with(quanTri()))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        return data(body);
    }

    private JwtRequestPostProcessor quanTri() {
        return asUser(tenant, admin, "TENANT_ADMIN");
    }

    private void nhan(Luot l) {
        assertThat(metrics.ghiNhan(l.build())).isTrue();
    }

    private Luot luot(String branch) {
        return new Luot(branch);
    }

    /** Dựng sự kiện ai.turn.completed đúng lược đồ docs/events/ai.turn.completed.v1.json. */
    private final class Luot {
        private final Map<String, Object> p = new LinkedHashMap<>();
        private String luc = java.time.Instant.now().toString();

        Luot(String branch) {
            p.put("conversation_id", conv.toString());
            p.put("branch", branch);
            p.put("status", "SUCCESS");
            p.put("is_answered", true);
            p.put("refusal_reason", null);
            p.put("llm_called", false);
            p.put("is_cached", false);
            p.put("is_degraded", false);
            p.put("is_handoff", false);
            p.put("model_name", "template");
            p.put("model_version", null);
            p.put("prompt_tokens", 0);
            p.put("completion_tokens", 0);
            p.put("cost_vnd", new BigDecimal("0"));
            p.put("latency_ms", 10);
            p.put("latency_breakdown", Map.of());
            p.put("groundedness_score", null);
        }

        Luot llm(boolean b) {
            p.put("llm_called", b);
            if (b) {
                p.put("model_name", "gemini-2.5-flash");
                p.put("prompt_tokens", 800);
                p.put("completion_tokens", 60);
                p.put("groundedness_score", 0.8);
            }
            return this;
        }

        Luot cost(String v) {
            p.put("cost_vnd", new BigDecimal(v));
            return this;
        }

        Luot tre(int tong, Map<String, Integer> cacChang) {
            p.put("latency_ms", tong);
            p.put("latency_breakdown", cacChang);
            return this;
        }

        Luot tuChoi() {
            p.put("is_answered", false);
            p.put("refusal_reason", "LOW_CONFIDENCE");
            return this;
        }

        Luot moHinh(String ten, String phienBan) {
            p.put("model_name", ten);
            p.put("model_version", phienBan);
            return this;
        }

        Luot luc(String iso) {
            luc = iso;
            return this;
        }

        JsonNode build() {
            Map<String, Object> sk = new LinkedHashMap<>();
            sk.put("event_id", UUID.randomUUID().toString());
            sk.put("event_version", 1);
            sk.put("event_type", "TurnCompleted");
            sk.put("tenant_id", tenant.toString());
            sk.put("aggregate_id", conv.toString());
            sk.put("occurred_at", luc);
            sk.put("payload", p);
            return mapper.valueToTree(sk);
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

    private static void exec(Connection c, String query, Object... args) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            ps.executeUpdate();
        }
    }
}
